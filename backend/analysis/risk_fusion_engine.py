"""
Weighted risk fusion engine — combines all forensic signals with explainability.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# Module weights (sum ≈ 1.0)
FUSION_WEIGHTS: Dict[str, float] = {
    "metadata": 0.08,
    "ela": 0.14,
    "wavelet": 0.10,
    "copy_move": 0.14,
    "edge": 0.05,
    "ai_generation": 0.18,
    "ocr": 0.06,
    "document_consistency": 0.07,
    "deepfake": 0.10,
    "tampering": 0.08,
}


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def _score_label(score_pct: float) -> str:
    if score_pct >= 70:
        return "HIGH"
    if score_pct >= 45:
        return "MEDIUM"
    if score_pct >= 20:
        return "LOW"
    return "MINIMAL"


def compute_fusion_risk(
    signals: Dict[str, Any],
    *,
    profile: str = "natural_photo",
    ai_generation: Optional[Dict[str, Any]] = None,
    tampering_score: float = 0.0,
    deepfake_probability: float = 0.0,
    face_authenticity_score: float = 1.0,
    ocr_risk: float = 0.0,
    document_consistency: float = 0.0,
    multispectral_score: float = 0.0,
) -> Dict[str, Any]:
    """
    Fuse all forensic modules into actionable scores with explainability.

    Returns authenticity_score, manipulation_score, ai_generation_score,
    overall_fraud_risk, confidence, explainability, verdict.
    """
    ai_det = ai_generation or {}
    ai_score = _clamp(ai_det.get("ai_generated_probability", signals.get("gan_ai_score", 0)))
    synthetic_conf = _clamp(ai_det.get("synthetic_artifact_confidence", ai_score))

    components = {
        "metadata": _clamp(max(
            signals.get("metadata_risk_score", 0),
            1.0 if signals.get("metadata_suspicious") else 0.0,
        )),
        "ela": _clamp(signals.get("ela_score", 0)),
        "wavelet": _clamp(signals.get("wavelet_score", 0)),
        "copy_move": _clamp(max(
            signals.get("copy_move_score", 0),
            0.85 if signals.get("copy_move_detected") else 0.0,
        )),
        "edge": _clamp(signals.get("edge_density", 0)),
        "ai_generation": ai_score,
        "ocr": _clamp(ocr_risk),
        "document_consistency": _clamp(document_consistency),
        "deepfake": _clamp(max(deepfake_probability, 1.0 - face_authenticity_score if face_authenticity_score < 0.7 else 0)),
        "tampering": _clamp(tampering_score),
    }

    if multispectral_score > 0:
        components["ela"] = max(components["ela"], _clamp(multispectral_score) * 0.6)

    # Weighted manipulation (excludes AI generation)
    manip_keys = ("ela", "wavelet", "copy_move", "edge", "tampering", "metadata")
    manip_w = sum(FUSION_WEIGHTS[k] for k in manip_keys)
    manipulation = sum(components[k] * FUSION_WEIGHTS[k] for k in manip_keys) / max(manip_w, 0.01)

    ai_w = FUSION_WEIGHTS["ai_generation"]
    deepfake_w = FUSION_WEIGHTS["deepfake"]
    ocr_w = FUSION_WEIGHTS["ocr"] + FUSION_WEIGHTS["document_consistency"]

    overall = (
        manipulation * (manip_w + FUSION_WEIGHTS["tampering"])
        + ai_score * ai_w
        + components["deepfake"] * deepfake_w
        + (ocr_risk * 0.5 + document_consistency * 0.5) * ocr_w
    )
    overall = _clamp(overall)
    overall_pct = round(overall * 100, 2)

    authenticity = round((1.0 - overall) * 100, 2)
    manipulation_pct = round(manipulation * 100, 2)
    ai_pct = round(ai_score * 100, 2)

    explainability: List[str] = _build_explanations(components, ai_det, signals)

    if overall_pct >= 70:
        verdict = "HIGH RISK - LIKELY FORGED OR AI-GENERATED"
    elif overall_pct >= 45:
        verdict = "MEDIUM RISK - SUSPICIOUS"
    elif overall_pct >= 20:
        verdict = "LOW RISK - MINOR ANOMALIES"
    else:
        verdict = "NO SIGNIFICANT ANOMALY DETECTED"

    active = sum(1 for v in components.values() if v >= 0.35)
    confidence = round(min(99.0, 50 + active * 8 + (10 if overall_pct >= 60 else 0)), 2)

    return {
        "overall_fraud_risk": overall_pct,
        "risk_score": overall_pct,
        "authenticity_score": authenticity,
        "manipulation_score": manipulation_pct,
        "ai_generation_score": ai_pct,
        "synthetic_artifact_confidence": round(synthetic_conf * 100, 2),
        "confidence": confidence,
        "verdict": verdict,
        "risk_level": _score_label(overall_pct),
        "component_scores": {k: round(v, 4) for k, v in components.items()},
        "fusion_weights": FUSION_WEIGHTS,
        "explainability": explainability,
        "profile": profile,
    }


def _build_explanations(
    components: Dict[str, float],
    ai_det: Dict[str, Any],
    signals: Dict[str, Any],
) -> List[str]:
    reasons: List[str] = []
    thresholds = [
        ("copy_move", 0.35, "Copy-move forgery indicators detected — duplicated regions found via feature matching."),
        ("ela", 0.40, "Error Level Analysis shows compression inconsistencies suggesting editing."),
        ("wavelet", 0.35, "Wavelet frequency analysis reveals manipulation artifacts."),
        ("metadata", 0.30, "EXIF/metadata anomalies suggest the file was edited or re-saved."),
        ("edge", 0.40, "Edge density patterns are inconsistent with an unmodified photograph."),
        ("tampering", 0.35, "Neural tampering detector flagged suspicious regions."),
        ("deepfake", 0.30, "Face forensics indicates possible deepfake or synthetic face manipulation."),
        ("ai_generation", 0.35, None),
        ("ocr", 0.30, "OCR/text consistency checks found anomalies."),
        ("document_consistency", 0.30, "Document layout/font/spacing consistency issues detected."),
    ]
    for key, thresh, default_msg in thresholds:
        if components.get(key, 0) >= thresh:
            if key == "ai_generation":
                gen = ai_det.get("generator_prediction", "AI generator")
                prob = ai_det.get("ai_generated_probability", components[key])
                reasons.append(
                    f"AI-generated imagery detected ({prob:.0%} probability). "
                    f"Most likely source: {gen}."
                )
            else:
                reasons.append(default_msg)

    if signals.get("copy_move_detected") and not any("Copy-move" in r for r in reasons):
        reasons.append(
            f"Copy-move detection: {signals.get('matched_points', 0)} matched points, "
            f"{signals.get('ransac_inliers', signals.get('inliers', 0))} RANSAC inliers."
        )

    if not reasons:
        reasons.append("No significant forensic anomalies exceeded detection thresholds.")

    return reasons
