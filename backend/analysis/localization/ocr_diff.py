"""OCR difference engine — structured text & key-value field modification report."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

from backend.utils.bbox_schema import normalize_bbox as _nb, bbox_to_xyxy as _bte

KEY_FIELD_PATTERNS = [
    (r"(?i)\b(total\s*amount|total\s*due|subtotal|net\s*amount|total)\b", "TOTAL AMOUNT", "Modified Amount"),
    (r"(?i)\b(policy\s*no|policy\s*number|policy\s*id|policy)\b", "Policy Number", "Changed Policy Number"),
    (r"(?i)\b(premium\s*amount|premium)\b", "Premium", "Modified Amount"),
    (r"(?i)\b(customer\s*name|insured\s*name|client\s*name|name|payee)\b", "Name", "Changed Name"),
    (r"(?i)\b(vehicle\s*number|registration\s*no|vehicle\s*no|reg\s*no|vin|wheel)\b", "Vehicle Number", "Changed Registration Number"),
    (r"(?i)\b(invoice\s*date|effective\s*date|issue\s*date|due\s*date|date)\b", "Date", "Changed Date"),
    (r"(?i)\b(authorized\s*signature|signature\s*block|signature)\b", "Signature Block", "Fake Signature"),
]

_SENSITIVE_PATTERNS = (
    (r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", "date", "Changed Date"),
    (r"\b\d{4}-\d{2}-\d{2}\b", "date", "Changed Date"),
    (r"[$₹€£]\s*[\d,]+\.?\d*", "currency", "Modified Amount"),
    (r"\b\d{5,}\b", "identifier", "Changed Policy Number"),
    (r"\b[A-Z]{2,}\d{4,}\b", "reference_id", "Changed Registration Number"),
)


def _classify_field_name(text: str) -> Tuple[str, str]:
    """Match key-value field name and edit classification."""
    for pattern, field_name, edit_type in KEY_FIELD_PATTERNS:
        if re.search(pattern, text):
            return field_name, edit_type

    for pattern, kind, edit_type in _SENSITIVE_PATTERNS:
        if re.search(pattern, text):
            return f"Field ({kind.title()})", edit_type

    if re.match(r"^\d+\.?\d*$", text.strip()):
        return "Numeric Field", "Modified Amount"

    return "Document Text Field", "Inserted Text"


def extract_structured_fields(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract structured key-value pairs and localized OCR field findings.
    Returns list of field findings with coordinates, evidence, impact, and recommendations.
    """
    ocr_data = analysis.get("ocr") or (analysis.get("document_intelligence") or {}).get("ocr") or {}
    doc_issues = (analysis.get("document_intelligence") or {}).get("issues") or []
    mismatch_regions = ocr_data.get("mismatch_regions") or ocr_data.get("regions") or []
    
    findings: List[Dict[str, Any]] = []

    # 1. Process explicit OCR mismatch regions
    for idx, item in enumerate(mismatch_regions, 1):
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or item.get("word") or item.get("detected") or "—").strip()
        orig = str(item.get("expected") or item.get("original") or "—").strip()
        field_name, edit_type = _classify_field_name(text)

        # Normalize raw bbox to canonical dict — handles list, dict, or missing
        raw_bbox = item.get("bbox") or item.get("coordinates") or [50, 50 + idx * 40, 350, 80 + idx * 40]
        canon_bbox = _nb(raw_bbox)
        xyxy = _bte(canon_bbox)

        conf = float(item.get("confidence") or item.get("score") or 0.88)
        conf_pct = round(conf * 100.0, 1) if conf <= 1.0 else round(conf, 1)

        findings.append({
            "finding_id": f"ocr-field-{idx}",
            "field_name": field_name,
            "field_modified": field_name,
            "detected_value": text,
            "claimed_original": orig if orig != text else "N/A (Original Baseline)",
            "edit_type": edit_type,
            "reason": item.get("reason") or f"Spatial typography & character inconsistency detected on {field_name}",
            # Always canonical dict — never a raw list
            "bbox": canon_bbox,
            "bounding_box": canon_bbox,
            # xyxy list for IoU math / pixel coordinates
            "coordinates": xyxy,
            "confidence": round(conf_pct / 100.0, 4),
            "confidence_pct": conf_pct,
            "severity": "Critical" if conf_pct >= 75 else "High" if conf_pct >= 55 else "Medium",
            "evidence": f"OCR mismatch: detected '{text}' vs expected '{orig}'. Font & compression boundary variance.",
            "possible_impact": f"High risk of {edit_type.lower()} in legal/financial document",
            "recommendation": f"Verify original source record for {field_name}",
            "page": int(item.get("page") or item.get("page_number") or 1),
        })

    # 2. Process Document Intelligence issues into structured field findings
    for idx, issue in enumerate(doc_issues, len(findings) + 1):
        if not isinstance(issue, dict):
            continue
        desc = issue.get("description", "")
        itype = issue.get("type", "")
        field_name, edit_type = _classify_field_name(desc)
        if itype == "edited_paragraph":
            edit_type = "Changed Paragraph"
        elif itype == "inserted_text":
            edit_type = "Inserted Text"
        elif itype == "fake_signature":
            edit_type = "Fake Signature"
            field_name = "Signature Block"

        # Normalize raw bbox to canonical dict — handles list, dict, or missing
        raw_bbox2 = issue.get("bbox") or issue.get("coordinates") or [100, 100 + idx * 30, 400, 130 + idx * 30]
        canon_bbox2 = _nb(raw_bbox2)
        xyxy2 = _bte(canon_bbox2)

        conf = float(issue.get("confidence") or issue.get("score") or 0.85)
        conf_pct = round(conf * 100.0, 1) if conf <= 1.0 else round(conf, 1)

        findings.append({
            "finding_id": f"ocr-field-{idx}",
            "field_name": field_name,
            "field_modified": field_name,
            "detected_value": desc[:60],
            "claimed_original": "Claimed Original Text",
            "edit_type": edit_type,
            "reason": issue.get("summary") or desc,
            # Always canonical dict — never a raw list
            "bbox": canon_bbox2,
            "bounding_box": canon_bbox2,
            # xyxy list for IoU math / pixel coordinates
            "coordinates": xyxy2,
            "confidence": round(conf_pct / 100.0, 4),
            "confidence_pct": conf_pct,
            "severity": "Critical" if conf_pct >= 75 else "High" if conf_pct >= 55 else "Medium",
            "evidence": "; ".join(issue.get("reasons") or [desc]),
            "possible_impact": f"Risk of unauthorized alteration on {field_name}",
            "recommendation": f"Cross-corroborate {field_name} with primary database record",
            "page": int(issue.get("page_number") or issue.get("page") or 1),
        })

    # Deduplicate findings by field_name & page
    seen = set()
    unique_findings = []
    for f in findings:
        key = (f["field_name"], f["page"], f["detected_value"])
        if key not in seen:
            seen.add(key)
            unique_findings.append(f)

    return unique_findings[:30]


def build_ocr_diff_report(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare OCR engine outputs and consensus mismatches.
    Returns complete structured Text & Field Modification Report.
    """
    field_findings = extract_structured_fields(analysis)

    summary = {
        "total_field_modifications": len(field_findings),
        "high_severity": sum(1 for m in field_findings if m.get("severity") in ("Critical", "High")),
        "amounts_modified": sum(1 for m in field_findings if m.get("edit_type") == "Modified Amount"),
        "dates_changed": sum(1 for m in field_findings if m.get("edit_type") == "Changed Date"),
        "names_changed": sum(1 for m in field_findings if m.get("edit_type") == "Changed Name"),
        "policy_numbers_changed": sum(1 for m in field_findings if m.get("edit_type") == "Changed Policy Number"),
        "reg_numbers_changed": sum(1 for m in field_findings if m.get("edit_type") == "Changed Registration Number"),
    }

    return {
        "success": True,
        "report_title": "Structured OCR Difference Report",
        "field_findings": field_findings,
        "modifications": field_findings,
        "summary": summary,
    }
