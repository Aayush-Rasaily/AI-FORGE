"""
Legacy single-engine OCR fallback (PaddleOCR → RapidOCR → EasyOCR).
Preserved for backward compatibility when multi-engine consensus fails.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any, Dict, Tuple

from backend.utils.hardware import get_device_info

logger = logging.getLogger("ai_forge.ocr.legacy")

_ENGINE_LOCK = threading.Lock()
_ENGINE_NAME = None
_ENGINE = None


def _init_engine() -> Tuple[str, Any]:
    global _ENGINE_NAME, _ENGINE
    with _ENGINE_LOCK:
        if _ENGINE is not None:
            return _ENGINE_NAME or "easyocr", _ENGINE

        gpu = get_device_info().get("cuda_available", False)

        try:
            from paddleocr import PaddleOCR
            _ENGINE = PaddleOCR(use_angle_cls=False, lang="en", use_gpu=gpu, show_log=False)
            _ENGINE_NAME = "paddleocr"
            return _ENGINE_NAME, _ENGINE
        except ImportError:
            pass

        try:
            from rapidocr_onnxruntime import RapidOCR
            _ENGINE = RapidOCR()
            _ENGINE_NAME = "rapidocr"
            return _ENGINE_NAME, _ENGINE
        except ImportError:
            pass

        import easyocr
        _ENGINE = easyocr.Reader(["en"], gpu=gpu)
        _ENGINE_NAME = "easyocr"
        return _ENGINE_NAME, _ENGINE


def _normalize_bbox(box):
    if isinstance(box, list) and box and isinstance(box[0], (list, tuple)):
        return [[float(p[0]), float(p[1])] for p in box]
    return []


def _parse_detections(raw):
    detections = []
    full_text = []
    for item in raw:
        if len(item) < 3:
            continue
        bbox, text, confidence = item[0], item[1], item[2]
        bbox = _normalize_bbox(bbox)
        if not bbox:
            continue
        x_coords = [p[0] for p in bbox]
        y_coords = [p[1] for p in bbox]
        detections.append({
            "text": str(text),
            "confidence": float(confidence),
            "bbox": bbox,
            "left": min(x_coords),
            "right": max(x_coords),
            "top": min(y_coords),
            "bottom": max(y_coords),
            "width": max(x_coords) - min(x_coords),
            "height": max(y_coords) - min(y_coords),
            "center_x": sum(x_coords) / len(x_coords),
            "center_y": sum(y_coords) / len(y_coords),
        })
        full_text.append(str(text))
    return detections, " ".join(full_text)


def run_legacy_ocr(image_path: str) -> Dict[str, Any]:
    engine_name, engine = _init_engine()
    path = str(Path(image_path).resolve())

    if engine_name == "paddleocr":
        result = engine.ocr(path, cls=False) or []
        rows = []
        for line in result:
            if line:
                rows.extend(line)
        parsed = [(r[0], r[1][0], r[1][1]) for r in rows if r and len(r) >= 2]
    elif engine_name == "rapidocr":
        result, _ = engine(path)
        parsed = [(r[0], r[1], r[2]) for r in (result or [])]
    else:
        parsed = engine.readtext(path)

    detections, full_text = _parse_detections(parsed)
    confs = [d["confidence"] for d in detections] if detections else [0.5]
    wc = sum(confs) / len(confs)
    return {
        "full_text": full_text,
        "text": full_text,
        "detections": detections,
        "word_count": len(full_text.split()),
        "engine": engine_name,
        "word_confidence": wc,
        "character_confidence": wc,
        "layout_confidence": min(1.0, len(detections) / 15.0) if detections else 0.3,
        "detected_language": "en",
        "success": bool(full_text or detections),
    }
