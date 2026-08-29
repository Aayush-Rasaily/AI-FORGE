"""Evidence-backed document tampering projection.

The document engines already perform OCR, layout, font, spacing, image, and
metadata analysis.  This module only normalizes their localized observations
into a stable finding contract; it does not invent detections.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from backend.services.signature_service import update_forensic_dossier


def _confidence(row: Dict[str, Any]) -> Optional[float]:
    value = row.get("confidence")
    if value is None:
        value = row.get("score")
    if value is None:
        value = row.get("risk_score")
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if value > 1.0:
        value /= 100.0
    return round(max(0.0, min(1.0, value)), 4)


def _xywh(raw: Any) -> Optional[List[float]]:
    if isinstance(raw, dict):
        x = raw.get("x", raw.get("left"))
        y = raw.get("y", raw.get("top"))
        width = raw.get("width", raw.get("w"))
        height = raw.get("height", raw.get("h"))
        if None in (x, y, width, height):
            return None
        values = [x, y, width, height]
    elif isinstance(raw, (list, tuple)) and len(raw) >= 4:
        if isinstance(raw[0], (list, tuple)):
            points = raw
            xs = [float(point[0]) for point in points if len(point) >= 2]
            ys = [float(point[1]) for point in points if len(point) >= 2]
            if not xs or not ys:
                return None
            x, y = min(xs), min(ys)
            values = [x, y, max(xs) - x, max(ys) - y]
        else:
            values = list(raw[:4])
    else:
        return None
    try:
        x, y, width, height = (float(value) for value in values)
    except (TypeError, ValueError):
        return None
    if width <= 0 or height <= 0:
        return None
    return [round(x, 2), round(y, 2), round(width, 2), round(height, 2)]


def _polygon(row: Dict[str, Any], bbox: List[float]) -> List[List[float]]:
    polygon = row.get("polygon") or row.get("points")
    if isinstance(polygon, list) and len(polygon) >= 3:
        points = []
        for point in polygon:
            if isinstance(point, (list, tuple)) and len(point) >= 2:
                points.append([float(point[0]), float(point[1])])
        if len(points) >= 3:
            return points
    x, y, width, height = bbox
    return [
        [x, y],
        [x + width, y],
        [x + width, y + height],
        [x, y + height],
    ]


def _category(row: Dict[str, Any]) -> str:
    value = str(
        row.get("category")
        or row.get("field_category")
        or row.get("type")
        or row.get("anomaly_type")
        or row.get("module")
        or "document anomaly"
    ).lower()
    if any(token in value for token in ("amount", "number", "numeric", "price", "invoice", "policy")):
        return "Text Manipulation"
    if any(token in value for token in ("font", "spacing", "baseline", "alignment", "layout", "line_break")):
        return "Text Layout"
    if "signature" in value:
        return "Signature"
    if "logo" in value:
        return "Logo"
    if "seal" in value or "stamp" in value:
        return "Seal"
    if any(token in value for token in ("copy", "clone")):
        return "Copy-Move"
    if any(token in value for token in ("ela", "jpeg", "compression", "resampling", "frequency")):
        return "Image Compression"
    if "noise" in value:
        return "Noise"
    if "metadata" in value:
        return "Metadata"
    if any(token in value for token in ("object", "region", "pixel", "splic")):
        return "Image Content"
    return "Document Analysis"


def _human_summary(category: str, row: Dict[str, Any], description: str) -> str:
    value = str(row.get("type") or row.get("anomaly_type") or "").lower()
    if category == "Text Manipulation":
        if "date" in value:
            return "The date field appears inconsistent with surrounding document text."
        if "policy" in value:
            return "The policy number appears inconsistent with surrounding document text."
        if "invoice" in value:
            return "The invoice number appears inconsistent with surrounding document text."
        return "The highlighted numeric or text value appears to have been digitally modified."
    if category == "Text Layout":
        return "The highlighted text has spacing, alignment, baseline, or rendering characteristics that differ from nearby text."
    if category == "Signature":
        return "The highlighted signature region requires comparison with an authenticated specimen."
    if category == "Logo":
        return "The highlighted logo region has image characteristics that differ from surrounding document content."
    if category == "Seal":
        return "The highlighted seal or stamp region requires source verification."
    if category == "Copy-Move":
        return "Matching or duplicated image features were recorded in the highlighted region."
    if category == "Image Compression":
        return "The highlighted region shows localized compression or resampling characteristics that differ from nearby content."
    if category == "Noise":
        return "Noise characteristics in the highlighted region differ from the surrounding document."
    if category == "Metadata":
        return "File-history metadata contains an inconsistency requiring contextual review."
    return description


def _recommendation(category: str) -> str:
    actions = {
        "Text Manipulation": "Verify the value against the original source record.",
        "Text Layout": "Compare the highlighted text with the original document rendering.",
        "Signature": "Compare the region with an authenticated signature specimen.",
        "Logo": "Verify the logo against an authenticated issuer copy.",
        "Seal": "Verify the seal or stamp against an authenticated source.",
        "Copy-Move": "Review both matched regions and obtain the original image.",
        "Image Compression": "Review the source file and recompression history.",
        "Noise": "Compare the region with the original scan or capture.",
        "Metadata": "Compare metadata with custody and source-system records.",
    }
    return actions.get(category, "Review the localized evidence against an authenticated source.")


def _severity(row: Dict[str, Any], category: str) -> str:
    supplied = str(row.get("severity") or row.get("risk_level") or "").upper()
    if supplied in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        return supplied
    if category in {"Text Manipulation", "Signature", "Seal"}:
        return "HIGH"
    if category in {"Copy-Move", "Logo"}:
        return "MEDIUM"
    return "LOW"


def _iter_page_rows(result: Dict[str, Any]) -> Iterable[Tuple[Dict[str, Any], Optional[int], str]]:
    pages = result.get("pages") or []
    for page_index, page in enumerate(pages, start=1):
        if not isinstance(page, dict):
            continue
        page_number = page.get("page_number") or page_index
        page_heatmap = page.get("heatmap") or {}
        for container_name in ("issues",):
            for row in page.get(container_name) or []:
                if isinstance(row, dict):
                    yield {**row, "_page_heatmap": page_heatmap}, int(page_number), container_name
        risk = page.get("risk") or {}
        for row in risk.get("findings") or []:
            if isinstance(row, dict):
                yield {**row, "_page_heatmap": page_heatmap}, int(page_number), "risk"
        raw_analysis = risk.get("raw_analysis") or {}
        raw_regions = raw_analysis.get("regions") or []
        if isinstance(raw_regions, dict):
            raw_regions = raw_regions.get("regions") or []
        for row in raw_regions:
            if isinstance(row, dict):
                yield {**row, "_page_heatmap": page_heatmap}, int(page_number), "risk_regions"
    if not pages:
        for row in result.get("findings") or []:
            if isinstance(row, dict):
                yield row, row.get("page"), "document"


def build_document_tampering(
    result: Dict[str, Any],
    *,
    analysis_dir: str | Path,
    evidence_id: str,
) -> Dict[str, Any]:
    """Create and persist localized findings from existing document output."""
    findings: List[Dict[str, Any]] = []
    for row, page, source in _iter_page_rows(result):
        bbox = _xywh(row.get("bbox") or row.get("bounding_box") or row.get("location"))
        confidence = _confidence(row)
        if bbox is None or confidence is None:
            # No localization or measurable detector confidence: no finding.
            continue
        category = _category(row)
        description = str(
            row.get("description")
            or row.get("reason")
            or row.get("what")
            or row.get("technical_reason")
            or row.get("type")
            or "Localized document observation."
        )
        polygon = _polygon(row, bbox)
        finding = {
            "id": str(row.get("id") or row.get("finding_id") or f"DOC-{len(findings) + 1:03d}"),
            "category": category,
            "type": str(row.get("type") or row.get("anomaly_type") or row.get("module") or "document_anomaly"),
            "severity": _severity(row, category),
            "confidence": confidence,
            "bbox": bbox,
            "polygon": polygon,
            "description": description,
            "human_summary": _human_summary(category, row, description),
            "technical_reason": str(row.get("technical_reason") or row.get("reason") or description),
            "recommended_action": str(row.get("recommended_action") or row.get("recommendation") or _recommendation(category)),
            "page": page,
            "source": source,
            "mask": row.get("mask") or row.get("mask_path") or row.get("mask_url"),
            "center_point": [
                round(bbox[0] + bbox[2] / 2.0, 2),
                round(bbox[1] + bbox[3] / 2.0, 2),
            ],
            "heatmap_layer": (
                row.get("heatmap_layer")
                or row.get("heatmap")
                or (row.get("_page_heatmap") or {}).get("heatmap")
            ),
        }
        findings.append(finding)

    payload = {
        "status": "completed",
        "available": True,
        "detector": "existing_document_forensics",
        "evidence_id": evidence_id,
        "finding_count": len(findings),
        "findings": findings,
    }
    analysis_dir = Path(analysis_dir)
    analysis_dir.mkdir(parents=True, exist_ok=True)
    temporary = analysis_dir / "document_tampering.tmp"
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(analysis_dir / "document_tampering.json")
    update_forensic_dossier(analysis_dir, payload, section="document_tampering")
    return payload


__all__ = ["build_document_tampering"]
