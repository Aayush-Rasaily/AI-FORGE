"""
OCR Layout Agent — analyses spacing, font consistency, and layout anomalies.
"""

from typing import Any, Dict, List, Optional

from backend.agents.jury.utils import (
    build_finding,
    clamp,
    safe_float,
    verdict_from_score,
)


def run_ocr_layout_agent(
    analysis: Optional[Dict[str, Any]] = None,
    document_analysis: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    analysis = analysis or {}
    document_analysis = document_analysis or {}
    signals = analysis.get("signals") or {}

    findings: List[Dict[str, Any]] = []
    risk_factors: List[float] = []

    # From unified image analysis signals
    spacing_risk = safe_float(signals.get("spacing_risk", 0)) / 100.0
    font_anomaly_count = int(signals.get("font_anomaly_count", 0) or 0)
    region_anomaly_count = int(signals.get("region_anomaly_count", 0) or 0)

    if spacing_risk >= 0.4:
        risk_factors.append(spacing_risk)
        findings.append(build_finding(
            "spacing",
            "Irregular word and line spacing detected in text regions.",
            "OCR layout analysis found spacing deviations inconsistent with "
            "natural document typography.",
            spacing_risk,
        ))

    if font_anomaly_count > 0:
        risk = min(0.5 + font_anomaly_count * 0.1, 0.95)
        risk_factors.append(risk)
        findings.append(build_finding(
            "font",
            f"Font inconsistencies detected across {font_anomaly_count} region(s).",
            "Multiple font styles or sizes in similar document zones suggest "
            "possible text insertion or overlay.",
            risk,
        ))

    if region_anomaly_count > 0:
        risk = min(0.45 + region_anomaly_count * 0.08, 0.90)
        risk_factors.append(risk)
        findings.append(build_finding(
            "region",
            f"Layout anomalies found in {region_anomaly_count} document region(s).",
            "Structural layout analysis identified regions with abnormal bounding boxes "
            "or alignment patterns.",
            risk,
        ))

    # From document forensics pipeline
    if document_analysis:
        doc_type = document_analysis.get("document_type", "document")
        page_count = document_analysis.get("page_count", 0)
        findings.append(build_finding(
            "document",
            f"Document forensics analyzed {page_count} page(s) of type '{doc_type}'.",
            "Full document OCR and layout pipeline was applied to extracted content.",
            0.80,
        ))

        layout_issues = document_analysis.get("layout_issues") or []
        for issue in layout_issues[:3]:
            risk_factors.append(0.6)
            findings.append(build_finding(
                "document_layout",
                str(issue),
                "Document layout module flagged structural inconsistency.",
                0.6,
            ))

    if not findings:
        findings.append(build_finding(
            "ocr_layout",
            "No significant OCR or layout anomalies detected.",
            "Text spacing, font consistency, and region layout appear normal.",
            0.85,
        ))
        risk_factors.append(0.12)

    risk_score = clamp(sum(risk_factors) / len(risk_factors)) if risk_factors else 0.12
    verdict = verdict_from_score(risk_score)
    confidence = clamp(max(risk_factors) if risk_factors else 0.85)

    return {
        "agent_id": "ocr",
        "agent_name": "OCR Agent",
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "risk_score": round(risk_score, 4),
        "findings": findings,
        "explanation": " ".join(f["what"] for f in findings),
        "signals": [f["what"] for f in findings],
        "raw_scores": {
            "spacing_risk": round(spacing_risk, 4),
            "font_anomalies": font_anomaly_count,
            "region_anomalies": region_anomaly_count,
        },
        "vote": "risk" if risk_score >= 0.45 else "authentic",
    }
