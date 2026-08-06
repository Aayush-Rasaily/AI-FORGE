"""PaddleOCR engine."""

from __future__ import annotations

import time
from functools import lru_cache
from typing import Any, Dict

from backend.ocr.engines.base import empty_result, make_result, parse_raw_detections
from backend.utils.hardware import get_device_info


@lru_cache(maxsize=1)
def _get_paddle():
    from paddleocr import PaddleOCR
    gpu = get_device_info().get("cuda_available", False)
    return PaddleOCR(use_angle_cls=False, lang="en", use_gpu=gpu, show_log=False)


def run_paddleocr(image_path: str) -> Dict[str, Any]:
    start = time.perf_counter()
    try:
        engine = _get_paddle()
        result = engine.ocr(str(image_path), cls=False) or []
        rows = []
        for line in result:
            if line:
                rows.extend(line)
        parsed = [(r[0], r[1][0], r[1][1]) for r in rows if r and len(r) >= 2]
        detections, full_text = parse_raw_detections(parsed)
        elapsed = (time.perf_counter() - start) * 1000
        return make_result("paddleocr", detections, full_text, detected_language="en", elapsed_ms=elapsed)
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        result = empty_result("paddleocr", str(exc))
        result["elapsed_ms"] = elapsed
        return result
