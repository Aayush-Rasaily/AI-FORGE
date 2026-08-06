"""
GAN / AI generator detection — parallel CNN, ViT, CLIP, frequency fusion.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional

from backend.analysis.gan_detection.clip_detector import GENERATOR_LABELS, detect_clip
from backend.analysis.gan_detection.cnn_detector import detect_cnn
from backend.analysis.gan_detection.frequency_fingerprint import detect_frequency_fingerprint
from backend.analysis.gan_detection.vit_detector import detect_vit
from backend.utils.hardware import get_device_info

logger = logging.getLogger("ai_forge.gan_detection")

DETECTOR_WEIGHTS = {
    "cnn": 0.22,
    "vit": 0.22,
    "clip": 0.36,
    "frequency": 0.20,
}

DETECTORS = {
    "cnn": detect_cnn,
    "vit": detect_vit,
    "clip": detect_clip,
    "frequency": detect_frequency_fingerprint,
}


def fuse_gan_results(results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    if not results:
        return {
            "ai_generated_score": 0.0,
            "confidence": 0.0,
            "generator_prediction": "Unknown",
            "reasoning": "No GAN detector results.",
        }

    weighted_sum = 0.0
    weight_total = 0.0
    conf_sum = 0.0
    explanations: List[str] = []

    for name, result in results.items():
        w = DETECTOR_WEIGHTS.get(name, 0.1)
        score = float(result.get("score", 0))
        conf = float(result.get("confidence", 0.5))
        effective = w * conf
        weighted_sum += score * effective
        weight_total += effective
        conf_sum += conf * w
        if score >= 0.3 and result.get("explanation"):
            explanations.append(f"{name.upper()}: {result['explanation']}")

    ai_score = weighted_sum / weight_total if weight_total > 0 else 0.0
    confidence = conf_sum / sum(DETECTOR_WEIGHTS.values())

    clip = results.get("clip", {})
    generator = clip.get("generator_label") or GENERATOR_LABELS.get(
        clip.get("generator", ""), "Unknown"
    )
    generator_scores = clip.get("generator_scores", {})

    if ai_score >= 0.6:
        summary = f"High probability of AI-generated imagery. Predicted generator: {generator}."
    elif ai_score >= 0.35:
        summary = f"Moderate AI-generation indicators. Most likely: {generator}."
    else:
        summary = "Image appears consistent with authentic photography."
        if clip.get("generator") == "authentic":
            generator = "Authentic / Not AI-Generated"

    reasoning = summary
    if explanations:
        reasoning += " " + " | ".join(explanations[:3])

    return {
        "ai_generated_score": round(ai_score, 4),
        "ai_generated_score_pct": round(ai_score * 100, 2),
        "confidence": round(confidence, 4),
        "generator_prediction": generator,
        "generator_key": clip.get("generator", "unknown"),
        "generator_scores": generator_scores,
        "reasoning": reasoning,
        "detector_weights": DETECTOR_WEIGHTS,
    }


def analyze_gan_image(
    image_path: str,
    progress: Optional[Callable[[str, str, float], None]] = None,
    max_workers: int = 4,
) -> Dict[str, Any]:
    """Run all GAN detectors in parallel."""
    device_info = get_device_info()
    results: Dict[str, Dict[str, Any]] = {}

    def _emit(name: str, status: str, elapsed: float = 0.0):
        if progress:
            progress(name, status, elapsed)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fn, image_path): name for name, fn in DETECTORS.items()}
        for future in as_completed(futures):
            name = futures[future]
            _emit(f"gan_{name}", "running")
            try:
                results[name] = future.result()
                _emit(f"gan_{name}", "completed")
            except Exception as exc:
                logger.warning("GAN detector %s failed: %s", name, exc)
                results[name] = {
                    "score": 0.0,
                    "confidence": 0.2,
                    "explanation": str(exc),
                }
                _emit(f"gan_{name}", "failed")

    fusion = fuse_gan_results(results)
    return {
        "success": True,
        "device": device_info.get("device", "cpu"),
        "detectors": results,
        "fusion": fusion,
        "ai_generated_score": fusion["ai_generated_score"],
        "confidence": fusion["confidence"],
        "generator_prediction": fusion["generator_prediction"],
        "generator_scores": fusion["generator_scores"],
        "reasoning": fusion["reasoning"],
    }
