"""GPS coordinate validation."""

from __future__ import annotations

from typing import Any, Dict, List


def validate_gps(gps: Dict[str, Any]) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []
    lat = gps.get("latitude")
    lon = gps.get("longitude")
    has_gps = lat is not None and lon is not None

    if not has_gps:
        return {
            "valid": None,
            "has_gps": False,
            "score": 0.0,
            "issues": [],
            "verdict": "No GPS coordinates in metadata.",
        }

    valid = True
    if not (-90 <= lat <= 90):
        valid = False
        issues.append({
            "type": "fake_metadata",
            "severity": "critical",
            "description": f"Invalid latitude value: {lat}",
            "score": 0.95,
        })
    if not (-180 <= lon <= 180):
        valid = False
        issues.append({
            "type": "fake_metadata",
            "severity": "critical",
            "description": f"Invalid longitude value: {lon}",
            "score": 0.95,
        })

    if abs(lat) < 0.001 and abs(lon) < 0.001:
        valid = False
        issues.append({
            "type": "fake_metadata",
            "severity": "high",
            "description": "GPS coordinates at null island (0,0) — likely placeholder or fake.",
            "score": 0.85,
        })

    alt = gps.get("altitude")
    if alt is not None and (alt < -500 or alt > 9000):
        issues.append({
            "type": "fake_metadata",
            "severity": "medium",
            "description": f"Unusual GPS altitude: {alt}m",
            "score": 0.55,
        })

    score = max((i["score"] for i in issues), default=0.0)
    return {
        "valid": valid and score < 0.5,
        "has_gps": True,
        "latitude": lat,
        "longitude": lon,
        "altitude": alt,
        "score": round(score, 4),
        "issues": issues,
        "verdict": "GPS coordinates appear valid." if valid and not issues else "GPS anomalies detected.",
    }
