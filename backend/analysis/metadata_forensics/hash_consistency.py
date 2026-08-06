"""File hash consistency and metadata integrity checks."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, List


def compute_hashes(image_path: str) -> Dict[str, Any]:
    path = Path(image_path)
    data = path.read_bytes()
    return {
        "md5": hashlib.md5(data).hexdigest(),
        "sha256": hashlib.sha256(data).hexdigest(),
        "file_size_bytes": len(data),
    }


def validate_hash_consistency(image_path: str, exif_data: Dict[str, Any]) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []
    hashes = compute_hashes(image_path)
    dims = exif_data.get("dimensions") or {}
    width = dims.get("width", 0)
    height = dims.get("height", 0)
    pixels = width * height
    file_size = hashes["file_size_bytes"]

    unique_id = exif_data.get("image_unique_id")
    if unique_id and len(unique_id) < 8:
        issues.append({
            "type": "fake_metadata",
            "severity": "medium",
            "description": f"Suspiciously short ImageUniqueID: {unique_id}",
            "score": 0.5,
        })

    if pixels > 0 and file_size > 0:
        bytes_per_pixel = file_size / pixels
        if bytes_per_pixel < 0.05:
            issues.append({
                "type": "edited_metadata",
                "severity": "medium",
                "description": (
                    f"Unusually low bytes/pixel ({bytes_per_pixel:.3f}) — "
                    "heavy compression or metadata stripping."
                ),
                "score": 0.45,
            })
        if bytes_per_pixel > 8.0:
            issues.append({
                "type": "fake_metadata",
                "severity": "low",
                "description": f"Unusually high bytes/pixel ({bytes_per_pixel:.2f}).",
                "score": 0.3,
            })

    score = max((i["score"] for i in issues), default=0.0)
    return {
        "hashes": hashes,
        "bytes_per_pixel": round(file_size / pixels, 4) if pixels else None,
        "image_unique_id": unique_id,
        "score": round(score, 4),
        "issues": issues,
        "verdict": "Hash metrics consistent." if not issues else "Hash/size anomalies detected.",
    }
