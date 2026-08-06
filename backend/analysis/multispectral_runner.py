"""
Run all spectral + JPEG detectors in parallel and fuse results.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional

from backend.analysis.detectors.frequency_analysis import analyze_frequency
from backend.analysis.detectors.hsv_analysis import analyze_hsv
from backend.analysis.detectors.jpeg_block_analysis import analyze_jpeg_blocks
from backend.analysis.detectors.lab_analysis import analyze_lab
from backend.analysis.detectors.rgb_analysis import analyze_rgb
from backend.analysis.detectors.ycbcr_analysis import analyze_ycbcr
from backend.analysis.detectors.base import DetectorResult

logger = logging.getLogger("ai_forge.multispectral")

DETECTOR_WEIGHTS: Dict[str, float] = {
    "rgb": 0.12,
    "hsv": 0.10,
    "lab": 0.14,
    "ycbcr": 0.14,
    "frequency": 0.18,
    "jpeg_block": 0.32,
}

DETECTOR_TASKS = {
    "rgb": analyze_rgb,
    "hsv": analyze_hsv,
    "lab": analyze_lab,
    "ycbcr": analyze_ycbcr,
    "frequency": analyze_frequency,
    "jpeg_block": analyze_jpeg_blocks,
}


def run_multispectral_analysis(
    image_path: str,
    progress: Optional[Callable[[str, str, float], None]] = None,
    max_workers: int = 6,
) -> Dict[str, Any]:
    """Execute all spectral/JPEG detectors concurrently."""
    results: Dict[str, DetectorResult] = {}

    def _emit(name: str, status: str, elapsed: float = 0.0):
        if progress:
            progress(name, status, elapsed)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fn, image_path): name for name, fn in DETECTOR_TASKS.items()}
        for future in as_completed(futures):
            name = futures[future]
            _emit(name, "running")
            try:
                results[name] = future.result()
                _emit(name, "completed")
            except Exception as exc:
                logger.warning("Detector %s failed: %s", name, exc)
                results[name] = {
                    "detector": name,
                    "score": 0.0,
                    "confidence": 0.2,
                    "explanation": f"Detector failed: {exc}",
                }
                _emit(name, "failed")

    fusion = fuse_detector_results(results)
    return {
        "detectors": results,
        "fusion": fusion,
    }


def fuse_detector_results(results: Dict[str, DetectorResult]) -> Dict[str, Any]:
    """
    Weighted voting fusion across all detectors.

    Returns overall_score (0–1), confidence, reasoning.
    """
    if not results:
        return {"overall_score": 0.0, "confidence": 0.0, "reasoning": "No detector results."}

    weighted_sum = 0.0
    weight_total = 0.0
    conf_sum = 0.0
    explanations: List[str] = []

    for name, result in results.items():
        w = DETECTOR_WEIGHTS.get(name, 0.1)
        score = float(result.get("score", 0))
        conf = float(result.get("confidence", 0.5))
        effective_w = w * conf
        weighted_sum += score * effective_w
        weight_total += effective_w
        conf_sum += conf * w
        if score >= 0.35 and result.get("explanation"):
            explanations.append(f"{name.upper()}: {result['explanation']}")

    overall = weighted_sum / weight_total if weight_total > 0 else 0.0
    confidence = conf_sum / sum(DETECTOR_WEIGHTS.get(n, 0.1) for n in results) if results else 0.0

    # Peak-signal boost for strong individual detectors
    peak = max(float(r.get("score", 0)) for r in results.values())
    if peak >= 0.6:
        overall = max(overall, peak * 0.85)

    if overall >= 0.55:
        summary = "Multi-spectral analysis indicates probable image manipulation."
    elif overall >= 0.3:
        summary = "Multi-spectral analysis detected moderate forensic anomalies."
    else:
        summary = "Multi-spectral analysis found no strong manipulation indicators."

    if explanations:
        reasoning = summary + " " + " | ".join(explanations[:4])
    else:
        reasoning = summary

    return {
        "overall_score": round(overall, 4),
        "overall_score_pct": round(overall * 100, 2),
        "confidence": round(confidence, 4),
        "reasoning": reasoning,
        "weights": DETECTOR_WEIGHTS,
        "component_scores": {k: round(float(v.get("score", 0)), 4) for k, v in results.items()},
    }
