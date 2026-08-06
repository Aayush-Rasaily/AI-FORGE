"""Frequency domain (FFT) forensic detector."""

from __future__ import annotations

import cv2
import numpy as np

from backend.analysis.detectors._utils import load_working_bgr
from backend.analysis.detectors.base import DetectorResult, failed_result, make_result


def analyze_frequency(image_path: str) -> DetectorResult:
    try:
        bgr = load_working_bgr(image_path)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)

        # Tile FFT analysis for localized frequency anomalies
        tile = 64
        h, w = gray.shape
        high_energy_ratios = []

        for y in range(0, h - tile, tile):
            for x in range(0, w - tile, tile):
                block = gray[y: y + tile, x: x + tile]
                f = np.fft.fft2(block)
                fshift = np.fft.fftshift(f)
                magnitude = np.abs(fshift)
                total = float(np.sum(magnitude)) + 1e-6
                cy, cx = tile // 2, tile // 2
                mask = np.ones((tile, tile), dtype=bool)
                mask[cy - 8: cy + 8, cx - 8: cx + 8] = False
                high = float(np.sum(magnitude[mask]))
                high_energy_ratios.append(high / total)

        if not high_energy_ratios:
            return make_result("frequency", 0.0, 0.5, "Insufficient data for frequency analysis.")

        arr = np.array(high_energy_ratios)
        score = float(min(1.0, np.std(arr) / (np.mean(arr) + 1e-6) * 3.0))

        if score >= 0.5:
            expl = "Frequency-domain analysis reveals uneven high-frequency energy — consistent with sharpening, GAN artifacts, or localized editing."
        elif score >= 0.28:
            expl = "Moderate frequency-domain irregularities detected across tiles."
        else:
            expl = "Frequency spectrum appears consistent across the image."

        return make_result("frequency", score, confidence=0.68, explanation=expl)
    except Exception as exc:
        return failed_result("frequency", str(exc))
