"""RGB channel inconsistency detector."""

from __future__ import annotations

import cv2
import numpy as np

from backend.analysis.detectors._utils import anomaly_score_from_tiles, load_working_bgr, tile_means
from backend.analysis.detectors.base import DetectorResult, failed_result, make_result


def analyze_rgb(image_path: str) -> DetectorResult:
    try:
        bgr = load_working_bgr(image_path)
        b, g, r = cv2.split(bgr)
        rb_ratio_tiles = []
        h, w = r.shape
        tile = 32
        for y in range(0, h - tile, tile):
            for x in range(0, w - tile, tile):
                rb = float(np.mean(r[y: y + tile, x: x + tile])) / (
                    float(np.mean(b[y: y + tile, x: x + tile])) + 1e-6
                )
                rb_ratio_tiles.append(rb)

        score = anomaly_score_from_tiles(rb_ratio_tiles)
        r_var = anomaly_score_from_tiles(tile_means(r))
        g_var = anomaly_score_from_tiles(tile_means(g))
        score = min(1.0, score * 0.5 + (r_var + g_var) * 0.25)

        if score >= 0.55:
            expl = "RGB channel balance varies abnormally across regions — possible splicing or localized color adjustment."
        elif score >= 0.3:
            expl = "Moderate RGB inconsistency detected between image regions."
        else:
            expl = "RGB channels appear consistent across the image."

        return make_result("rgb", score, confidence=0.72, explanation=expl)
    except Exception as exc:
        return failed_result("rgb", str(exc))
