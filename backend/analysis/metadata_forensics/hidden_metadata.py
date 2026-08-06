"""Hidden metadata — XMP, IPTC, ICC, APP segments."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List


def _parse_xmp(xmp_text: str) -> Dict[str, str]:
    fields: Dict[str, str] = {}
    patterns = {
        "creator_tool": r"xmp:CreatorTool[^>]*>([^<]+)",
        "software": r"photoshop:[^>]*>([^<]+)",
        "history": r"stEvt:action[^>]*>([^<]+)",
        "create_date": r"xmp:CreateDate[^>]*>([^<]+)",
        "modify_date": r"xmp:ModifyDate[^>]*>([^<]+)",
        "document_id": r"xmpMM:DocumentID[^>]*>([^<]+)",
    }
    for key, pat in patterns.items():
        match = re.search(pat, xmp_text, re.IGNORECASE)
        if match:
            fields[key] = match.group(1).strip()
    return fields


def scan_hidden_metadata(image_path: str) -> Dict[str, Any]:
    path = Path(image_path)
    raw = path.read_bytes()
    issues: List[Dict[str, Any]] = []

    xmp_blocks = re.findall(rb"<\?xpacket begin.*?\?>", raw, re.DOTALL)
    xmp_text = ""
    if xmp_blocks:
        xmp_text = xmp_blocks[0].decode("utf-8", errors="replace")
    elif b"http://ns.adobe.com/xap/1.0/" in raw:
        start = raw.find(b"<?xpacket")
        if start == -1:
            start = raw.find(b"<x:xmpmeta")
        if start >= 0:
            end = raw.find(b"<?xpacket end", start)
            if end < 0:
                end = raw.find(b"</x:xmpmeta>", start)
            if end > start:
                xmp_text = raw[start:end + 20].decode("utf-8", errors="replace")

    xmp = _parse_xmp(xmp_text) if xmp_text else {}

    has_icc = b"ICC_PROFILE" in raw or raw[:4] == b"\x89PNG"
    has_iptc = b"Photoshop 3.0" in raw or b"\x1c\x02" in raw[:2000]
    has_exif_marker = b"Exif" in raw[:65536]
    has_xmp = bool(xmp_text)

    hidden_count = sum([has_xmp, has_icc, has_iptc, has_exif_marker])

    if has_xmp and xmp.get("history"):
        issues.append({
            "type": "edited_metadata",
            "severity": "high",
            "description": f"XMP edit history found: {xmp.get('history')}",
            "score": 0.8,
        })

    if has_xmp and xmp.get("creator_tool"):
        tool = xmp["creator_tool"].lower()
        if any(s in tool for s in ("photoshop", "gimp", "lightroom", "affinity")):
            issues.append({
                "type": "edited_metadata",
                "severity": "high",
                "description": f"XMP CreatorTool: {xmp['creator_tool']}",
                "score": 0.85,
            })

    segments = {
        "xmp": has_xmp,
        "icc_profile": has_icc,
        "iptc": has_iptc,
        "exif_marker": has_exif_marker,
    }

    score = max((i["score"] for i in issues), default=0.0)
    return {
        "segments": segments,
        "hidden_metadata_count": hidden_count,
        "xmp": xmp,
        "has_hidden_metadata": hidden_count > 0,
        "score": round(score, 4),
        "issues": issues,
        "verdict": f"{hidden_count} hidden metadata segment(s) found.",
    }
