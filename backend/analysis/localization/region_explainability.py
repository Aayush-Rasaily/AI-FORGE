"""Per-region explainability — detector contributions and verdicts."""

from __future__ import annotations

from typing import Any, Dict, List


DETECTOR_LABELS = {
    "ela": "ELA",
    "wavelet": "Wavelet",
    "copy_move": "Copy-Move",
    "noise": "Noise",
    "metadata": "Metadata",
    "ocr": "OCR",
    "vit_attention": "Attention",
    "segmentation": "AI Segmentation",
    "gradcam": "GradCAM",
    "edges": "Edge",
}


def explain_region(
    region: Dict[str, Any],
    analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """Build click-to-inspect explanation payload for a region."""
    contributions = region.get("detector_contributions") or {}
    votes = region.get("detector_votes") or {}
    confidence = float(region.get("confidence") or 0)
    if confidence <= 1:
        confidence *= 100.0

    detector_rows: List[Dict[str, Any]] = []
    for key, val in contributions.items():
        if isinstance(val, bool):
            score = 1.0 if val else 0.0
        else:
            score = float(val)
        detector_rows.append({
            "detector": DETECTOR_LABELS.get(key, key.replace("_", " ").title()),
            "contribution": round(score, 4),
            "active": score >= 0.35 or votes.get(key, False),
        })
    detector_rows.sort(key=lambda r: r["contribution"], reverse=True)

    signals = analysis.get("signals") or {}
    return {
        "region_id": region.get("id"),
        "label": region.get("label"),
        "verdict": region.get("verdict") or "SUSPICIOUS",
        "confidence": round(confidence, 2),
        "detector_contributions": detector_rows,
        "technical_explanation": region.get("technical_explanation") or region.get("reason") or "",
        "plain_english_explanation": region.get("plain_english_explanation") or "",
        "evidence": region.get("evidence") or [],
        "global_signals": {
            "ela": signals.get("ela_score"),
            "wavelet": signals.get("wavelet_score"),
            "edge_density": signals.get("edge_density"),
            "copy_move": signals.get("copy_move_score"),
        },
    }


def attach_region_explanations(
    regions: List[Dict[str, Any]],
    analysis: Dict[str, Any],
) -> List[Dict[str, Any]]:
    enriched = []
    for reg in regions:
        explanation = explain_region(reg, analysis)
        enriched.append({**reg, "explainability": explanation, "investigation": _format_investigation(explanation)})
    return enriched


def _format_investigation(exp: Dict[str, Any]) -> str:
    lines = [
        f"Region: {exp.get('label')}",
        f"Verdict: {exp.get('verdict')}",
        f"Confidence: {exp.get('confidence')}%",
        "",
        "Detector Contributions:",
    ]
    for row in exp.get("detector_contributions") or []:
        status = "ACTIVE" if row.get("active") else "inactive"
        lines.append(f"  • {row['detector']}: {row['contribution']:.3f} ({status})")
    if exp.get("technical_explanation"):
        lines.extend(["", "Technical:", exp["technical_explanation"]])
    if exp.get("plain_english_explanation"):
        lines.extend(["", "Summary:", exp["plain_english_explanation"]])
    return "\n".join(lines)
