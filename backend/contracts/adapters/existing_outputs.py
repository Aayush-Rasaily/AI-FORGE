"""Adapters from existing AI-FORGE output shapes to canonical findings."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from backend.contracts.adapters.investigator_language import (
    hedge_evidence,
    investigator_location,
    investigator_title,
    investigator_type,
    metadata_date_finding,
    reference_comparison,
    what_changed_text,
)
from backend.contracts.forensic_finding import (
    ForensicFinding,
    build_finding,
    investigative_severity,
)

_SUSPICIOUS = (
    "tamper", "forg", "susp", "anomal", "mismatch", "alter", "inconsisten",
    "invalid", "risk", "duplicat", "insert", "manipul", "splic", "clone", "modif",
)


def _evidence(raw: Dict[str, Any]) -> List[str]:
    values = (
        raw.get("observed_evidence")
        or raw.get("evidence")
        or raw.get("reason")
        or raw.get("reasons")
        or raw.get("explanation")
        or raw.get("human_summary")
    )
    if isinstance(values, str):
        values = [values]
    return [
        hedge_evidence(value)
        for value in (values or [])
        if str(value or "").strip() and str(value).strip() not in {"—", "-"}
    ]


def _is_suspicious(raw: Dict[str, Any]) -> bool:
    text = " ".join(str(raw.get(k, "")) for k in ("verdict", "status", "type", "severity", "reason")).lower()
    return any(token in text for token in _SUSPICIOUS)


def _impact_and_review(finding_type: Any) -> tuple[str, str]:
    value = str(finding_type or "").lower()
    if any(token in value for token in ("amount", "financial", "invoice", "transaction")):
        return (
            "May affect the reliability of a stated financial value.",
            "Verify the value against an independently authenticated transaction or issuer record.",
        )
    if "signature" in value:
        return (
            "May affect the reliability of the authorization represented by the signature.",
            "Obtain the original signed evidence and compare it with an authenticated specimen.",
        )
    if "date" in value:
        return (
            "May affect reliance on the stated chronology of the document.",
            "Verify the date against independent source and custody records.",
        )
    if any(token in value for token in ("logo", "company", "entity")):
        return (
            "May indicate inconsistent representation of the issuing organization.",
            "Compare the identity elements with independently verified issuer records.",
        )
    if "metadata" in value:
        return (
            "May indicate file activity requiring contextual review; metadata alone does not establish alteration.",
            "Compare the file history with source-system and custody records.",
        )
    if "video" in value or "frame" in value:
        return (
            "May affect reliance on the recorded sequence at the identified time.",
            "Review adjacent frames and, where available, the source recording.",
        )
    return (
        "May affect the reliability of the identified evidence region.",
        "Compare the observation with an independently authenticated source.",
    )


def _adapt_rows(
    rows: Iterable[Dict[str, Any]],
    *,
    evidence_id: str,
    source_artifact: str,
    method: str,
    media_type: str,
    require_suspicious: bool = False,
) -> List[ForensicFinding]:
    findings: List[ForensicFinding] = []
    for raw in rows:
        if not isinstance(raw, dict) or (require_suspicious and not _is_suspicious(raw)):
            continue
        observed = _evidence(raw)
        if not observed:
            continue
        finding_type = investigator_type(
            raw.get("type") or raw.get("edit_type") or raw.get("manipulation") or method,
            raw.get("field") or raw.get("label"),
            raw.get("field_category"),
        )
        default_impact, default_review = _impact_and_review(finding_type)
        time_seconds = raw.get("time_seconds") or raw.get("timestamp_seconds") or raw.get("timestamp")
        title = investigator_title(
            finding_type=finding_type,
            field=raw.get("field") or raw.get("label"),
            media_type=raw.get("media_type") or media_type,
            time_seconds=time_seconds,
            supplied_title=raw.get("title"),
        )
        comparison = reference_comparison(raw, source_artifact)
        if isinstance(raw.get("structured_comparison"), dict):
            comparison = {**(comparison or {}), **raw["structured_comparison"]}
        changed = what_changed_text(comparison, observed, title)
        reason = " ".join(observed)
        supplied_severity = raw.get("severity") or raw.get("risk") or raw.get("risk_level")
        severity = investigative_severity(
            finding_type,
            supplied_severity,
            legal_or_authorization_impact=bool(
                raw.get("is_legal_document") or
                raw.get("critical_impact") or
                raw.get("authorization_impact")
            ),
        )
        provenance = [{
            "evidence_id": evidence_id,
            "source_artifact": source_artifact,
            "source_file": raw.get("source_file"),
            "method": method,
            "sha256": raw.get("sha256"),
            "observed_at": raw.get("observed_at"),
            "generated_at": raw.get("generated_at"),
        }]
        if isinstance(raw.get("reference_provenance"), dict):
            provenance.append(raw["reference_provenance"])
        finding_args = dict(
                evidence_id=evidence_id,
                title=title,
                finding_type=finding_type,
                verdict=raw.get("verdict") or "Potential anomaly requiring review",
                severity=severity,
                confidence=raw.get("confidence", raw.get("score", 0)),
                media_type=raw.get("media_type") or media_type,
                page=raw.get("page") or raw.get("page_number"),
                frame=raw.get("frame") or raw.get("frame_number"),
                time_seconds=time_seconds,
                bbox=raw.get("bbox") or raw.get("bounding_box"),
                bbox_format=raw.get("bbox_format"),
                coordinate_space=raw.get("coordinate_space", "pixels"),
                source_width=raw.get("source_width") or raw.get("image_width"),
                source_height=raw.get("source_height") or raw.get("image_height"),
                location=investigator_location(
                    page=raw.get("page") or raw.get("page_number"),
                    frame=raw.get("frame") or raw.get("frame_number"),
                    time_seconds=time_seconds,
                    field=raw.get("field") or raw.get("label"),
                    location=raw.get("location") or raw.get("where"),
                    finding_type=finding_type,
                ),
                observed_evidence=observed,
                short_explanation=raw.get("short_explanation") or changed,
                detailed_explanation=raw.get("detailed_explanation") or raw.get("technical_explanation") or reason,
                original_comparison=comparison,
                potential_impact=raw.get("potential_impact") or raw.get("impact") or default_impact,
                recommended_review=(
                    raw.get("recommended_review") or
                    raw.get("recommendation") or
                    default_review
                ),
                provenance=provenance,
            )
        try:
            findings.append(build_finding(**finding_args))
        except ValueError:
            # Invalid supplied regions are rejected. Rows that were genuinely
            # unlocalized already pass bbox=None and remain document-wide.
            continue
    return findings


def adapt_localization(data: Dict[str, Any], evidence_id: str, source: str) -> List[ForensicFinding]:
    rows = []
    for row in data.get("regions") or data.get("findings") or []:
        if isinstance(row, dict):
            rows.append({
                **row,
                "evidence": row.get("evidence") or row.get("source_signals") or row.get("detectors"),
            })
    return _adapt_rows(rows, evidence_id=evidence_id, source_artifact=source,
                       method="localization", media_type=data.get("media_type") or "image")


def adapt_jury_or_dossier(data: Dict[str, Any], evidence_id: str, source: str) -> List[ForensicFinding]:
    dossier = (data.get("fusion") or {}).get("forensic_dossier") or data.get("forensic_dossier") or data
    findings = adapt_signature_analysis(dossier, evidence_id, source)
    findings.extend(adapt_document_tampering(dossier, evidence_id, source))
    findings.extend(_adapt_rows(
        dossier.get("explanations") or dossier.get("findings") or [],
        evidence_id=evidence_id, source_artifact=source,
        method="jury_dossier", media_type="document",
    ))
    return findings


def adapt_ocr_document(data: Dict[str, Any], evidence_id: str, source: str) -> List[ForensicFinding]:
    rows = list(data.get("findings") or data.get("issues") or [])
    for page_index, page in enumerate(data.get("pages") or []):
        if not isinstance(page, dict):
            continue
        for issue in page.get("issues") or (page.get("intelligence") or {}).get("issues") or []:
            if isinstance(issue, dict):
                rows.append({
                    **issue,
                    "page": issue.get("page") or issue.get("page_number")
                            or page.get("page_number") or page_index + 1,
                    "source_width": issue.get("source_width") or page.get("width")
                                    or page.get("image_width"),
                    "source_height": issue.get("source_height") or page.get("height")
                                     or page.get("image_height"),
                })
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        category = str(row.get("field_category") or "")
        normalized.append({
            **row,
            "page": row.get("page") or data.get("page") or 1,
            "type": investigator_type(row.get("type"), row.get("field"), category),
        })
    return _adapt_rows(normalized,
                       evidence_id=evidence_id, source_artifact=source,
                       method="ocr_document_intelligence", media_type="document")


def adapt_signature_logo(data: Dict[str, Any], evidence_id: str, source: str) -> List[ForensicFinding]:
    rows: List[Dict[str, Any]] = []
    for key in ("signature_analysis", "signature_verification", "logo_analysis", "logo_verification"):
        value = data.get(key)
        if isinstance(value, dict):
            rows.append({**value, "type": value.get("type") or key})
    return _adapt_rows(rows, evidence_id=evidence_id, source_artifact=source,
                       method="signature_logo", media_type="document", require_suspicious=True)


def adapt_signature_analysis(
    data: Dict[str, Any], evidence_id: str, source: str
) -> List[ForensicFinding]:
    """Adapt the existing detector's localized signature findings."""
    payload = data.get("signature_analysis") if isinstance(
        data.get("signature_analysis"), dict
    ) else data
    if not isinstance(payload, dict):
        return []

    rows: List[Dict[str, Any]] = []
    for region in payload.get("signature_regions") or payload.get("findings") or []:
        if not isinstance(region, dict):
            continue
        explanation = str(
            region.get("explanation")
            or region.get("human_summary")
            or "Signature-region analysis completed."
        )
        rows.append({
            **region,
            "type": "signature",
            "field": "Signature",
            "title": region.get("label") or "Signature detected",
            "reason": explanation,
            "evidence": [explanation, region.get("human_summary")],
            "verdict": (
                "Original handwritten signature detected"
                if str(region.get("label", "")).lower()
                == "original handwritten signature"
                else "Potential signature alteration requiring review"
            ),
        })
    return _adapt_rows(
        rows,
        evidence_id=evidence_id,
        source_artifact=source,
        method="signature_detection",
        media_type=payload.get("media_type") or "image",
    )


