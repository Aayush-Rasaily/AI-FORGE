"""Full EXIF extraction and normalization."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import ExifTags, Image

GPS_TAGS = {ExifTags.GPSTAGS[k]: k for k in ExifTags.GPSTAGS}


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", errors="replace").strip("\x00")
        except Exception:
            return value.hex()
    return str(value).strip()


def _parse_rational(value: Any) -> Optional[float]:
    try:
        if hasattr(value, "numerator") and hasattr(value, "denominator"):
            return float(value.numerator) / max(float(value.denominator), 1e-9)
        if isinstance(value, tuple) and len(value) == 2:
            return float(value[0]) / max(float(value[1]), 1e-9)
        return float(value)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _dms_to_decimal(dms: Any, ref: str) -> Optional[float]:
    if not dms or len(dms) < 3:
        return None
    try:
        degrees = _parse_rational(dms[0]) or 0.0
        minutes = _parse_rational(dms[1]) or 0.0
        seconds = _parse_rational(dms[2]) or 0.0
        decimal = degrees + minutes / 60.0 + seconds / 3600.0
        if ref in ("S", "W"):
            decimal = -decimal
        return round(decimal, 6)
    except Exception:
        return None


def _parse_datetime(value: str) -> Optional[datetime]:
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y:%m:%d"):
        try:
            return datetime.strptime(value[:19], fmt)
        except ValueError:
            continue
    return None


def extract_exif(image_path: str) -> Dict[str, Any]:
    path = Path(image_path)
    result: Dict[str, Any] = {
        "metadata_found": False,
        "metadata_count": 0,
        "tags": {},
        "raw_tags": {},
        "camera_make": None,
        "camera_model": None,
        "software": None,
        "artist": None,
        "datetime_original": None,
        "datetime_digitized": None,
        "datetime_modified": None,
        "orientation": None,
        "image_unique_id": None,
        "gps": {},
        "dimensions": {},
        "format": None,
    }

    if not path.exists():
        result["error"] = f"Image not found: {path}"
        return result

    try:
        with Image.open(path) as image:
            result["format"] = image.format
            result["dimensions"] = {
                "width": image.width,
                "height": image.height,
                "mode": image.mode,
            }

            exif = image.getexif()
            if not exif:
                return result

            result["metadata_found"] = True
            tag_map = {ExifTags.TAGS.get(k, str(k)): v for k, v in exif.items()}
            result["raw_tags"] = {str(k): _safe_str(v) for k, v in exif.items()}
            result["tags"] = {k: _safe_str(v) for k, v in tag_map.items()}
            result["metadata_count"] = len(exif)

            result["camera_make"] = _safe_str(exif.get(271)) or None
            result["camera_model"] = _safe_str(exif.get(272)) or None
            result["software"] = _safe_str(exif.get(305)) or None
            result["artist"] = _safe_str(exif.get(315)) or None
            result["datetime_modified"] = _safe_str(exif.get(306)) or None
            result["orientation"] = exif.get(274)
            result["image_unique_id"] = _safe_str(exif.get(42016)) or None

            exif_ifd = exif.get_ifd(0x8769) if hasattr(exif, "get_ifd") else {}
            if exif_ifd:
                result["datetime_original"] = _safe_str(exif_ifd.get(36867)) or None
                result["datetime_digitized"] = _safe_str(exif_ifd.get(36868)) or None
                result["lens_model"] = _safe_str(exif_ifd.get(42036)) or None
                result["focal_length"] = _parse_rational(exif_ifd.get(37386))
                result["f_number"] = _parse_rational(exif_ifd.get(33437))
                result["iso"] = exif_ifd.get(34855) or exif_ifd.get(34864)
                result["exposure_time"] = _parse_rational(exif_ifd.get(33434))
                result["flash"] = exif_ifd.get(37385)
                result["white_balance"] = exif_ifd.get(41987)
                result["offset_time"] = _safe_str(exif_ifd.get(36880)) or None
                result["offset_time_original"] = _safe_str(exif_ifd.get(36881)) or None

            gps_ifd = exif.get_ifd(0x8825) if hasattr(exif, "get_ifd") else {}
            if gps_ifd:
                lat = _dms_to_decimal(gps_ifd.get(2), _safe_str(gps_ifd.get(1)))
                lon = _dms_to_decimal(gps_ifd.get(4), _safe_str(gps_ifd.get(3)))
                alt = _parse_rational(gps_ifd.get(6))
                result["gps"] = {
                    "latitude": lat,
                    "longitude": lon,
                    "altitude": alt,
                    "latitude_ref": _safe_str(gps_ifd.get(1)),
                    "longitude_ref": _safe_str(gps_ifd.get(3)),
                    "timestamp": _safe_str(gps_ifd.get(7)),
                }

            parsed_times = {}
            for key in ("datetime_original", "datetime_digitized", "datetime_modified"):
                val = result.get(key)
                if val:
                    parsed_times[key] = _parse_datetime(val)
            result["parsed_times"] = {
                k: v.isoformat() if v else None for k, v in parsed_times.items()
            }

    except Exception as exc:
        result["error"] = str(exc)

    return result
