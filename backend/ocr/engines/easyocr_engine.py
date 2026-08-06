"""EasyOCR engine."""

from __future__ import annotations

import time
from functools import lru_cache
from typing import Any, Dict

from backend.ocr.engines.base import empty_result, make_result, parse_raw_detections
from backend.utils.hardware import get_device_info


@lru_cache(maxsize=1)
def _get_reader():
    import easyocr
    gpu = get_device_info().get("cuda_available", False)
    return easyocr.Reader(["en"], gpu=gpu)


def run_easyocr(image_path: str) -> Dict[str, Any]:
    start = time.perf_counter()
    try:
        reader = _get_reader()
        parsed = reader.readtext(str(image_path))
        detections, full_text = parse_raw_detections(parsed)
        elapsed = (time.perf_counter() - start) * 1000
        return make_result("easyocr", detections, full_text, detected_language="en", elapsed_ms=elapsed)
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        result = empty_result("easyocr", str(exc))
        result["elapsed_ms"] = elapsed
        return result
