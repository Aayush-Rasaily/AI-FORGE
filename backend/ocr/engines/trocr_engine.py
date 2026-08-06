"""TrOCR (Transformer OCR) engine."""

from __future__ import annotations

import time
from functools import lru_cache
from typing import Any, Dict

import cv2
import numpy as np

from backend.ocr.engines.base import detection_from_box, empty_result, make_result
from backend.utils.hardware import get_torch_device


@lru_cache(maxsize=1)
def _get_trocr():
    import torch
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel

    device = torch.device(get_torch_device())
    model_name = "microsoft/trocr-base-printed"
    processor = TrOCRProcessor.from_pretrained(model_name)
    model = VisionEncoderDecoderModel.from_pretrained(model_name).eval().to(device)
    return processor, model, device


def run_trocr(image_path: str) -> Dict[str, Any]:
    start = time.perf_counter()
    try:
        import torch
        from PIL import Image

        processor, model, device = _get_trocr()
        image = Image.open(image_path).convert("RGB")

        pixel_values = processor(images=image, return_tensors="pt").pixel_values.to(device)
        with torch.no_grad():
            generated_ids = model.generate(pixel_values)
        text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()

        # Full-page TrOCR — single detection covering image
        arr = np.array(image)
        h, w = arr.shape[:2]
        box = [[0, 0], [w, 0], [w, h], [0, h]]
        det = detection_from_box(box, text, 0.82)
        detections = [det] if det else []

        elapsed = (time.perf_counter() - start) * 1000
        return make_result("trocr", detections, text, detected_language="en", elapsed_ms=elapsed)
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        result = empty_result("trocr", str(exc))
        result["elapsed_ms"] = elapsed
        return result
