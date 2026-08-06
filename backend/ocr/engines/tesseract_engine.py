"""Tesseract OCR engine."""

from __future__ import annotations

import time
from typing import Any, Dict

from backend.ocr.engines.base import detection_from_box, empty_result, make_result


def run_tesseract(image_path: str) -> Dict[str, Any]:
    start = time.perf_counter()
    try:
        import pytesseract
        from PIL import Image

        img = Image.open(image_path).convert("RGB")
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

        detections = []
        parts = []

        for i, text in enumerate(data.get("text", [])):
            text = (text or "").strip()
            if not text:
                continue
            conf = float(data["conf"][i])
            if conf < 0:
                conf = 50.0
            conf /= 100.0
            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            box = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]
            det = detection_from_box(box, text, conf)
            if det:
                detections.append(det)
                parts.append(text)

        full_text = " ".join(parts)
        try:
            osd = pytesseract.image_to_osd(img)
            detected_lang = str(osd.get("script", "Latin")).lower()
        except Exception:
            detected_lang = "en"

        elapsed = (time.perf_counter() - start) * 1000
        return make_result(
            "tesseract",
            detections,
            full_text,
            detected_language=detected_lang,
            elapsed_ms=elapsed,
        )
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        result = empty_result("tesseract", str(exc))
        result["elapsed_ms"] = elapsed
        return result
