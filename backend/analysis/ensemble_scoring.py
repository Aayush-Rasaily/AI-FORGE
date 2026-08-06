"""
Weighted ensemble scoring for image forensics — adaptive by image profile.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


# Base weights per user spec
BASE_WEIGHTS: Dict[str, float] = {
    "ela": 0.35,
    "copy_move": 0.30,
    "wavelet": 0.20,
    "metadata": 0.10,
    "edge": 0.05,
}

# Profile adjustments — increase sensitivity for manipulation-prone types
PROFILE_BOOSTS: Dict[str, Dict[str, float]] = {
    "natural_photo": {
        "ela": 0.05,
        "copy_move": 0.05,
        "wavelet": 0.0,
    },
    "text_document": {
        "metadata": 0.05,
        "ela": 0.03,
    },
    "scanned_document": {
        "ela": 0.08,
        "copy_move": 0.05,
    },
    "mixed": {},
}


def compute_ensemble_risk(
    signals: Dict[str, Any],
    *,
    profile: str = "natural_photo",
    tampering_score: float = 0.0,
    noise_inconsistency: float = 0.0,
    multispectral_score: float = 0.0,
    multispectral_confidence: float = 0.0,
    gan_ai_score: float = 0.0,
    gan_confidence: float = 0.0,
    deepfake_probability: float = 0.0,
    face_authenticity_score: float = 1.0,
) -> Dict[str, Any]:
    """
    Compute weighted ensemble risk score (0–100) with boosted sensitivity
    for edits, clone regions, compression anomalies, etc.
    """
    ela = min(1.0, float(signals.get("ela_score", 0)))
    copy_move = min(1.0, float(signals.get("copy_move_score", 0)))
    if signals.get("copy_move_detected"):
        copy_move = max(copy_move, 0.85)
    wavelet = min(1.0, float(signals.get("wavelet_score", 0)))
    metadata = 1.0 if signals.get("metadata_suspicious") else min(1.0, float(signals.get("metadata_score", 0)))
    edge = min(1.0, float(signals.get("edge_density", 0)))

    weights = dict(BASE_WEIGHTS)
    for key, boost in PROFILE_BOOSTS.get(profile, {}).items():
        weights[key] = weights.get(key, 0) + boost

    # Boost for tampering CNN / hybrid detector
    if tampering_score > 0.35:
        weights["ela"] = weights.get("ela", 0) + 0.05
        weights["copy_move"] = weights.get("copy_move", 0) + 0.05

    # Noise inconsistency — JPEG quantization / resave attacks
    if noise_inconsistency > 0.3:
        weights["wavelet"] = weights.get("wavelet", 0) + 0.04
        weights["ela"] = weights.get("ela", 0) + 0.03

    total_w = sum(weights.values()) or 1.0
    weighted = (
        ela * weights["ela"]
        + copy_move * weights["copy_move"]
        + wavelet * weights["wavelet"]
        + metadata * weights["metadata"]
        + edge * weights["edge"]
    ) / total_w

    # Incorporate multi-spectral + JPEG block fusion (professional engine)
    if multispectral_score > 0:
        ms_weight = 0.22 * max(0.5, multispectral_confidence)
        weighted = weighted * (1 - ms_weight) + multispectral_score * ms_weight

    # GAN / AI generator detection
    if gan_ai_score > 0:
        gan_weight = 0.18 * max(0.5, gan_confidence)
        weighted = weighted * (1 - gan_weight) + gan_ai_score * gan_weight

    # Face forensics / deepfake probability
    if deepfake_probability > 0.2:
        df_weight = 0.15
        weighted = weighted * (1 - df_weight) + deepfake_probability * df_weight
    elif face_authenticity_score < 0.7:
        weighted = max(weighted, (1.0 - face_authenticity_score) * 0.85)

    # Incorporate tampering module (generative AI, deepfake signals)
    if tampering_score > 0:
        weighted = weighted * 0.75 + tampering_score * 0.25

    # Sensitivity boost for high individual signals (object removal/insertion)
    peak = max(ela, copy_move, wavelet, tampering_score)
    if peak >= 0.55:
        weighted = max(weighted, peak * 0.9)

    risk_pct = round(min(100.0, weighted * 100), 2)

    if risk_pct >= 70:
        verdict = "HIGH RISK - LIKELY FORGED"
    elif risk_pct >= 45:
        verdict = "MEDIUM RISK - SUSPICIOUS"
    elif risk_pct >= 20:
        verdict = "LOW RISK - MINOR ANOMALIES"
    else:
        verdict = "NO SIGNIFICANT ANOMALY DETECTED"

    return {
        "risk_score": risk_pct,
        "forensic_score": round(weighted, 4),
        "verdict": verdict,
        "ensemble_weights": {k: round(v / total_w, 4) for k, v in weights.items()},
        "component_scores": {
            "ela": round(ela, 4),
            "copy_move": round(copy_move, 4),
            "wavelet": round(wavelet, 4),
            "metadata": round(metadata, 4),
            "edge": round(edge, 4),
            "tampering": round(tampering_score, 4),
            "multispectral": round(multispectral_score, 4),
            "gan_ai": round(gan_ai_score, 4),
            "deepfake": round(deepfake_probability, 4),
            "face_authenticity": round(face_authenticity_score, 4),
        },
        "multispectral_confidence": round(multispectral_confidence, 4),
        "gan_confidence": round(gan_confidence, 4),
    }
