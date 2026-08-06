"""
OCR visualization — mismatch heatmap and layout overlay.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np


def generate_mismatch_heatmap(
    image_path: str,
    mismatch_regions: List[Dict[str, Any]],
    output_path: str,
) -> str:
    """Highlight regions where OCR engines disagreed."""
    img = cv2.imread(str(image_path))
    if img is None:
        return ""

    h, w = img.shape[:2]
    heatmap = np.zeros((h, w), dtype=np.float32)

    for region in mismatch_regions:
        bbox = region.get("bbox") or []
        if not bbox:
            continue
        pts = np.array(bbox, dtype=np.int32)
        score = float(region.get("disagreement", 0.5))
        cv2.fillPoly(heatmap, [pts], score)

    heatmap = cv2.GaussianBlur(heatmap, (31, 31), 0)
    if heatmap.max() > heatmap.min():
        heatmap = (heatmap - heatmap.min()) / (heatmap.max() - heatmap.min())

    colored = np.zeros((h, w, 3), dtype=np.uint8)
    colored[heatmap < 0.33] = [34, 197, 94]
    colored[(heatmap >= 0.33) & (heatmap < 0.66)] = [249, 115, 22]
    colored[heatmap >= 0.66] = [239, 68, 68]

    overlay = cv2.addWeighted(img, 0.55, colored, 0.45, 0)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), overlay)
    return str(out)


def generate_layout_overlay(
    image_path: str,
    detections: List[Dict[str, Any]],
    output_path: str,
) -> str:
    """Draw consensus OCR bounding boxes on page image."""
    img = cv2.imread(str(image_path))
    if img is None:
        return ""

    overlay = img.copy()
    for det in detections:
        bbox = det.get("bbox") or []
        if not bbox:
            continue
        pts = np.array(bbox, dtype=np.int32)
        conf = float(det.get("confidence", 0.5))
        color = (34, 197, 94) if conf >= 0.7 else (249, 115, 22) if conf >= 0.4 else (239, 68, 68)
        cv2.polylines(overlay, [pts], True, color, 2)
        x, y = int(det.get("left", pts[0][0])), int(det.get("top", pts[0][1]) - 4)
        label = f"{det.get('text', '')[:20]} ({conf:.0%})"
        cv2.putText(overlay, label, (max(0, x), max(12, y)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), overlay)
    return str(out)


def build_ocr_visualizations(
    image_path: str,
    ocr_result: Dict[str, Any],
    analysis_dir: Optional[str] = None,
) -> Dict[str, Optional[str]]:
    if not analysis_dir:
        return {"mismatch_heatmap": None, "layout_overlay": None}

    base = Path(analysis_dir)
    stem = Path(image_path).stem
    mismatch_path = base / f"{stem}_ocr_mismatch.jpg"
    layout_path = base / f"{stem}_ocr_layout.jpg"

    mismatch = generate_mismatch_heatmap(
        image_path,
        ocr_result.get("mismatch_regions", []),
        str(mismatch_path),
    )
    layout = generate_layout_overlay(
        image_path,
        ocr_result.get("detections", []),
        str(layout_path),
    )
    return {
        "mismatch_heatmap": mismatch or None,
        "layout_overlay": layout or None,
    }
