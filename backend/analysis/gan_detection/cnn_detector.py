"""
CNN-based synthetic image detector using EfficientNet embeddings.
"""

from __future__ import annotations

from typing import Any, Dict

from backend.analysis.ml_models import _load_rgb_image, get_efficientnet_bundle, patch_embedding_variance


def detect_cnn(image_path: str) -> Dict[str, Any]:
    bundle = get_efficientnet_bundle()
    if not bundle:
        return {
            "score": 0.0,
            "confidence": 0.3,
            "method": "unavailable",
            "explanation": "CNN backbone unavailable.",
        }

    rgb = _load_rgb_image(image_path)
    variance = patch_embedding_variance(bundle, rgb)
    score = min(1.0, max(0.0, variance * 2.2))

    if score >= 0.55:
        expl = "CNN embeddings show patch-level inconsistency typical of AI-generated imagery."
    elif score >= 0.3:
        expl = "Moderate CNN embedding variance suggests possible synthetic generation."
    else:
        expl = "CNN embedding distribution appears consistent with natural photography."

    return {
        "score": round(score, 4),
        "confidence": 0.76,
        "method": bundle["name"],
        "explanation": expl,
        "embedding_variance": round(variance, 4),
    }
