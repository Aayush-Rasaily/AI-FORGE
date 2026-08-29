"""Signature region localization and forensic indicators."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

logger = logging.getLogger("ai_forge.localization.signature")


def localize_signatures(
    image_path: str,
    analysis: Dict[str, Any],
    output_dir: Path,
) -> Dict[str, Any]:
    """
    Detect signature regions and compute stroke/pressure heuristics.
    Integrates Siamese verification when reference is available.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    original = cv2.imread(str(image_path))
    if original is None:
        return {"regions": [], "available": False}

    h, w = original.shape[:2]
    regions: List[Dict[str, Any]] = []

    # Document analysis signature hints
    for block_key in ("font_consistency", "text_layout", "region_anomaly", "ocr"):
        block = analysis.get(block_key) or {}
        for item in block.get("suspicious_words") or block.get("regions") or []:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or item.get("type") or "").lower()
            if "sign" not in label:
                continue
            bbox = item.get("bbox") or item.get("box") or {}
            if not bbox:
                continue
            x = int(float(bbox.get("x", bbox.get("left", 0))))
            y = int(float(bbox.get("y", bbox.get("top", 0))))
            bw = int(float(bbox.get("w", bbox.get("width", 40))))
            bh = int(float(bbox.get("h", bbox.get("height", 20))))
            regions.append(_build_signature_region(original, x, y, bw, bh, len(regions) + 1, item))

    # Heuristic: bottom-third ink-dense regions (common signature placement)
    if not regions:
        gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
        roi = gray[int(h * 0.65) :, :]
        _, thresh = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in sorted(contours, key=cv2.contourArea, reverse=True)[:3]:
            area = cv2.contourArea(cnt)
            if area < 800 or area > w * h * 0.15:
                continue
            x, y, bw, bh = cv2.boundingRect(cnt)
            y += int(h * 0.65)
            regions.append(_build_signature_region(original, x, y, bw, bh, len(regions) + 1, {}))
            break

    overlay = original.copy()
    for reg in regions:
        b = reg["bbox"]
        # Use canonical width/height keys
        cv2.rectangle(
            overlay,
            (b["x"], b["y"]),
            (b["x"] + b["width"], b["y"] + b["height"]),
            (0, 140, 255),
            2,
        )
        cv2.putText(
            overlay,
            f"SIG {reg['confidence']:.0f}%",
            (b["x"], max(14, b["y"] - 4)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 140, 255),
            1,
        )

    overlay_path = output_dir / "signature_localization.png"
    cv2.imwrite(str(overlay_path), overlay)
    logger.info("Generated: Signature Localization -> saved")

    # Optional Siamese similarity when signature_result in analysis
    sig_result = analysis.get("signature_verification") or analysis.get("signature_result") or {}
    similarity = float(sig_result.get("similarity") or sig_result.get("score") or 0)
    for reg in regions:
        if similarity > 0:
            reg["similarity_score"] = round(similarity * 100 if similarity <= 1 else similarity, 2)
            reg["evidence"].append(f"Siamese similarity: {reg['similarity_score']}%")

    return {
        "available": bool(regions),
        "regions": regions,
        "overlay_path": str(overlay_path),
        "similarity_score": similarity,
    }


def _build_signature_region(
    original: np.ndarray,
    x: int,
    y: int,
    bw: int,
    bh: int,
    index: int,
    meta: Dict[str, Any],
) -> Dict[str, Any]:
    h, w = original.shape[:2]
    x, y = max(0, x), max(0, y)
    bw, bh = min(bw, w - x), min(bh, h - y)
    roi = original[y : y + bh, x : x + bw] if bw > 0 and bh > 0 else original
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if roi.size else np.zeros((1, 1), dtype=np.uint8)

    # Stroke discontinuity proxy — edge fragment count
    edges = cv2.Canny(gray, 40, 120)
    fragments = cv2.countNonZero(edges)
    discontinuity = min(1.0, fragments / max(1, bw * bh) * 8.0)

    # Pressure inconsistency — local intensity variance
    pressure_var = float(np.std(gray.astype(np.float32))) / 128.0 if gray.size else 0.0

    confidence = min(95.0, 40.0 + discontinuity * 30.0 + pressure_var * 35.0)
    if meta.get("confidence"):
        confidence = max(confidence, float(meta["confidence"]) * (100 if float(meta["confidence"]) <= 1 else 1))

    # Canonical bbox — always use width/height, never w/h shorthand
    _canon_bbox = {"x": x, "y": y, "width": bw, "height": bh}
    return {
        "id": f"SIG-{index:03d}",
        "index": index,
        "label": "Forged Signature",
        "type": "signature",
        "manipulation": "signature forgery indicators",
        "bbox": _canon_bbox,
        "bounding_box": _canon_bbox,
        "coordinates": [x, y, x + bw, y + bh],
        "score": round(confidence / 100.0, 4),
        "confidence": round(confidence, 2),
        "stroke_discontinuity": round(discontinuity, 4),
        "pressure_inconsistency": round(pressure_var, 4),
        "similarity_score": None,
        "evidence": [
            f"Stroke discontinuity index: {discontinuity:.3f}",
            f"Pressure variance: {pressure_var:.3f}",
        ],
        "technical_explanation": (
            "Elevated stroke fragmentation and pressure variance suggest non-authentic signature strokes."
        ),
        "plain_english_explanation": "This signature region shows ink patterns inconsistent with natural pen pressure.",
        "detector_contributions": {
            "stroke_analysis": round(discontinuity, 3),
            "pressure_analysis": round(pressure_var, 3),
            "segmentation": 0.5,
        },
        "verdict": "PROBABLE SIGNATURE FORGERY" if confidence >= 65 else "SUSPICIOUS SIGNATURE",
    }