def adapt_document_tampering(
    data: Dict[str, Any], evidence_id: str, source: str
) -> List[ForensicFinding]:
    """Adapt localized document tampering observations."""
    payload = data.get("document_tampering") if isinstance(
        data.get("document_tampering"), dict
    ) else data
    if not isinstance(payload, dict):
        return []

    rows: List[Dict[str, Any]] = []
    for finding in payload.get("findings") or []:
        if not isinstance(finding, dict):
            continue
        evidence = [
            finding.get("technical_reason"),
            finding.get("description"),
            finding.get("human_summary"),
        ]
        rows.append({
            **finding,
            "type": finding.get("type") or "document_tampering",
            "title": finding.get("human_summary") or finding.get("description"),
            "reason": finding.get("technical_reason") or finding.get("description"),
            "evidence": [item for item in evidence if item],
            "field": finding.get("field") or finding.get("type"),
            "verdict": "Potential document tampering requiring review",
        })
    return _adapt_rows(
        rows,
        evidence_id=evidence_id,
        source_artifact=source,
        method="document_forensics",
        media_type="document",
    )


def adapt_metadata_structure(data: Dict[str, Any], evidence_id: str, source: str) -> List[ForensicFinding]:
    rows: List[Dict[str, Any]] = []
    for key in ("metadata_forensics", "metadata", "document_structure"):
        value = data.get(key)
        if not isinstance(value, dict):
            continue
        date_finding = metadata_date_finding(value)
        if date_finding:
            title, evidence, explanation = date_finding
            rows.append({
                "type": "metadata_timestamp_inconsistency",
                "title": title,
                "reason": evidence,
                "short_explanation": explanation,
                "severity": "MEDIUM",
            })
        for item in value.get("anomalies") or value.get("warnings") or value.get("flags") or []:
            rows.append(item if isinstance(item, dict) else {
                "type": f"{key}_anomaly", "reason": str(item), "severity": "LOW",
            })
    date_finding = metadata_date_finding(data)
    if date_finding and not rows:
        title, evidence, explanation = date_finding
        rows.append({
            "type": "metadata_timestamp_inconsistency",
            "title": title,
            "reason": evidence,
            "short_explanation": explanation,
            "severity": "MEDIUM",
        })
    return _adapt_rows(rows, evidence_id=evidence_id, source_artifact=source,
                       method="metadata_structure", media_type="document")


