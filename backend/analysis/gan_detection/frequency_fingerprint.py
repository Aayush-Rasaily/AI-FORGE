"""
Frequency-domain fingerprints for diffusion / GAN upscaling artifacts.
"""

from __future__ import annotations

from typing import Any, Dict

import cv2
import numpy as np

from backend.analysis.ml_models import _load_rgb_image


def _radial_spectrum(gray: np.ndarray) -> np.ndarray:
    f = np.fft.fft2(gray.astype(np.float32))
    fshift = np.fft.fftshift(f)
    magnitude = np.log1p(np.abs(fshift))
    h, w = magnitude.shape
    cy, cx = h // 2, w // 2
    y, x = np.ogrid[:h, :w]
    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2).astype(int)
    max_r = min(cy, cx)
    profile = np.zeros(max_r)
    counts = np.zeros(max_r)
    for radius in range(max_r):
        mask = r == radius
        if np.any(mask):
            profile[radius] = float(np.mean(magnitude[mask]))
            counts[radius] = 1
    return profile


def detect_frequency_fingerprint(image_path: str) -> Dict[str, Any]:
    rgb = _load_rgb_image(image_path, max_side=768)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    profile = _radial_spectrum(gray)

    if len(profile) < 16:
        return {"score": 0.0, "confidence": 0.4, "explanation": "Insufficient frequency data."}

    # Diffusion models often show periodic high-frequency peaks
    high_band = profile[len(profile) // 3:]
    low_band = profile[: len(profile) // 3]
    high_energy = float(np.mean(high_band))
    low_energy = float(np.mean(low_band)) + 1e-6
    ratio = high_energy / low_energy

    # Grid periodicity at 8px (upscaler artifacts)
    tile = 64
    grid_scores = []
    h, w = gray.shape
    for y in range(0, h - tile, tile):
        for x in range(0, w - tile, tile):
            block = gray[y: y + tile, x: x + tile]
            f = np.fft.fft2(block.astype(np.float32))
            mag = np.abs(np.fft.fftshift(f))
            cy, cx = tile // 2, tile // 2
            grid_scores.append(float(mag[cy, cx + 8] + mag[cy + 8, cx]) / (float(np.sum(mag)) + 1e-6))

    grid_peak = float(np.mean(grid_scores)) if grid_scores else 0.0
    score = min(1.0, max(0.0, (ratio - 0.85) * 0.6 + grid_peak * 8.0))

    if score >= 0.5:
        expl = (
            "Frequency fingerprint shows diffusion upscaler grid peaks and "
            "abnormal high-frequency radial energy — consistent with AI generation."
        )
    elif score >= 0.28:
        expl = "Moderate frequency-domain anomalies detected."
    else:
        expl = "Frequency spectrum matches typical camera-captured imagery."

    return {
        "score": round(score, 4),
        "confidence": 0.71,
        "method": "fft_fingerprint",
        "explanation": expl,
        "radial_ratio": round(ratio, 4),
        "grid_peak": round(grid_peak, 6),
    }
