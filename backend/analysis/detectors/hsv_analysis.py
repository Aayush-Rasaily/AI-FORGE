"""HSV color space anomaly detector."""

from __future__ import annotations

import cv2

from backend.analysis.detectors._utils import anomaly_score_from_tiles, load_working_bgr, tile_means
from backend.analysis.detectors.base import DetectorResult, failed_result, make_result


def analyze_hsv(image_path: str) -> DetectorResult:
    try:
        bgr = load_working_bgr(image_path)
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)

        s_score = anomaly_score_from_tiles(tile_means(s))
        v_score = anomaly_score_from_tiles(tile_means(v))
        h_score = anomaly_score_from_tiles(tile_means(h))
        score = min(1.0, s_score * 0.45 + v_score * 0.35 + h_score * 0.20)

        if score >= 0.5:
            expl = "HSV analysis reveals localized saturation or luminance shifts typical of compositing or brush edits."
        elif score >= 0.28:
            expl = "Moderate HSV irregularities detected in regional color statistics."
        else:
            expl = "HSV color distribution appears uniform across the image."

        return make_result("hsv", score, confidence=0.70, explanation=expl)
    except Exception as exc:
        return failed_result("hsv", str(exc))
