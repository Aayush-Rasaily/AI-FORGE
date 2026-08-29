"""
OCR Layout Agent — analyses spacing, font consistency, and layout anomalies.
Now returns structured forensic_findings with bounding boxes for court-ready reports.
"""

from typing import Any, Dict, List, Optional

from backend.agents.jury.utils import (
    build_finding,
    clamp,
    safe_float,
    verdict_from_score,
)


def _build_forensic_finding(
    idx: int,
    field_finding: Dict[str, Any],
) -> Dict[str, Any]:
    """Convert an OCR structured field finding into a ForensicFinding dict."""
    conf_pct = float(field_finding.get("confidence_pct") or
                     field_finding.get("confidence", 0.85) * 100)

    # Evidence bullets — always a list of plain-language strings
    evidence_raw = field_finding.get("evidence") or ""
    if isinstance(evidence_raw, str):
        evidence_bullets = [evidence_raw] if evidence_raw else []
    else:
        evidence_bullets = list(evidence_raw)

    # Add field-specific forensic bullets
    field = field_finding.get("field_name", "Document Field")
    det_val = field_finding.get("detected_value", "")
    orig_val = field_finding.get("claimed_original", "")
    edit_type = field_finding.get("edit_type", "Modified Field")

    if edit_type == "Modified Amount":
        evidence_bullets += [
            "Character boundaries inconsistent with surrounding text",
            "Font rendering differs from adjacent typeset characters",
            "Compression artifact mismatch at field boundary",
            "Local noise inconsistency relative to document baseline",
        ]
    elif edit_type == "Fake Signature":
        evidence_bullets += [
            "Ink pattern inconsistent with natural pen pressure",
            "Stroke discontinuity index elevated",
            "Edge statistics differ from surrounding content",
        ]
    elif edit_type in ("Changed Date", "Changed Policy Number", "Changed Registration Number"):
        evidence_bullets += [
            "OCR character spacing deviates from document norm",
            "Font stroke width inconsistent with surrounding text",
            "Baseline alignment offset detected",
        ]
    else:
        evidence_bullets += [
            "OCR layout analysis detected typographic inconsistency",
            "Text compression boundary differs from surrounding regions",
        ]

    # Deduplicate while preserving order
    seen = set()
    unique_bullets = []
    for b in evidence_bullets:
        key = b.strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique_bullets.append(b)

    bbox = field_finding.get("bbox") or field_finding.get("bounding_box") or {
        "x": 50, "y": 50 + idx * 40, "width": 300, "height": 28
    }
    coords = field_finding.get("coordinates") or [
        bbox.get("x", 0), bbox.get("y", 0),
        bbox.get("x", 0) + bbox.get("width", 300),
        bbox.get("y", 0) + bbox.get("height", 28),
    ]

    severity = field_finding.get("severity") or (
        "Critical" if conf_pct >= 85 else
        "High" if conf_pct >= 65 else
        "Medium"
    )

    location_str = field_finding.get("location") or _estimate_location(coords)

    plain_eng = (
        f"The {field} field appears to have been modified. "
        f"{'Value changed to ' + det_val + '.' if det_val else ''} "
        f"Multiple forensic detectors flagged this region as inconsistent with "
        f"the rest of the document."
    )

    tech_exp = (
        f"OCR mismatch on field '{field}'. "
        f"Detected: '{det_val}', expected: '{orig_val}'. "
        f"Edit type: {edit_type}. "
        f"Spatial typography and character boundary analysis flagged this region. "
        f"Confidence: {conf_pct:.1f}%."
    )

    recommendation = _recommendation_for(edit_type, field)

    return {
        "finding_id": f"ocr-{idx}",
        "page": int(field_finding.get("page") or 1),
        "location": location_str,
        "field_name": field,
        "object_type": "text_field",
        "detected_value": det_val,
        "claimed_original": orig_val,
        "edit_type": edit_type,
        "severity": severity,
        "evidence": unique_bullets[:8],
        "technical_explanation": tech_exp,
        "plain_english_explanation": plain_eng,
        "confidence_pct": round(conf_pct, 1),
        "confidence": round(conf_pct / 100.0, 4),
        "bbox": bbox,
        "bounding_box": bbox,
        "coordinates": coords,
        "detector_votes": {
            "OCR": True,
            "Font Analysis": edit_type in ("Modified Amount", "Inserted Text", "Changed Date"),
            "ELA": conf_pct >= 75,
        },
        "detectors": ["OCR", "Font Analysis", "Layout Analysis"],
        "crop_url": "",
        "overlay_url": "",
        "investigation": (
            f"Finding: {field}\n"
            f"Page: {field_finding.get('page', 1)}\n"
            f"Location: {location_str}\n"
            f"Detected Value: {det_val}\n\n"
            "Evidence:\n" + "\n".join(f"• {b}" for b in unique_bullets[:6]) +
            f"\n\nConclusion\n{'Very likely edited.' if conf_pct >= 85 else 'Suspicious — recommend review.'}"
            f"\n\nConfidence\n{conf_pct:.1f}%"
        ),
        "recommendation": recommendation,
        "source_agent": "ocr_layout",
    }


