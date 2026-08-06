"""
Human-readable forensic verdict explanations.
"""

from __future__ import annotations

from typing import Any, Dict, List


def generate_forensic_explanation(
    verdict: str,
    signals: Dict[str, Any],
    findings: List[str] | None = None,
) -> str:
    """Generate a plain-language explanation for the verdict."""
    findings = findings or []
    parts: List[str] = []

    risk_high = "HIGH RISK" in verdict.upper() or "FORGED" in verdict.upper()
    risk_med = "MEDIUM" in verdict.upper() or "SUSPICIOUS" in verdict.upper()

    if not risk_high and not risk_med:
        parts.append(
            "The image shows consistent JPEG compression patterns with no duplicated regions detected."
        )
        if not signals.get("metadata_suspicious"):
            parts.append("Metadata appears consistent with the image content.")
        if float(signals.get("wavelet_score", 0)) < 0.3:
            parts.append("No suspicious wavelet frequency artifacts were found.")
        return " ".join(parts)

    if float(signals.get("ela_score", 0)) >= 0.35:
        parts.append(
            "The ELA map reveals localized compression inconsistencies that may indicate editing or re-saving."
        )
    if signals.get("copy_move_detected") or float(signals.get("copy_move_score", 0)) >= 0.4:
        parts.append(
            "Copy-move analysis detected duplicated texture regions consistent with clone or paste manipulation."
        )
    if float(signals.get("wavelet_score", 0)) >= 0.35:
        parts.append("Wavelet analysis shows abnormal high-frequency patterns in localized areas.")
    if signals.get("metadata_suspicious"):
        sw = signals.get("software") or "editing software"
        parts.append(f"Metadata contains indicators of {sw}, which may suggest post-capture modification.")
    if float(signals.get("noise_inconsistency", 0)) >= 0.3:
        parts.append("Noise distribution is inconsistent across regions, suggesting possible compositing.")
    if float(signals.get("tampering_score", 0)) >= 0.4:
        parts.append("AI tampering classifier flagged anomalies consistent with synthetic or manipulated content.")

    if findings:
        parts.append(f"Key findings: {'; '.join(str(f) for f in findings[:3])}.")

    if not parts:
        parts.append(
            "Multiple weak forensic signals were detected. Manual review is recommended."
        )

    return " ".join(parts)
