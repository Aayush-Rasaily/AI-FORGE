"""
Weighted risk fusion engine — commercial forensic scoring + module voting.

Weights (classic forgery path):
  Copy-Move 30% | ELA 25% | Metadata 15% | Wavelet 10% | Noise 10% | OCR 10%
AI / deepfake / tampering remain additive specialists.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# Primary forensic weights (sum = 1.0 for classic forgery score)
FORENSIC_WEIGHTS: Dict[str, float] = {
    "copy_move": 0.30,
    "ela": 0.25,
    "metadata": 0.15,
    "wavelet": 0.10,
    "noise": 0.10,
    "ocr": 0.10,
}

# Specialist weights blended after classic score
SPECIALIST_WEIGHTS: Dict[str, float] = {
    "ai_generation": 0.35,
    "deepfake": 0.25,
    "tampering": 0.20,
    "document_consistency": 0.12,
    "edge": 0.08,
}

# Backward-compatible alias used by older callers / explainability
FUSION_WEIGHTS: Dict[str, float] = {
    **FORENSIC_WEIGHTS,
    **SPECIALIST_WEIGHTS,
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
    Fuse forensic modules into an actionable fraud score with voting overrides.
    Never returns 'no anomaly' when multiple detectors disagree toward manipulation.
    """
    ai_det = ai_generation or {}
    ai_score = _clamp(ai_det.get("ai_generated_probability", signals.get("gan_ai_score", 0)))
    synthetic_conf = _clamp(ai_det.get("synthetic_artifact_confidence", ai_score))
    noise_score = _clamp(float(signals.get("noise_inconsistency", signals.get("noise_score", 0)) or 0))

    components = {
        "metadata": _clamp(max(
            signals.get("metadata_risk_score", 0),
            signals.get("metadata_score", 0),
            1.0 if signals.get("metadata_suspicious") else 0.0,
        )),
        "ela": _clamp(signals.get("ela_score", 0)),
        "wavelet": _clamp(signals.get("wavelet_score", 0)),
        "copy_move": _clamp(max(
            signals.get("copy_move_score", 0),
            0.85 if signals.get("copy_move_detected") else 0.0,
        )),
        "edge": _clamp(signals.get("edge_density", 0)),
        "noise": noise_score,
        "ai_generation": ai_score,
        "ocr": _clamp(ocr_risk),
        "document_consistency": _clamp(document_consistency),
        "deepfake": _clamp(max(
            deepfake_probability,
            1.0 - face_authenticity_score if face_authenticity_score < 0.7 else 0,
        )),
        "tampering": _clamp(tampering_score),
    }

    if multispectral_score > 0:
        components["ela"] = max(components["ela"], _clamp(multispectral_score) * 0.6)

    # Classic weighted forgery score
    classic = sum(components[k] * FORENSIC_WEIGHTS[k] for k in FORENSIC_WEIGHTS)
    specialist = (
        components["ai_generation"] * SPECIALIST_WEIGHTS["ai_generation"]
        + components["deepfake"] * SPECIALIST_WEIGHTS["deepfake"]
        + components["tampering"] * SPECIALIST_WEIGHTS["tampering"]
        + components["document_consistency"] * SPECIALIST_WEIGHTS["document_consistency"]
        + (components["edge"] if components["edge"] >= 0.55 else 0.0) * SPECIALIST_WEIGHTS["edge"]
    )
    # Blend: classic dominates; specialists can raise risk
    overall = _clamp(classic * 0.72 + specialist * 0.28)
    overall = max(overall, classic)

    # Voting modules (thresholds tuned for commercial sensitivity)
    vote_scores = {
        "ela": components["ela"],
        "wavelet": components["wavelet"],
        "copy_move": components["copy_move"],
        "metadata": components["metadata"],
        "noise": components["noise"],
        "ocr": components["ocr"],
        "tampering": components["tampering"],
        "document_consistency": components["document_consistency"],
        "ai_generation": components["ai_generation"],
        "deepfake": components["deepfake"],
    }
    if components["edge"] >= 0.55:
        vote_scores["edge"] = components["edge"]

    elevated = [k for k, v in vote_scores.items() if v >= 0.28]
    strong = [k for k, v in vote_scores.items() if v >= 0.42]
    consensus: Dict[str, Any] = {
        "elevated_modules": elevated,
        "strong_modules": strong,
        "votes_for_manipulation": len(elevated),
        "votes_cast": len(vote_scores),
    }

    # Explicit triad: ELA + Copy-Move + Noise ⇒ High even if metadata clean
    triad = (
        components["ela"] >= 0.30
        and components["copy_move"] >= 0.30
        and components["noise"] >= 0.28
    )
    if triad:
        overall = max(overall, 0.72)
        consensus["override"] = "ela_copymove_noise_triad"

    # Forensic voting rules
    if len(strong) >= 5 or len(elevated) >= 5:
        overall = max(overall, 0.75)
        consensus["override"] = consensus.get("override") or "force_high_risk_5plus"
    elif len(strong) >= 3 or len(elevated) >= 4:
        overall = max(overall, 0.58)
        consensus["override"] = consensus.get("override") or "force_high_medium_3strong"
    elif len(elevated) >= 3:
        overall = max(overall, 0.48)
        consensus["override"] = consensus.get("override") or "force_medium_3votes"
    elif len(elevated) == 2 and max(components["ela"], components["copy_move"]) >= 0.40:
        overall = max(overall, 0.45)
        consensus["override"] = consensus.get("override") or "force_medium_pair"
    elif len(elevated) == 0 and max(vote_scores.values(), default=0) < 0.22 and ai_score < 0.25:
        overall = min(overall, 0.15)
        consensus["override"] = "force_authentic_cap"

    # Never claim "no anomaly" when any 2+ modules are elevated
    if len(elevated) >= 2:
        overall = max(overall, 0.42)

    overall = _clamp(overall)
    overall_pct = round(overall * 100, 2)

    authenticity = round((1.0 - overall) * 100, 2)
    manipulation_pct = round(classic * 100, 2)
    ai_pct = round(ai_score * 100, 2)

    explainability: List[str] = _build_explanations(components, ai_det, signals)
    if len(elevated) >= 2:
        explainability.insert(
            0,
            f"Module consensus: {len(elevated)} detectors indicate manipulation "
            f"({', '.join(elevated)}).",
        )

    if overall_pct >= 70:
        verdict = "HIGH RISK - LIKELY FORGED OR AI-GENERATED"
    elif overall_pct >= 45:
        verdict = "MEDIUM RISK - SUSPICIOUS"
    elif overall_pct >= 20:
        verdict = "LOW RISK - MINOR ANOMALIES"
    else:
        verdict = "NO SIGNIFICANT ANOMALY DETECTED"

    # Confidence calibration (not random)
    image_conf = _module_confidence([components["ela"], components["wavelet"], components["copy_move"], components["noise"]])
    metadata_conf = _module_confidence([components["metadata"]], completeness=1.0 if signals.get("metadata") or signals.get("metadata_suspicious") is not None else 0.5)
    ocr_conf = _module_confidence([components["ocr"], components["document_consistency"]])
    forgery_conf = _module_confidence([components["copy_move"], components["ela"], components["tampering"]])
    agreement_boost = min(20.0, len(elevated) * 3.5 + len(strong) * 2.0)
    overall_conf = round(min(99.0, 48 + agreement_boost + (12 if overall_pct >= 60 else 0) + image_conf * 0.15), 2)

    confidence_breakdown = {
        "image_confidence": round(image_conf, 1),
        "metadata_confidence": round(metadata_conf, 1),
        "ocr_confidence": round(ocr_conf, 1),
        "forgery_confidence": round(forgery_conf, 1),
        "overall_confidence": overall_conf,
        "agreeing_modules": len(elevated),
    }

    return {
        "overall_fraud_risk": overall_pct,
        "risk_score": overall_pct,
        "authenticity_score": authenticity,
        "manipulation_score": manipulation_pct,
        "ai_generation_score": ai_pct,
        "synthetic_artifact_confidence": round(synthetic_conf * 100, 2),
        "confidence": overall_conf,
        "confidence_breakdown": confidence_breakdown,
        "verdict": verdict,
        "risk_level": _score_label(overall_pct),
        "component_scores": {k: round(v, 4) for k, v in components.items()},
        "fusion_weights": {**FORENSIC_WEIGHTS, **{f"specialist_{k}": v for k, v in SPECIALIST_WEIGHTS.items()}},
        "forensic_weights": FORENSIC_WEIGHTS,
        "explainability": explainability,
        "profile": profile,
        "consensus": consensus,
    }


