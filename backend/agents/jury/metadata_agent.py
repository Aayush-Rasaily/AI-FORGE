"""
Metadata Agent — analyses EXIF, timestamps, and software provenance only.
"""

from typing import Any, Dict, List, Optional

from backend.agents.jury.utils import (
    build_finding,
    clamp,
    safe_float,
    verdict_from_score,
)


def run_metadata_agent(
    analysis: Optional[Dict[str, Any]] = None,
    tampering: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    analysis = analysis or {}
    tampering = tampering or {}
    signals = analysis.get("signals") or {}
    tampering_analysis = tampering.get("analysis") or {}
    metadata_block = tampering_analysis.get("metadata") or {}

    findings: List[Dict[str, Any]] = []
    risk_factors: List[float] = []

    metadata_forensics = analysis.get("metadata_forensics") or {}
    metadata_risk = safe_float(
        metadata_forensics.get("metadata_risk_score")
        or signals.get("metadata_risk_score", 0)
    )

    if metadata_risk >= 0.35:
        risk_factors.append(metadata_risk)
        findings.append(build_finding(
            "metadata_forensics",
            f"Metadata forensics risk score {metadata_risk:.0%}.",
            metadata_forensics.get("forensic_report", {}).get("summary", "")
            or "EXIF/GPS/thumbnail/hash analysis flagged integrity issues.",
            metadata_risk,
        ))
    software_detected = bool(signals.get("software_detected", False))
    software = signals.get("software") or metadata_block.get("software")

    metadata_suspicious = bool(signals.get("metadata_suspicious", False)) or metadata_risk >= 0.35

    if metadata_suspicious and metadata_risk < 0.35:
        risk_factors.append(0.75)
        findings.append(build_finding(
            "metadata",
            "Metadata timestamps are inconsistent with image content.",
            "EXIF creation and modification timestamps do not align with expected "
            "capture patterns, suggesting post-processing.",
            0.75,
        ))

    if software_detected and software:
        risk_factors.append(0.65)
        findings.append(build_finding(
            "metadata",
            f"Editing software detected in metadata: {software}.",
            "Presence of image editing software in EXIF data is a common indicator "
            "that the file underwent post-capture modification.",
            0.65,
        ))

    if metadata_block.get("suspicious_software"):
        risk_factors.append(0.80)
        findings.append(build_finding(
            "metadata",
            "Suspicious software signatures found in EXIF metadata.",
            "Metadata contains indicators of professional editing tools.",
            0.80,
        ))

    if metadata_block.get("metadata_missing") or not signals.get("metadata_found", True):
        risk_factors.append(0.55)
        findings.append(build_finding(
            "metadata",
            "EXIF metadata is missing or stripped from the file.",
            "Absence of metadata is common in re-saved or intentionally sanitized images.",
            0.55,
        ))

    camera_make = metadata_block.get("camera_make") or signals.get("camera_make")
    if camera_make:
        findings.append(build_finding(
            "metadata",
            f"Camera device recorded: {camera_make}.",
            "Device provenance information is available for chain-of-custody validation.",
            0.90,
        ))

    if not findings:
        findings.append(build_finding(
            "metadata",
            "Metadata appears consistent with an unmodified capture.",
            "No suspicious EXIF anomalies, software tags, or timestamp conflicts detected.",
            0.85,
        ))
        risk_factors.append(0.15)

    risk_score = clamp(sum(risk_factors) / len(risk_factors)) if risk_factors else 0.15
    verdict = verdict_from_score(risk_score)
    confidence = clamp(max(risk_factors) if risk_factors else 0.85)

    return {
        "agent_id": "metadata",
        "agent_name": "Metadata Agent",
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "risk_score": round(risk_score, 4),
        "findings": findings,
        "explanation": " ".join(f["what"] for f in findings),
        "signals": [f["what"] for f in findings],
        "raw_scores": {"metadata_risk": round(risk_score, 4)},
        "vote": "risk" if risk_score >= 0.45 else "authentic",
    }