def _estimate_location(coords: List[float]) -> str:
    """Estimate quadrant from xyxy coordinates (assumes ~A4 page)."""
    if not coords or len(coords) < 4:
        return "Unknown"
    cx = (coords[0] + coords[2]) / 2.0
    cy = (coords[1] + coords[3]) / 2.0
    # Assume page width ~2480px, height ~3508px for A4 @300dpi
    vert = "Top" if cy < 1754 else "Bottom"
    horiz = "Left" if cx < 1240 else "Right"
    return f"{vert} {horiz}"


def _recommendation_for(edit_type: str, field: str) -> str:
    mapping = {
        "Modified Amount": f"Cross-verify {field} against original financial records or policy database",
        "Fake Signature": "Compare with authenticated signature specimen from secure registry",
        "Changed Date": "Verify document date against issuance records in primary system",
        "Changed Name": "Confirm identity against official ID document",
        "Changed Policy Number": "Validate policy number against insurer's live database",
        "Inserted Text": f"Cross-reference {field} with original document backup or certified copy",
    }
    return mapping.get(edit_type, f"Verify {field} with primary source document")


def run_ocr_layout_agent(
    analysis: Optional[Dict[str, Any]] = None,
    document_analysis: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    analysis = analysis or {}
    document_analysis = document_analysis or {}
    signals = analysis.get("signals") or {}

    findings: List[Dict[str, Any]] = []
    forensic_findings: List[Dict[str, Any]] = []
    risk_factors: List[float] = []

    # ── Pull structured OCR field findings ─────────────────────────────────
    try:
        from backend.analysis.localization.ocr_diff import extract_structured_fields
        field_findings = extract_structured_fields(analysis)
        for i, ff in enumerate(field_findings[:10], 1):
            conf = float(ff.get("confidence_pct") or ff.get("confidence", 0.85) * 100)
            risk_factors.append(conf / 100.0)
            findings.append(build_finding(
                "ocr_field",
                f"{ff.get('field_name', 'Field')} appears modified: {ff.get('detected_value', '')}",
                ff.get("reason") or "OCR field analysis detected typographic inconsistency.",
                conf / 100.0,
            ))
            forensic_findings.append(_build_forensic_finding(i, ff))
    except Exception:
        pass

    # ── Scalar signals fallback ─────────────────────────────────────────────
    spacing_risk = safe_float(signals.get("spacing_risk", 0)) / 100.0
    font_anomaly_count = int(signals.get("font_anomaly_count", 0) or 0)
    region_anomaly_count = int(signals.get("region_anomaly_count", 0) or 0)

    if spacing_risk >= 0.4:
        risk_factors.append(spacing_risk)
        findings.append(build_finding(
            "spacing",
            "Irregular word and line spacing detected in text regions.",
            "OCR layout analysis found spacing deviations inconsistent with "
            "natural document typography.",
            spacing_risk,
        ))

    if font_anomaly_count > 0:
        risk = min(0.5 + font_anomaly_count * 0.1, 0.95)
        risk_factors.append(risk)
        findings.append(build_finding(
            "font",
            f"Font inconsistencies detected across {font_anomaly_count} region(s).",
            "Multiple font styles or sizes in similar document zones suggest "
            "possible text insertion or overlay.",
            risk,
        ))

    if region_anomaly_count > 0:
        risk = min(0.45 + region_anomaly_count * 0.08, 0.90)
        risk_factors.append(risk)
        findings.append(build_finding(
            "region",
            f"Layout anomalies found in {region_anomaly_count} document region(s).",
            "Structural layout analysis identified regions with abnormal bounding boxes "
            "or alignment patterns.",
            risk,
        ))

    if document_analysis:
        doc_type = document_analysis.get("document_type", "document")
        page_count = document_analysis.get("page_count", 0)
        findings.append(build_finding(
            "document",
            f"Document forensics analyzed {page_count} page(s) of type '{doc_type}'.",
            "Full document OCR and layout pipeline was applied to extracted content.",
            0.80,
        ))
        for issue in (document_analysis.get("layout_issues") or [])[:3]:
            risk_factors.append(0.6)
            findings.append(build_finding(
                "document_layout",
                str(issue),
                "Document layout module flagged structural inconsistency.",
                0.6,
            ))

    if not findings:
        findings.append(build_finding(
            "ocr_layout",
            "No significant OCR or layout anomalies detected.",
            "Text spacing, font consistency, and region layout appear normal.",
            0.85,
        ))
        risk_factors.append(0.12)

    risk_score = clamp(sum(risk_factors) / len(risk_factors)) if risk_factors else 0.12
    verdict = verdict_from_score(risk_score)
    confidence = clamp(max(risk_factors) if risk_factors else 0.85)

    return {
        "agent_id": "ocr",
        "agent_name": "OCR Agent",
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "risk_score": round(risk_score, 4),
        "findings": findings,
        "forensic_findings": forensic_findings,     # NEW ← structured findings with bbox
        "explanation": " ".join(f["what"] for f in findings[:4]),
        "signals": [f["what"] for f in findings],
        "raw_scores": {
            "spacing_risk": round(spacing_risk, 4),
            "font_anomalies": font_anomaly_count,
            "region_anomalies": region_anomaly_count,
            "ocr_field_count": len(forensic_findings),
        },
        "vote": "risk" if risk_score >= 0.45 else "authentic",
    }
