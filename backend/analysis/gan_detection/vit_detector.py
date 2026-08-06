"""
Vision Transformer synthetic image detector.
"""

from __future__ import annotations

from typing import Any, Dict

from backend.analysis.ml_models import _load_rgb_image, get_vit_bundle, patch_embedding_variance


def detect_vit(image_path: str) -> Dict[str, Any]:
    bundle = get_vit_bundle()
    if not bundle:
        return {
            "score": 0.0,
            "confidence": 0.3,
            "method": "unavailable",
            "explanation": "ViT backbone unavailable.",
        }

    rgb = _load_rgb_image(image_path)
    variance = patch_embedding_variance(bundle, rgb)
    score = min(1.0, max(0.0, variance * 2.0))

    if score >= 0.55:
        expl = "ViT attention patterns reveal global inconsistencies common in diffusion-generated images."
    elif score >= 0.3:
        expl = "ViT embedding variance indicates moderate synthetic-generation risk."
    else:
        expl = "ViT features align with authentic photographic structure."

    return {
        "score": round(score, 4),
        "confidence": 0.74,
        "method": bundle["name"],
        "explanation": expl,
        "embedding_variance": round(variance, 4),
    }
