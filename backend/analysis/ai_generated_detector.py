"""
Dedicated AI-generated image detector — CLIP/ViT/CNN ensemble.

Detects imagery from ChatGPT, DALL-E, Midjourney, Flux, Stable Diffusion, etc.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from backend.analysis.gan_detection.engine import analyze_gan_image

logger = logging.getLogger("ai_forge.ai_generated")


def detect_ai_generated_image(image_path: str) -> Dict[str, Any]:
    """
    Run dedicated AI-generation detection.

    Returns:
        ai_generated_probability (0–1)
        human_photo_probability (0–1)
        synthetic_artifact_confidence (0–1)
        generator_prediction
        reasoning
        detectors (full breakdown)
    """
    try:
        gan = analyze_gan_image(image_path)
    except Exception as exc:
        logger.warning("AI generation detection failed: %s", exc)
        return _empty_result(str(exc))

    fusion = gan.get("fusion") or gan
    detectors = gan.get("detectors") or {}

    ai_prob = float(fusion.get("ai_generated_score", gan.get("ai_generated_score", 0)))
    ai_prob = max(0.0, min(1.0, ai_prob))
    human_prob = max(0.0, min(1.0, 1.0 - ai_prob))

    clip = detectors.get("clip") or {}
    freq = detectors.get("frequency") or {}
    vit = detectors.get("vit") or {}

    synthetic_signals = [
        float(freq.get("score", 0)),
        float(vit.get("score", 0)),
        float(clip.get("score", 0)) if clip.get("generator") != "authentic" else 0.0,
    ]
    synthetic_conf = max(synthetic_signals) if synthetic_signals else ai_prob * 0.8

    generator = fusion.get("generator_prediction") or gan.get("generator_prediction", "Unknown")
    reasoning = fusion.get("reasoning") or gan.get("reasoning", "")

    top_generators = clip.get("generator_scores") or {}
    if top_generators and ai_prob >= 0.35:
        top3 = sorted(top_generators.items(), key=lambda x: x[1], reverse=True)[:3]
        gen_hint = ", ".join(f"{k} ({v:.0%})" for k, v in top3)
        reasoning = f"{reasoning} Top generator matches: {gen_hint}."

    return {
        "success": True,
        "module": "ai_generated_detection",
        "ai_generated_probability": round(ai_prob, 4),
        "human_photo_probability": round(human_prob, 4),
        "synthetic_artifact_confidence": round(synthetic_conf, 4),
        "generator_prediction": generator,
        "generator_scores": top_generators,
        "confidence": float(fusion.get("confidence", gan.get("confidence", 0.5))),
        "reasoning": reasoning.strip(),
        "detectors": detectors,
        "fusion": fusion,
    }


def _empty_result(error: str) -> Dict[str, Any]:
    return {
        "success": False,
        "module": "ai_generated_detection",
        "ai_generated_probability": 0.0,
        "human_photo_probability": 1.0,
        "synthetic_artifact_confidence": 0.0,
        "generator_prediction": "Unknown",
        "confidence": 0.0,
        "reasoning": f"AI detection unavailable: {error}",
        "detectors": {},
    }
