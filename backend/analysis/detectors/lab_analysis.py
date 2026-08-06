"""LAB color space anomaly detector."""

from __future__ import annotations

import cv2
import numpy as np

from backend.analysis.detectors._utils import anomaly_score_from_tiles, load_working_bgr, tile_means
from backend.analysis.detectors.base import DetectorResult, failed_result, make_result


def analyze_lab(image_path: str) -> DetectorResult:
    try:
        bgr = load_working_bgr(image_path)
        lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
        l_ch, a_ch, b_ch = cv2.split(lab)

        l_score = anomaly_score_from_tiles(tile_means(l_ch))
        ab_combined = np.sqrt(a_ch.astype(np.float32) ** 2 + b_ch.astype(np.float32) ** 2)
        ab_score = anomaly_score_from_tiles(tile_means(ab_combined))
        score = min(1.0, l_score * 0.55 + ab_score * 0.45)

        if score >= 0.5:
            expl = "LAB analysis shows perceptual lightness/chroma inconsistency — possible background replacement or object insertion."
        elif score >= 0.28:
            expl = "Moderate LAB color-space anomalies between regions."
        else:
            expl = "LAB perceptual color channels are consistent."

        return make_result("lab", score, confidence=0.74, explanation=expl)
    except Exception as exc:
        return failed_result("lab", str(exc))