def adapt_detector_outputs(data: Dict[str, Any], evidence_id: str, source: str) -> List[ForensicFinding]:
    rows = data.get("detector_outputs") or data.get("findings") or []
    normalized = []
    for row in rows:
        if not isinstance(row, dict) or not _is_suspicious(row):
            continue
        evidence = row.get("evidence") or row.get("reason") or row.get("signals")
        normalized.append({**row, "evidence": evidence, "type": row.get("type") or row.get("detector_name")})
    return _adapt_rows(normalized, evidence_id=evidence_id, source_artifact=source,
                       method="detector", media_type="image")


def adapt_video(data: Dict[str, Any], evidence_id: str, source: str) -> List[ForensicFinding]:
    rows = []
    for row in data.get("findings") or data.get("suspicious_intervals") or data.get("timeline") or []:
        if not isinstance(row, dict):
            continue
        rows.append({
            **row,
            "time_seconds": row.get("time_seconds") or row.get("timestamp_seconds")
                            or row.get("timestamp") or row.get("start_time"),
            "frame": row.get("frame") or row.get("frame_number") or row.get("start_frame"),
            "media_type": "video",
        })
    return _adapt_rows(rows, evidence_id=evidence_id, source_artifact=source,
                       method="video", media_type="video", require_suspicious=True)


