"""YCbCr chroma subsampling and block artifact detector."""

from __future__ import annotations

import cv2
import numpy as np

from backend.analysis.detectors._utils import anomaly_score_from_tiles, boundary_grid_score, load_working_bgr, tile_means
from backend.analysis.detectors.base import DetectorResult, failed_result, make_result


def analyze_ycbcr(image_path: str) -> DetectorResult:
    try:
        bgr = load_working_bgr(image_path)
        ycbcr = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
        y, cr, cb = cv2.split(ycbcr)

        cb_score = anomaly_score_from_tiles(tile_means(cb))
        cr_score = anomaly_score_from_tiles(tile_means(cr))
        grid = boundary_grid_score(y, period=8)
        score = min(1.0, cb_score * 0.35 + cr_score * 0.35 + grid * 0.30)

        if score >= 0.5:
            expl = "YCbCr chroma planes show block-aligned inconsistencies — indicative of JPEG recompression or splice at 8×8 boundaries."
        elif score >= 0.28:
            expl = "Moderate YCbCr chroma variation detected."
        else:
            expl = "YCbCr chroma channels appear consistent."

        return make_result("ycbcr", score, confidence=0.71, explanation=expl, grid_score=round(grid, 4))
    except Exception as exc:
        return failed_result("ycbcr", str(exc))
