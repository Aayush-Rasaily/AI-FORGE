"""Smart region detection — labeling, IDs, confidence, verdicts."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


LABEL_PATTERNS = (
    (r"sign", "forged signature", "signature"),
    (r"logo|brand", "manipulated logo", "logo"),
    (r"date|time", "edited date", "date"),
    (r"invoice|amount|total|\$|₹|€", "altered invoice value", "number"),
    (r"id|account|ref", "modified identifier", "number"),
    (r"stamp|seal", "forged stamp", "stamp"),
    (r"text|word|ocr", "edited text", "text"),
    (r"copy|duplicate|clone", "copied object", "copy_move"),
)


def _infer_label(region: Dict[str, Any], analysis: Dict[str, Any]) -> Tuple[str, str]:
    text = " ".join(
        str(region.get(k, "")) for k in ("label", "type", "reason", "manipulation")
    ).lower()
    for pattern, label, rtype in LABEL_PATTERNS:
        if re.search(pattern, text):
            return label, rtype
    if region.get("type"):
        return str(region["type"]).replace("_", " "), str(region["type"])
    score = float(region.get("score") or 0)
    if score >= 0.65:
        return "manipulated region", "manipulation"
    return "suspicious region", "anomaly"


def _verdict(confidence: float) -> str:
    if confidence >= 85:
        return "HIGH CONFIDENCE MANIPULATION"
    if confidence >= 65:
        return "PROBABLE MANIPULATION"
    if confidence >= 45:
        return "SUSPICIOUS — REQUIRES REVIEW"
    return "LOW CONFIDENCE ANOMALY"


def build_smart_regions(
    raw_regions: List[Dict[str, Any]],
    analysis: Dict[str, Any],
    layers: Optional[Dict[str, np.ndarray]] = None,
) -> List[Dict[str, Any]]:
    """Enrich contour regions with smart labels, unique IDs, and verdicts."""
    layers = layers or {}
    smart: List[Dict[str, Any]] = []
    for i, reg in enumerate(raw_regions):
        label, rtype = _infer_label(reg, analysis)
        score = float(reg.get("score") or 0)
        conf = float(reg.get("confidence") or (score * 100 if score <= 1 else score))
        if conf <= 1:
            conf *= 100.0
        conf = min(99.0, max(0.0, conf))

        region_id = reg.get("id") or f"REG-{i + 1:03d}"
        bbox = reg.get("bbox") or reg.get("bounding_box") or {}

        contributions: Dict[str, float] = {}
        if layers:
            for layer_name, layer_map in layers.items():
                x = int(bbox.get("x", 0))
                y = int(bbox.get("y", 0))
                bw = int(bbox.get("w", bbox.get("width", 0)))
                bh = int(bbox.get("h", bbox.get("height", 0)))
                h, w = layer_map.shape[:2]
                x2, y2 = min(w, x + bw), min(h, y + bh)
                x, y = max(0, x), max(0, y)
                if x2 > x and y2 > y:
                    contributions[layer_name] = round(float(layer_map[y:y2, x:x2].mean()), 4)

        smart.append({
            **reg,
            "id": region_id,
            "index": i + 1,
            "label": label.title(),
            "type": rtype,
            "manipulation": label,
            "confidence": round(conf, 2),
            "verdict": _verdict(conf),
            "detector_contributions": contributions or reg.get("detector_votes", {}),
            "detector_votes": reg.get("detector_votes") or {
                k: v >= 0.45 for k, v in (contributions or {}).items()
            },
        })
    smart.sort(key=lambda r: float(r.get("confidence") or 0), reverse=True)
    return smart