def _xywh(raw: Any) -> Optional[Dict[str, float]]:
    if isinstance(raw, dict):
        x = raw.get("x", raw.get("left"))
        y = raw.get("y", raw.get("top"))
        width = raw.get("width", raw.get("w"))
        height = raw.get("height", raw.get("h"))
        if None in (x, y, width, height):
            return None
        return {"x": float(x), "y": float(y), "width": float(width), "height": float(height)}
    if isinstance(raw, (list, tuple)) and len(raw) >= 4:
        return {"x": float(raw[0]), "y": float(raw[1]), "width": float(raw[2]), "height": float(raw[3])}
    return None


def adapt_copy_move(data: Dict[str, Any], evidence_id: str, source: str) -> List[ForensicFinding]:
    payload = data.get("copy_move") if isinstance(data.get("copy_move"), dict) else data
    if not payload.get("copy_move_detected") and not payload.get("detected"):
        nested = ((data.get("tampering_detection") or {}).get("analysis") or {}).get("copy_move") or {}
        payload = nested if nested.get("copy_move_detected") else payload
    if not payload.get("copy_move_detected") and not payload.get("detected"):
        return []
    rows: List[Dict[str, Any]] = []
    regions = payload.get("duplicated_regions") or []
    for region in regions:
        if not isinstance(region, dict):
            continue
        src = _xywh((region.get("original_area") or {}).get("bbox"))
        dst = _xywh((region.get("copied_area") or {}).get("bbox"))
        if src and (src["width"] <= 0 or src["height"] <= 0):
            src = None
        if dst and (dst["width"] <= 0 or dst["height"] <= 0):
            dst = None
        bbox = src or dst
        classification = region.get("classification") or "duplicated region"
        rows.append({
            "type": "copy_move",
            "title": "Potential duplicated image region",
            "verdict": "Potential copy-move duplication requiring review",
            "severity": "MEDIUM",
            "confidence": region.get("confidence") or payload.get("copy_move_score") or payload.get("score"),
            "bbox": bbox,
            "location": "Image region A ↔ Image region B" if src and dst else "Duplicated image region",
            "reason": (
                "The two highlighted regions contain matching visual features consistent "
                "with duplicated image content."
            ),
            "short_explanation": (
                f"Matching keypoints were recorded between a source region and a {classification}."
            ),
            "structured_comparison": {
                "paired_regions": True,
                "region_a": src,
                "region_b": dst,
                "explanation": (
                    "The two highlighted regions contain matching visual features consistent "
                    "with duplicated image content."
                ),
            },
        })
    if not rows:
        rows.append({
            "type": "copy_move",
            "title": "Potential duplicated image region",
            "verdict": payload.get("verdict") or "Potential copy-move duplication requiring review",
            "severity": "MEDIUM",
            "confidence": payload.get("copy_move_score") or payload.get("score"),
            "reason": (
                "Matching visual features consistent with duplicated image content were recorded."
            ),
        })
    return _adapt_rows(rows, evidence_id=evidence_id, source_artifact=source,
                       method="copy_move", media_type=data.get("media_type") or "image")


