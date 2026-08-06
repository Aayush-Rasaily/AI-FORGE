"""Common OCR result contract."""

from __future__ import annotations

from typing import Any, Dict, List


def empty_result(engine: str, error: str = "") -> Dict[str, Any]:
    return {
        "engine": engine,
        "success": False,
        "full_text": "",
        "text": "",
        "detections": [],
        "character_confidence": 0.0,
        "word_confidence": 0.0,
        "layout_confidence": 0.0,
        "detected_language": "unknown",
        "elapsed_ms": 0.0,
        "error": error or "Engine unavailable",
    }


def make_result(
    engine: str,
    detections: List[Dict[str, Any]],
    full_text: str,
    *,
    detected_language: str = "en",
    layout_confidence: float | None = None,
    elapsed_ms: float = 0.0,
) -> Dict[str, Any]:
    if not detections:
        return {
            "engine": engine,
            "success": bool(full_text.strip()),
            "full_text": full_text,
            "text": full_text,
            "detections": [],
            "character_confidence": 0.5 if full_text.strip() else 0.0,
            "word_confidence": 0.5 if full_text.strip() else 0.0,
            "layout_confidence": layout_confidence or 0.3,
            "detected_language": detected_language,
            "elapsed_ms": elapsed_ms,
            "error": None,
        }

    confs = [float(d.get("confidence", 0.5)) for d in detections]
    word_conf = sum(confs) / len(confs)
    char_conf = word_conf  # proxy when per-char scores unavailable

    # Layout: bbox coverage consistency
    if layout_confidence is None:
        areas = [float(d.get("width", 0)) * float(d.get("height", 0)) for d in detections]
        layout_confidence = min(1.0, len(detections) / 20.0) * (0.5 + word_conf * 0.5)

    return {
        "engine": engine,
        "success": True,
        "full_text": full_text,
        "text": full_text,
        "detections": detections,
        "character_confidence": round(char_conf, 4),
        "word_confidence": round(word_conf, 4),
        "layout_confidence": round(float(layout_confidence), 4),
        "detected_language": detected_language,
        "elapsed_ms": round(elapsed_ms, 2),
        "error": None,
    }


def normalize_bbox(box: Any) -> List[List[float]]:
    if isinstance(box, list) and box and isinstance(box[0], (list, tuple)):
        return [[float(p[0]), float(p[1])] for p in box]
    return []


def detection_from_box(box: Any, text: str, confidence: float) -> Dict[str, Any]:
    bbox = normalize_bbox(box)
    if not bbox:
        return {}
    x_coords = [p[0] for p in bbox]
    y_coords = [p[1] for p in bbox]
    return {
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
    }


def parse_raw_detections(raw: List[Any]) -> tuple[List[Dict[str, Any]], str]:
    detections: List[Dict[str, Any]] = []
    parts: List[str] = []
    for item in raw:
        if len(item) < 3:
            continue
        det = detection_from_box(item[0], item[1], item[2])
        if det:
            detections.append(det)
            parts.append(det["text"])
    return detections, " ".join(parts)