def _module_confidence(scores: List[float], *, completeness: float = 1.0) -> float:
    if not scores:
        return 40.0
    strength = sum(scores) / len(scores)
    spread = (max(scores) - min(scores)) if len(scores) > 1 else 0.0
    # High agreement (low spread) + signal strength → higher confidence (0–100)
    base = 55.0 + strength * 30.0 - spread * 15.0
    return round(min(99.0, max(20.0, base) * _clamp(completeness)), 1)


def _build_explanations(
    components: Dict[str, float],
    ai_det: Dict[str, Any],
    signals: Dict[str, Any],
) -> List[str]:
    reasons: List[str] = []
    thresholds = [
        ("copy_move", 0.28, "Copy-move forgery indicators detected — duplicated regions found via feature matching."),
        ("ela", 0.30, "Error Level Analysis shows compression inconsistencies suggesting editing."),
        ("wavelet", 0.28, "Wavelet frequency analysis reveals manipulation artifacts."),
        ("noise", 0.28, "Noise inconsistency patterns suggest local editing or splicing."),
        ("metadata", 0.25, "EXIF/metadata anomalies suggest the file was edited or re-saved."),
        ("edge", 0.55, "Edge density patterns are inconsistent with an unmodified photograph."),
        ("tampering", 0.30, "Neural tampering detector flagged suspicious regions."),
        ("deepfake", 0.28, "Face forensics indicates possible deepfake or synthetic face manipulation."),
        ("ai_generation", 0.30, None),
        ("ocr", 0.28, "OCR/text consistency checks found anomalies."),
        ("document_consistency", 0.28, "Document layout/font/spacing consistency issues detected."),
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