def adapt_localized_detector_regions(
    data: Dict[str, Any], evidence_id: str, source: str
) -> List[ForensicFinding]:
    """Turn localized ELA/edge/frequency regions into findings without using global scores alone."""
    rows: List[Dict[str, Any]] = []
    tampering = data.get("tampering_detection") if isinstance(data.get("tampering_detection"), dict) else {}
    analysis = tampering.get("analysis") if isinstance(tampering.get("analysis"), dict) else {}
    sources = [
        ("ELA", "compression_inconsistency", analysis.get("ela") or {},
         "Localized compression inconsistency identified in the highlighted region.",
         "The highlighted region exhibits compression characteristics that differ from "
         "surrounding content, which may indicate subsequent editing."),
        ("edge_analysis", "edge_inconsistency", analysis.get("edge_inconsistency") or {},
         "Highlighted boundary shows edge characteristics inconsistent with surrounding content.",
         "Edge analysis recorded a localized discontinuity that differs from adjacent content."),
        ("wavelet", "frequency_inconsistency", analysis.get("wavelet") or {},
         "Frequency-domain characteristics differ between the highlighted region and surrounding content.",
         "Wavelet analysis recorded localized frequency characteristics that differ from nearby content."),
        ("frequency", "frequency_inconsistency", data.get("frequency") or {},
         "Frequency-domain characteristics differ between the highlighted region and surrounding content.",
         "Frequency analysis recorded localized characteristics that differ from nearby content."),
    ]
    for method, finding_type, payload, title, explanation in sources:
        if not isinstance(payload, dict):
            continue
        for region in payload.get("regions") or []:
            if not isinstance(region, dict):
                continue
            bbox = _xywh(region.get("bbox") or region)
            if not bbox or bbox["width"] <= 0 or bbox["height"] <= 0:
                continue
            rows.append({
                "type": finding_type,
                "title": title,
                "verdict": "Potential localized inconsistency requiring review",
                "severity": "MEDIUM",
                "confidence": region.get("confidence") or payload.get("suspicion_score"),
                "bbox": bbox,
                "location": "Highlighted region",
                "reason": region.get("reason") or explanation,
                "short_explanation": explanation,
                "supporting_methods": [method],
            })
    for region in tampering.get("regions") or data.get("regions") or []:
        if not isinstance(region, dict):
            continue
        detector = str(region.get("detector") or "").lower()
        bbox = _xywh(region.get("bbox") or region)
        if not bbox or bbox["width"] <= 0 or bbox["height"] <= 0:
            continue
        if "ela" in detector:
            finding_type, title = "compression_inconsistency", (
                "Localized compression inconsistency identified in the highlighted region."
            )
        elif "edge" in detector:
            finding_type, title = "edge_inconsistency", (
                "Highlighted boundary shows edge characteristics inconsistent with surrounding content."
            )
        elif "copy" in detector:
            continue
        else:
            continue
        rows.append({
            "type": finding_type,
            "title": title,
            "verdict": "Potential localized inconsistency requiring review",
            "severity": "MEDIUM",
            "confidence": region.get("confidence"),
            "bbox": bbox,
            "location": "Highlighted region",
            "reason": region.get("reason") or title,
        })
    return _adapt_rows(rows, evidence_id=evidence_id, source_artifact=source,
                       method="localized_detector", media_type=data.get("media_type") or "image")


def adapt_analysis(data: Dict[str, Any], evidence_id: str, source: str) -> List[ForensicFinding]:
    root = data.get("analysis") if isinstance(data.get("analysis"), dict) else data
    findings = []
    findings.extend(adapt_signature_analysis(root, evidence_id, source))
    findings.extend(adapt_document_tampering(root, evidence_id, source))
    findings.extend(adapt_signature_logo(root, evidence_id, source))
    findings.extend(adapt_metadata_structure(root, evidence_id, source))
    # A standalone Siamese verification result exposes its structured
    # signature findings under ``findings`` as well.  Do not adapt that same
    # list a second time as generic detector output.
    is_signature_result = (
        "signature_present" in root
        and "signature_regions" in root
    )
    if not is_signature_result:
        findings.extend(adapt_detector_outputs(root, evidence_id, source))
    findings.extend(adapt_copy_move(root, evidence_id, source))
    findings.extend(adapt_localized_detector_regions(root, evidence_id, source))
    for key in ("video_analysis", "video"):
        if isinstance(root.get(key), dict):
            findings.extend(adapt_video(root[key], evidence_id, source))
    doc = root.get("document_intelligence")
    if isinstance(doc, dict):
        findings.extend(adapt_ocr_document(doc, evidence_id, source))
    return findings
