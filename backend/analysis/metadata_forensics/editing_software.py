"""Editing software detection from EXIF and XMP."""

from __future__ import annotations

from typing import Any, Dict, List

EDITING_SOFTWARE = [
    "photoshop", "adobe", "lightroom", "camera raw", "gimp", "paint.net",
    "pixlr", "canva", "affinity", "snapseed", "capture one", "darktable",
    "luminar", "topaz", "skylum", "paintshop", "corel", "figma",
    "remove.bg", "photopea", "inkscape", "illustrator", "after effects",
    "premiere", "davinci", "resolve", "facetune", "beautyplus",
]

SUSPICIOUS_HOSTS = [
    "windows photo", "microsoft photos", "preview", "photos app",
]


def detect_editing_software(exif_data: Dict[str, Any], hidden: Dict[str, Any]) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []
    detected: List[str] = []

    sources = {
        "software": exif_data.get("software"),
        "artist": exif_data.get("artist"),
        "xmp_creator_tool": hidden.get("xmp", {}).get("creator_tool"),
        "xmp_software": hidden.get("xmp", {}).get("software"),
        "xmp_history": hidden.get("xmp", {}).get("history"),
    }

    combined = " ".join(str(v) for v in sources.values() if v).lower()

    for name in EDITING_SOFTWARE:
        if name in combined:
            detected.append(name)
            issues.append({
                "type": "edited_metadata",
                "severity": "high" if name in ("photoshop", "gimp", "lightroom") else "medium",
                "description": f"Editing software detected: {name}",
                "score": 0.85 if name in ("photoshop", "gimp") else 0.65,
                "software": name,
            })

    for host in SUSPICIOUS_HOSTS:
        if host in combined:
            issues.append({
                "type": "edited_metadata",
                "severity": "low",
                "description": f"Image processed by OS viewer/editor: {host}",
                "score": 0.35,
            })

    primary = exif_data.get("software")
    score = max((i["score"] for i in issues), default=0.0)

    return {
        "software_detected": bool(detected or primary),
        "software": primary or (detected[0] if detected else None),
        "detected_tools": list(dict.fromkeys(detected)),
        "sources": {k: v for k, v in sources.items() if v},
        "score": round(score, 4),
        "issues": issues,
        "verdict": (
            f"Editing software: {', '.join(detected)}"
            if detected else "No editing software detected."
        ),
    }
