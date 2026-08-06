"""Compare metadata claims against actual image content."""

from __future__ import annotations

from typing import Any, Dict, List

import cv2
import numpy as np


def compare_metadata_content(image_path: str, exif_data: Dict[str, Any]) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []
    img = cv2.imread(str(image_path))
    if img is None:
        return {"score": 0.0, "issues": [], "verdict": "Could not read image."}

    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    brightness = float(np.mean(gray)) / 255.0
    noise_est = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    iso = exif_data.get("iso")
    flash = exif_data.get("flash")
    orientation = exif_data.get("orientation")
    make = (exif_data.get("camera_make") or "").lower()

    # Flash vs brightness
    if flash is not None and int(flash) % 2 == 1 and brightness < 0.25:
        issues.append({
            "type": "fake_metadata",
            "severity": "medium",
            "description": "Flash fired in metadata but image is very dark.",
            "score": 0.6,
        })

    if flash is not None and int(flash) % 2 == 0 and brightness > 0.92:
        issues.append({
            "type": "fake_metadata",
            "severity": "low",
            "description": "Flash not fired but image is extremely bright (outdoor/overexposed).",
            "score": 0.35,
        })

    # ISO vs noise
    if iso is not None:
        iso_val = int(iso) if not isinstance(iso, (list, tuple)) else int(iso[0])
        if iso_val <= 100 and noise_est > 800:
            issues.append({
                "type": "fake_metadata",
                "severity": "high",
                "description": f"Low ISO ({iso_val}) but high image noise — metadata may not match content.",
                "score": 0.7,
            })
        if iso_val >= 3200 and noise_est < 50:
            issues.append({
                "type": "fake_metadata",
                "severity": "medium",
                "description": f"High ISO ({iso_val}) but unusually low noise in image.",
                "score": 0.55,
            })

    # Orientation vs dimensions
    if orientation in (6, 8) and w > h:
        issues.append({
            "type": "edited_metadata",
            "severity": "medium",
            "description": "EXIF orientation indicates portrait but stored dimensions are landscape.",
            "score": 0.5,
        })

    # Smartphone resolution check
    if "iphone" in make or "samsung" in make or "pixel" in make:
        mp = (w * h) / 1_000_000
        if mp > 60:
            issues.append({
                "type": "fake_metadata",
                "severity": "medium",
                "description": f"Mobile device metadata but very high resolution ({mp:.1f}MP).",
                "score": 0.55,
            })

    # GPS without outdoor indicators (very rough heuristic)
    gps = exif_data.get("gps") or {}
    if gps.get("latitude") is not None and brightness < 0.15:
        issues.append({
            "type": "fake_metadata",
            "severity": "low",
            "description": "GPS coordinates present but image appears very dark/indoor.",
            "score": 0.3,
        })

    content_metrics = {
        "brightness": round(brightness, 4),
        "noise_estimate": round(noise_est, 2),
        "width": w,
        "height": h,
    }

    score = max((i["score"] for i in issues), default=0.0)
    return {
        "content_metrics": content_metrics,
        "score": round(score, 4),
        "issues": issues,
        "verdict": "Metadata aligns with image content." if not issues else "Metadata/content mismatches found.",
    }
