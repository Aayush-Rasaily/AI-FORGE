"""Audited links and conservative comparisons between examined and reference evidence."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from backend.evidence.paths import find_evidence_file, get_analysis_dir
from backend.forensics.repository import (
    append_audit_log, append_custody_event, get_evidence_record,
)
from backend.forensics.user_context import InvestigatorContext

REFERENCE_FILE = "reference_link.json"
REFERENCE_COMPARISON_FILE = "reference_comparison.json"
AUTHENTICITY_STATUSES = frozenset({"verified", "unverified", "unknown"})
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")


def _validate_id(value: str) -> str:
    value = str(value or "").strip()
    if not _ID.fullmatch(value):
        raise ValueError("invalid evidence ID")
    if get_evidence_record(value) is None and find_evidence_file(value) is None:
        raise FileNotFoundError(f"evidence not found: {value}")
    return value


def _hashes(evidence_id: str) -> Dict[str, Optional[str]]:
    record = get_evidence_record(evidence_id) or {}
    if record.get("sha256"):
        return {"sha256": record.get("sha256"), "sha512": record.get("sha512")}
    path = find_evidence_file(evidence_id)
    if path is None:
        return {"sha256": None, "sha512": None}
    from backend.forensics.evidence_hash import compute_evidence_hashes
    hashes = compute_evidence_hashes(path)
    return {"sha256": hashes.get("sha256"), "sha512": hashes.get("sha512")}


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _extract_reliable_fields(evidence_id: str) -> Dict[str, Dict[str, Any]]:
    analysis_dir = get_analysis_dir(evidence_id, create=False)
    report = _load_json(analysis_dir / "ocr_difference_report.json")
    fields: Dict[str, Dict[str, Any]] = {}
    for item in report.get("findings") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("field") or "").strip()
        value = item.get("current")
        confidence = float(item.get("confidence") or 0)
        if name and value not in (None, "", "—") and confidence >= 0.70:
            fields[name.casefold()] = {
                "field": name, "value": value, "page": item.get("page"),
                "bbox": item.get("bbox"), "confidence": confidence,
            }
    document_map = _load_json(analysis_dir / "document_map.json")
    mapped = [
        item for item in document_map.get("fields") or []
        if isinstance(item, dict)
    ]
    label_counts: Dict[str, int] = {}
    for item in mapped:
        label = str(item.get("label") or "").strip().casefold()
        if label:
            label_counts[label] = label_counts.get(label, 0) + 1
    generic_labels = {"table cells", "document text", "paragraph", "unknown"}
    for item in mapped:
        name = str(item.get("label") or "").strip()
        key = name.casefold()
        value = item.get("text") or item.get("value")
        confidence = float(item.get("confidence") or 0)
        if (
            key and key not in generic_labels and label_counts.get(key) == 1 and
            value not in (None, "", "—") and confidence >= 0.70 and key not in fields
        ):
            fields[key] = {
                "field": name,
                "value": value,
                "page": item.get("page") or item.get("page_number"),
                "bbox": item.get("bbox") or item.get("bounding_box"),
                "confidence": confidence,
            }
    return fields


def _field_finding_type(field: str) -> str:
    value = field.casefold()
    if any(token in value for token in ("amount", "total", "price", "tax", "balance")):
        return "financial_value_difference"
    if "date" in value:
        return "date_difference"
    if "signature" in value:
        return "signature_difference"
    if any(token in value for token in ("company", "logo", "issuer")):
        return "entity_identity_difference"
    return "reference_value_difference"


def _media_geometry(evidence_id: str) -> Optional[Dict[str, Any]]:
    path = find_evidence_file(evidence_id)
    if path is None:
        return None
    suffix = path.suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}:
        try:
            from PIL import Image
            with Image.open(path) as image:
                return {"kind": "image", "width": image.width, "height": image.height}
        except Exception:
            return None
    if suffix == ".pdf":
        try:
            import fitz
            with fitz.open(path) as document:
                if document.page_count == 0:
                    return None
                rect = document[0].rect
                return {
                    "kind": "document",
                    "width": round(float(rect.width), 2),
                    "height": round(float(rect.height), 2),
                    "page_count": document.page_count,
                }
        except Exception:
            return None
    if suffix in {".mp4", ".mov", ".avi", ".mkv", ".webm"}:
        try:
            import cv2
            capture = cv2.VideoCapture(str(path))
            if not capture.isOpened():
                return None
            geometry = {
                "kind": "video",
                "width": int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "height": int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                "fps": round(float(capture.get(cv2.CAP_PROP_FPS)), 3),
                "frame_count": int(capture.get(cv2.CAP_PROP_FRAME_COUNT)),
            }
            capture.release()
            return geometry
        except Exception:
            return None
    return None


def _media_family(value: Any) -> str:
    media = str(value or "").lower()
    if "video" in media:
        return "video"
    if "image" in media:
        return "image"
    if any(token in media for token in ("pdf", "document", "scan")):
        return "document"
    return media


def _generate_image_difference(
    examined_id: str,
    reference_id: str,
    compatible: bool,
) -> Optional[str]:
    if not compatible:
        return None
    examined_path = find_evidence_file(examined_id)
    reference_path = find_evidence_file(reference_id)
    if examined_path is None or reference_path is None:
        return None
    try:
        from PIL import Image, ImageChops, ImageOps
        with Image.open(examined_path) as examined_image, Image.open(reference_path) as reference_image:
            if examined_image.size != reference_image.size:
                return None
            difference = ImageChops.difference(
                examined_image.convert("RGB"),
                reference_image.convert("RGB"),
            )
            output = get_analysis_dir(examined_id) / "reference_difference.png"
            ImageOps.autocontrast(difference).save(output)
            return f"/api/localization/{examined_id}/file/{output.name}"
    except Exception:
        return None


def build_reference_comparison(examined_id: str, reference_id: str) -> Dict[str, Any]:
    examined = get_evidence_record(examined_id) or {}
    reference = get_evidence_record(reference_id) or {}
    left = _extract_reliable_fields(examined_id)
    right = _extract_reliable_fields(reference_id)
    comparisons = []
    for key in sorted(set(left).intersection(right)):
        current, baseline = left[key], right[key]
        comparisons.append({
            "field": current["field"],
            "examined_value": current["value"],
            "reference_value": baseline["value"],
            "values_match": str(current["value"]).strip() == str(baseline["value"]).strip(),
            "correspondence": "reliable_field_label_match",
            "examined_page": current.get("page"),
            "reference_page": baseline.get("page"),
            # Geometry remains item-specific and is not projected between documents.
            "examined_bbox": current.get("bbox"),
            "reference_bbox": baseline.get("bbox"),
            "confidence": min(
                float(current.get("confidence") or 0),
                float(baseline.get("confidence") or 0),
            ),
        })
    examined_media = examined.get("media_type")
    reference_media = reference.get("media_type")
    examined_geometry = _media_geometry(examined_id)
    reference_geometry = _media_geometry(reference_id)
    compatible = bool(
        examined_media and
        reference_media and
        _media_family(examined_media) == _media_family(reference_media) and
        examined_geometry and
        reference_geometry and
        examined_geometry == reference_geometry and
        examined_geometry.get("kind") == "image"
    )
    difference_url = _generate_image_difference(examined_id, reference_id, compatible)
    return {
        "comparison_method": "reliable OCR field-label correspondence",
        "field_comparisons": comparisons,
        "page_image_compatibility": {
            "compatible": compatible,
            "examined_media_type": examined_media,
            "reference_media_type": reference_media,
            "examined_geometry": examined_geometry,
            "reference_geometry": reference_geometry,
            "note": (
                "Media type and measured geometry match; synchronized overlay review is available."
                if compatible else
                "Geometry compatibility is unconfirmed; no overlay correspondence is inferred."
            ),
        },
        "artifact_urls": {
            "examined_original": f"/api/localization/{examined_id}/original",
            "reference_original": f"/api/localization/{reference_id}/original",
            "examined_findings": f"/api/evidence/{examined_id}/findings",
            "reference_findings": f"/api/evidence/{reference_id}/findings",
            "difference": difference_url,
        },
        "side_by_side_available": True,
        "change_claim": (
            "Differences are reported only for reliably corresponding OCR fields."
            if comparisons else
            "No reliable field correspondence was available; no change is claimed."
        ),
    }


def _write_reference_comparison(
    examined_id: str,
    reference_id: str,
    comparison: Dict[str, Any],
) -> None:
    reference_hashes = _hashes(reference_id)
    findings = []
    for item in comparison.get("field_comparisons") or []:
        if item.get("values_match"):
            continue
        field = str(item.get("field") or "corresponding field")
        findings.append({
            "type": _field_finding_type(field),
            "title": f"{field} differs from the linked reference evidence",
            "verdict": "Difference identified; significance requires review",
            "confidence": item.get("confidence"),
            "page": item.get("examined_page"),
            "bbox": item.get("examined_bbox"),
            "field": field,
            "original": item.get("reference_value"),
            "current": item.get("examined_value"),
            "evidence": [
                f"Examined value: {item.get('examined_value')}",
                f"Linked reference value: {item.get('reference_value')}",
                "The values were matched using a reliable field label correspondence.",
            ],
            "reason": (
                "The examined and linked reference values differ. This comparison "
                "does not by itself establish which value is authentic."
            ),
            "recommended_review": "Verify the field against an independently authenticated source.",
            "reference_provenance": {
                "evidence_id": reference_id,
                "source_artifact": "ocr_difference_report.json",
                "method": "reference_field_comparison",
                "sha256": reference_hashes.get("sha256"),
            },
        })
    output = get_analysis_dir(examined_id) / REFERENCE_COMPARISON_FILE
    tmp = output.with_suffix(".tmp")
    tmp.write_text(
        json.dumps({
            "schema_version": "1.0",
            "examined_id": examined_id,
            "reference_id": reference_id,
            "findings": findings,
        }, indent=2),
        encoding="utf-8",
    )
    tmp.replace(output)


def get_reference_link(examined_id: str) -> Optional[Dict[str, Any]]:
    _validate_id(examined_id)
    path = get_analysis_dir(examined_id) / REFERENCE_FILE
    if not path.is_file():
        return None
    return _load_json(path).get("reference")


def create_reference_link(
    examined_id: str,
    reference_id: str,
    *,
    relationship: str,
    authenticity_status: str = "unknown",
    investigator: Optional[InvestigatorContext] = None,
) -> Dict[str, Any]:
    examined_id, reference_id = _validate_id(examined_id), _validate_id(reference_id)
    if examined_id == reference_id:
        raise ValueError("examined evidence cannot reference itself")
    status = str(authenticity_status or "unknown").lower()
    if status not in AUTHENTICITY_STATUSES:
        raise ValueError("authenticity_status must be verified, unverified, or unknown")
    relationship = str(relationship or "").strip()
    if not relationship:
        raise ValueError("relationship is required")
    investigator = investigator or InvestigatorContext("system", "System")
    examined_record = get_evidence_record(examined_id) or {}
    reference_record = get_evidence_record(reference_id) or {}
    linked_at = datetime.now(timezone.utc).isoformat()
    reference = {
        "examined_id": examined_id,
        "reference_id": reference_id,
        "relationship": relationship,
        "authenticity_status": status,
        "linked_at": linked_at,
        "linked_by": {"user_id": investigator.user_id, "name": investigator.display_name},
        "hashes": {
            "examined": _hashes(examined_id),
            "reference": _hashes(reference_id),
        },
        "comparison": build_reference_comparison(examined_id, reference_id),
        "provenance_caveat": (
            "The linked item is supporting evidence and is not authenticated "
            "unless authenticity_status is verified."
        ),
    }
    _write_reference_comparison(
        examined_id,
        reference_id,
        reference["comparison"],
    )
    path = get_analysis_dir(examined_id) / REFERENCE_FILE
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"schema_version": "1.0", "reference": reference}, indent=2), encoding="utf-8")
    tmp.replace(path)
    try:
        from backend.services.forensic_findings_service import build_forensic_findings
        build_forensic_findings(examined_id, get_analysis_dir(examined_id))
    except Exception:
        pass
    try:
        from backend.services.forensic_findings_service import build_forensic_findings
        build_forensic_findings(examined_id, path.parent)
    except Exception:
        pass
    try:
        hashes = reference["hashes"]["examined"]
        append_custody_event(
            examined_id, "REFERENCE_LINKED",
            f"Supporting reference linked: {reference_id}",
            sha256=hashes.get("sha256") or "", sha512=hashes.get("sha512") or "",
            actor_id=investigator.user_id, actor_name=investigator.display_name,
            investigation_id=examined_record.get("investigation_id"),
            metadata={"reference_id": reference_id, "relationship": relationship,
                      "authenticity_status": status, "reference_hashes": reference["hashes"]["reference"]},
        )
        append_audit_log(
            "REFERENCE_LINKED", user_id=investigator.user_id,
            user_name=investigator.display_name, resource_type="evidence_reference",
            resource_id=reference_id, evidence_id=examined_id,
            investigation_id=examined_record.get("investigation_id")
                              or reference_record.get("investigation_id"),
            client_ip=investigator.client_ip, details=reference,
        )
    except Exception:
        # The durable sidecar remains usable when legacy audit storage is unavailable.
        pass
    return reference


def delete_reference_link(
    examined_id: str,
    *,
    investigator: Optional[InvestigatorContext] = None,
) -> Dict[str, Any]:
    examined_id = _validate_id(examined_id)
    path = get_analysis_dir(examined_id) / REFERENCE_FILE
    if not path.is_file():
        raise FileNotFoundError("reference link not found")
    old = _load_json(path).get("reference") or {}
    path.unlink()
    comparison_path = get_analysis_dir(examined_id) / REFERENCE_COMPARISON_FILE
    comparison_path.unlink(missing_ok=True)
    try:
        from backend.services.forensic_findings_service import build_forensic_findings
        build_forensic_findings(examined_id, get_analysis_dir(examined_id))
    except Exception:
        pass
    try:
        from backend.services.forensic_findings_service import build_forensic_findings
        build_forensic_findings(examined_id, path.parent)
    except Exception:
        pass
    investigator = investigator or InvestigatorContext("system", "System")
    try:
        record = get_evidence_record(examined_id) or {}
        hashes = _hashes(examined_id)
        append_custody_event(
            examined_id, "REFERENCE_UNLINKED",
            f"Supporting reference removed: {old.get('reference_id', 'unknown')}",
            sha256=hashes.get("sha256") or "", sha512=hashes.get("sha512") or "",
            actor_id=investigator.user_id, actor_name=investigator.display_name,
            investigation_id=record.get("investigation_id"), metadata={"previous_reference": old},
        )
    except Exception:
        pass
    return old
