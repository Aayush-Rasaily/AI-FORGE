"""Fuse explainability maps and extract suspicious region overlays."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np


def _load_gray_map(path: Optional[str], size: Tuple[int, int]) -> Optional[np.ndarray]:
    if not path:
        return None
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        colored = cv2.imread(str(path))
        if colored is None:
            return None
        img = cv2.cvtColor(colored, cv2.COLOR_BGR2GRAY)
    if img.shape[:2] != size[::-1]:
        img = cv2.resize(img, size)
    return img.astype(np.float32) / 255.0


def _extract_regions(mask: np.ndarray, min_area: int = 400) -> List[Dict[str, Any]]:
    binary = (mask > 0.55).astype(np.uint8) * 255
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    regions = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        regions.append({
            "bbox": [x, y, x + w, y + h],
            "area": int(area),
            "confidence": round(float(mask[y:y + h, x:x + w].mean()), 4),
        })
    regions.sort(key=lambda r: r["confidence"], reverse=True)
    return regions[:8]


def build_suspicious_overlay(
    image_path: str,
    output_dir: str,
    gradcam: Dict[str, Any],
    attention: Dict[str, Any],
    shap: Dict[str, Any],
    lime: Dict[str, Any],
) -> Dict[str, Any]:
    """Fuse GradCAM + Attention + SHAP + LIME into unified suspicious-region overlay."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fused_path = out / "fused_suspicious_heatmap.jpg"
    overlay_path = out / "fused_suspicious_overlay.jpg"
    boxed_path = out / "fused_suspicious_regions.jpg"

    original = cv2.imread(str(image_path))
    if original is None:
        return {"error": "Cannot read image", "regions": []}

    h, w = original.shape[:2]
    size = (w, h)
    weights = {"gradcam": 0.30, "attention": 0.30, "shap": 0.20, "lime": 0.20}

    fused = np.zeros((h, w), dtype=np.float32)
    sources_used = []

    for name, result, hm_key in [
        ("gradcam", gradcam, "heatmap"),
        ("attention", attention, "heatmap"),
        ("shap", shap, "heatmap"),
        ("lime", lime, "heatmap"),
    ]:
        gray = _load_gray_map(result.get(hm_key), size)
        if gray is not None:
            fused += weights[name] * gray
            sources_used.append(name)

    if fused.max() > 0:
        fused /= fused.max()

    colored = cv2.applyColorMap((fused * 255).astype(np.uint8), cv2.COLORMAP_JET)
    overlay = cv2.addWeighted(original, 0.5, colored, 0.5, 0)
    cv2.imwrite(str(fused_path), colored)
    cv2.imwrite(str(overlay_path), overlay)

    regions = _extract_regions(fused)
    boxed = original.copy()
    for i, region in enumerate(regions):
        x1, y1, x2, y2 = region["bbox"]
        color = (0, 0, 255) if region["confidence"] >= 0.7 else (0, 165, 255)
        cv2.rectangle(boxed, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            boxed, f"R{i + 1} {region['confidence']:.0%}",
            (x1, max(y1 - 6, 12)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1,
        )
    cv2.imwrite(str(boxed_path), boxed)

    why = (
        f"Fused overlay from {', '.join(sources_used)} identified {len(regions)} suspicious region(s) "
        f"above 55% confidence threshold."
        if regions else "No high-confidence suspicious regions after fusing explainability maps."
    )

    return {
        "fused_heatmap": str(fused_path),
        "fused_overlay": str(overlay_path),
        "boxed_regions": str(boxed_path),
        "suspicious_regions": regions,
        "sources_fused": sources_used,
        "why": why,
        "score": float(np.mean(fused[fused > 0.5])) if np.any(fused > 0.5) else float(np.mean(fused)),
    }
