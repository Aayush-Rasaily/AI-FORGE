"""Embedded thumbnail vs main image verification."""

from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
from PIL import Image


def _image_hash(img_array: np.ndarray, size: int = 16) -> str:
    gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY) if len(img_array.shape) == 3 else img_array
    resized = cv2.resize(gray, (size, size))
    return hashlib.md5(resized.tobytes()).hexdigest()


def _extract_thumbnail_bytes(image_path: str) -> Optional[bytes]:
    try:
        import piexif
        exif_dict = piexif.load(str(image_path))
        return exif_dict.get("thumbnail")
    except ImportError:
        pass
    except Exception:
        pass

    try:
        with Image.open(image_path) as img:
            exif = img.getexif()
            if hasattr(exif, "get_ifd"):
                thumb = exif.get_ifd(0x8769).get(513)
                if thumb:
                    return thumb
    except Exception:
        pass
    return None


def verify_thumbnail(image_path: str) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []
    path = Path(image_path)

    main = cv2.imread(str(path))
    if main is None:
        return {"verified": None, "score": 0.0, "issues": [], "verdict": "Could not read image."}

    thumb_bytes = _extract_thumbnail_bytes(image_path)
    if not thumb_bytes:
        return {
            "verified": None,
            "thumbnail_present": False,
            "score": 0.1,
            "issues": [],
            "verdict": "No embedded thumbnail in EXIF.",
        }

    try:
        thumb_arr = np.array(Image.open(BytesIO(thumb_bytes)).convert("RGB"))
        thumb_arr = cv2.cvtColor(thumb_arr, cv2.COLOR_RGB2BGR)
    except Exception as exc:
        return {
            "verified": False,
            "thumbnail_present": True,
            "score": 0.5,
            "issues": [{
                "type": "edited_metadata",
                "severity": "medium",
                "description": f"Thumbnail present but unreadable: {exc}",
                "score": 0.5,
            }],
            "verdict": "Thumbnail extraction failed.",
        }

    main_small = cv2.resize(main, (thumb_arr.shape[1], thumb_arr.shape[0]))
    main_hash = _image_hash(main_small)
    thumb_hash = _image_hash(thumb_arr)
    hash_match = main_hash == thumb_hash

    diff = cv2.absdiff(main_small, thumb_arr)
    mse = float(np.mean(diff ** 2))
    similarity = max(0.0, 1.0 - mse / 65025.0)

    if not hash_match and similarity < 0.85:
        issues.append({
            "type": "edited_metadata",
            "severity": "high",
            "description": (
                f"Embedded thumbnail does not match main image "
                f"(similarity {similarity:.0%}) — image likely re-encoded after edit."
            ),
            "score": min(0.9, 1.0 - similarity),
        })

    score = max((i["score"] for i in issues), default=0.0)
    return {
        "verified": hash_match or similarity >= 0.85,
        "thumbnail_present": True,
        "similarity": round(similarity, 4),
        "hash_match": hash_match,
        "score": round(score, 4),
        "issues": issues,
        "verdict": "Thumbnail matches main image." if not issues else "Thumbnail mismatch detected.",
    }
