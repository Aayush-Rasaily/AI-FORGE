"""Camera device fingerprinting and profile validation."""

from __future__ import annotations

from typing import Any, Dict, List

# Known camera resolution / ISO ranges (heuristic profiles)
CAMERA_PROFILES = {
    "apple": {"max_megapixels": 48, "iso_range": (25, 3200)},
    "canon": {"max_megapixels": 45, "iso_range": (50, 102400)},
    "nikon": {"max_megapixels": 46, "iso_range": (64, 102400)},
    "sony": {"max_megapixels": 61, "iso_range": (50, 102400)},
    "samsung": {"max_megapixels": 200, "iso_range": (50, 3200)},
    "google": {"max_megapixels": 50, "iso_range": (21, 6400)},
}


def build_camera_fingerprint(exif_data: Dict[str, Any]) -> Dict[str, Any]:
    make = (exif_data.get("camera_make") or "").lower()
    model = (exif_data.get("camera_model") or "").lower()
    dims = exif_data.get("dimensions") or {}
    width = dims.get("width", 0)
    height = dims.get("height", 0)
    megapixels = round((width * height) / 1_000_000, 2) if width and height else 0
    iso = exif_data.get("iso")
    focal = exif_data.get("focal_length")
    fnum = exif_data.get("f_number")

    fingerprint = {
        "make": exif_data.get("camera_make"),
        "model": exif_data.get("camera_model"),
        "lens_model": exif_data.get("lens_model"),
        "megapixels": megapixels,
        "iso": iso,
        "focal_length": focal,
        "f_number": fnum,
        "exposure_time": exif_data.get("exposure_time"),
        "flash": exif_data.get("flash"),
        "hash_key": f"{make}|{model}|{megapixels}|{iso}|{focal}",
    }
    return fingerprint


def validate_camera_fingerprint(exif_data: Dict[str, Any]) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []
    fp = build_camera_fingerprint(exif_data)
    make = (fp.get("make") or "").lower()
    model = (fp.get("model") or "").lower()
    dims = exif_data.get("dimensions") or {}

    if not make and not model:
        return {
            "fingerprint": fp,
            "matched_profile": None,
            "score": 0.2,
            "issues": [{
                "type": "removed_metadata",
                "severity": "medium",
                "description": "Camera make/model missing — device fingerprint unavailable.",
                "score": 0.2,
            }],
            "verdict": "No camera fingerprint.",
        }

    matched = None
    for brand, profile in CAMERA_PROFILES.items():
        if brand in make or brand in model:
            matched = brand
            mp = fp.get("megapixels", 0)
            if mp > profile["max_megapixels"] * 1.5:
                issues.append({
                    "type": "fake_metadata",
                    "severity": "high",
                    "description": (
                        f"Resolution ({mp}MP) exceeds expected range for {brand} devices "
                        f"(max ~{profile['max_megapixels']}MP)."
                    ),
                    "score": 0.75,
                })
            iso = fp.get("iso")
            if iso is not None:
                lo, hi = profile["iso_range"]
                if iso < lo * 0.5 or iso > hi * 2:
                    issues.append({
                        "type": "fake_metadata",
                        "severity": "medium",
                        "description": f"ISO {iso} outside typical {brand} range ({lo}–{hi}).",
                        "score": 0.55,
                    })
            break

    if make and "iphone" in model and dims.get("width", 0) > 10000:
        issues.append({
            "type": "fake_metadata",
            "severity": "high",
            "description": "iPhone metadata with unusually large image dimensions.",
            "score": 0.7,
        })

    if make and not model:
        issues.append({
            "type": "edited_metadata",
            "severity": "low",
            "description": "Camera make present but model tag missing.",
            "score": 0.25,
        })

    score = max((i["score"] for i in issues), default=0.0)
    return {
        "fingerprint": fp,
        "matched_profile": matched,
        "score": round(score, 4),
        "issues": issues,
        "verdict": "Camera fingerprint consistent." if not issues else "Camera fingerprint anomalies.",
    }
