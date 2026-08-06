"""
LayoutLMv3 document layout analysis.

Uses layout-aware embeddings to detect structural inconsistencies.
Falls back to OCR bbox heuristics when the model is unavailable.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

from backend.utils.hardware import get_torch_device

logger = logging.getLogger("ai_forge.layoutlmv3")

_MODEL = None
_PROCESSOR = None


@lru_cache(maxsize=1)
def _load_layoutlmv3():
    global _MODEL, _PROCESSOR
    try:
        import torch
        from transformers import LayoutLMv3Model, LayoutLMv3Processor

        device = get_torch_device()
        model_name = "microsoft/layoutlmv3-base"
        processor = LayoutLMv3Processor.from_pretrained(model_name, apply_ocr=False)
        model = LayoutLMv3Model.from_pretrained(model_name).eval()
        model.to(device)
        _MODEL, _PROCESSOR = model, processor
        return model, processor, torch.device(device)
    except Exception as exc:
        logger.warning("LayoutLMv3 unavailable: %s", exc)
        return None, None, None


def _heuristic_layout_score(image_path: str, ocr_detections: List[Dict[str, Any]]) -> Dict[str, Any]:
    img = cv2.imread(str(image_path))
    if img is None:
        return {"layout_anomaly_score": 0.0, "method": "heuristic", "confidence": 0.4}

    h, w = img.shape[:2]
    if not ocr_detections:
        return {"layout_anomaly_score": 0.2, "method": "heuristic", "confidence": 0.5, "note": "No OCR boxes"}

    # Header zone vs body zone y-position spread
    tops = [d.get("top", 0) for d in ocr_detections]
    heights = [d.get("height", 1) for d in ocr_detections]
    header_words = [d for d in ocr_detections if d.get("top", h) < h * 0.15]
    body_words = [d for d in ocr_detections if d.get("top", 0) >= h * 0.15]

    anomaly = 0.0
    if header_words and body_words:
        h_heights = np.mean([d.get("height", 0) for d in header_words])
        b_heights = np.mean([d.get("height", 0) for d in body_words])
        if b_heights > 0:
            ratio = abs(h_heights - b_heights) / b_heights
            anomaly = min(1.0, ratio * 0.8)

    y_spread = float(np.std(tops)) / h if tops else 0
    anomaly = min(1.0, max(anomaly, y_spread * 2.0))

    return {
        "layout_anomaly_score": round(anomaly, 4),
        "method": "heuristic",
        "confidence": 0.55,
        "header_word_count": len(header_words),
        "body_word_count": len(body_words),
    }


def analyze_layoutlmv3(
    image_path: str,
    ocr_detections: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Run LayoutLMv3 layout analysis on a document page."""
    ocr_detections = ocr_detections or []
    model, processor, device = _load_layoutlmv3()

    if model is None or processor is None:
        result = _heuristic_layout_score(image_path, ocr_detections)
        result["model"] = "layoutlmv3_heuristic"
        return result

    try:
        import torch
        from PIL import Image

        image = Image.open(image_path).convert("RGB")
        words = [str(d.get("text", "")) for d in ocr_detections[:128]]
        boxes = []
        w_img, h_img = image.size
        for d in ocr_detections[:128]:
            boxes.append([
                int(1000 * d.get("left", 0) / max(w_img, 1)),
                int(1000 * d.get("top", 0) / max(h_img, 1)),
                int(1000 * d.get("right", w_img) / max(w_img, 1)),
                int(1000 * d.get("bottom", h_img) / max(h_img, 1)),
            ])

        if not words:
            words = ["document"]
            boxes = [[0, 0, 1000, 1000]]

        encoding = processor(
            image, words, boxes=boxes, return_tensors="pt",
            padding="max_length", truncation=True, max_length=512,
        )
        encoding = {k: v.to(device) for k, v in encoding.items()}

        with torch.no_grad():
            outputs = model(**encoding)
            hidden = outputs.last_hidden_state[0].cpu().numpy()

        # Layout inconsistency = high variance across token embeddings
        token_var = float(np.mean(np.std(hidden, axis=0)))
        anomaly = min(1.0, max(0.0, (token_var - 0.5) / 2.0))

        return {
            "layout_anomaly_score": round(anomaly, 4),
            "method": "layoutlmv3-base",
            "model": "microsoft/layoutlmv3-base",
            "confidence": 0.78,
            "token_variance": round(token_var, 4),
            "words_analyzed": len(words),
        }
    except Exception as exc:
        logger.warning("LayoutLMv3 inference failed: %s", exc)
        result = _heuristic_layout_score(image_path, ocr_detections)
        result["model"] = "layoutlmv3_fallback"
        result["error"] = str(exc)
        return result
