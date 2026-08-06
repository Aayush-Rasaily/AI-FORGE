"""Timezone and timestamp consistency validation."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value[:19], fmt)
        except ValueError:
            continue
    return None


def validate_timezone(exif_data: Dict[str, Any]) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []

    dt_orig = _parse_dt(exif_data.get("datetime_original"))
    dt_dig = _parse_dt(exif_data.get("datetime_digitized"))
    dt_mod = _parse_dt(exif_data.get("datetime_modified"))
    offset = exif_data.get("offset_time") or exif_data.get("offset_time_original")

    timestamps = [t for t in (dt_orig, dt_dig, dt_mod) if t]
    if not timestamps:
        return {
            "consistent": None,
            "score": 0.15,
            "issues": [{
                "type": "removed_metadata",
                "severity": "medium",
                "description": "No capture timestamps found in EXIF.",
                "score": 0.15,
            }],
            "verdict": "Timestamps missing.",
        }

    if dt_orig and dt_dig:
        delta = abs((dt_orig - dt_dig).total_seconds())
        if delta > 86400:
            issues.append({
                "type": "edited_metadata",
                "severity": "high",
                "description": (
                    f"DateTimeOriginal ({exif_data.get('datetime_original')}) differs from "
                    f"DateTimeDigitized ({exif_data.get('datetime_digitized')}) by {int(delta / 3600)}h."
                ),
                "score": min(0.9, 0.4 + delta / 86400 * 0.1),
            })

    if dt_mod and dt_orig and dt_mod < dt_orig:
        issues.append({
            "type": "fake_metadata",
            "severity": "high",
            "description": "Modification timestamp predates original capture time.",
            "score": 0.8,
        })

    if dt_mod and dt_orig:
        edit_gap = (dt_mod - dt_orig).total_seconds()
        if edit_gap > 300:
            issues.append({
                "type": "edited_metadata",
                "severity": "medium",
                "description": f"File modified {int(edit_gap / 60)} minutes after capture — possible re-save.",
                "score": min(0.7, 0.3 + edit_gap / 3600 * 0.05),
            })

    if not offset and exif_data.get("gps", {}).get("latitude") is not None:
        issues.append({
            "type": "removed_metadata",
            "severity": "low",
            "description": "GPS present but timezone offset metadata missing.",
            "score": 0.2,
        })

    # Future timestamps
    now = datetime.now()
    for label, dt in (("original", dt_orig), ("digitized", dt_dig), ("modified", dt_mod)):
        if dt and dt > now:
            issues.append({
                "type": "fake_metadata",
                "severity": "critical",
                "description": f"{label} timestamp is in the future: {dt.isoformat()}",
                "score": 0.95,
            })

    score = max((i["score"] for i in issues), default=0.0)
    return {
        "consistent": len(issues) == 0,
        "offset_time": offset,
        "timestamps": {
            "original": exif_data.get("datetime_original"),
            "digitized": exif_data.get("datetime_digitized"),
            "modified": exif_data.get("datetime_modified"),
        },
        "score": round(score, 4),
        "issues": issues,
        "verdict": "Timestamps consistent." if not issues else "Timestamp inconsistencies detected.",
    }
