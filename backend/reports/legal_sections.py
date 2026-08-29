"""
Legal report section builders — shared structured data for all export formats.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.utils.safe_mapping import snapshot_items


def build_detector_votes_table(
    detector_outputs: List[Dict[str, Any]],
    localization: Optional[Dict[str, Any]] = None,
    evidence_fusion: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Aggregate detector-level votes for legal evidence table."""
    rows: List[Dict[str, Any]] = []
    for d in detector_outputs or []:
        if not isinstance(d, dict):
            continue
        rows.append({
            "detector": str(d.get("detector_name", "unknown")).replace("_", " ").upper(),
            "score": round(float(d.get("score") or 0), 4),
            "confidence": round(float(d.get("confidence") or 0), 4),
            "reliability": round(float(d.get("reliability") or 0), 4),
            "status": d.get("status", "ok"),
            "verdict": "ELEVATED" if float(d.get("score") or 0) >= 0.28 else "NORMAL",
            "summary": (d.get("technical_reason") or "")[:300],
        })

    elevated = (evidence_fusion or {}).get("elevated_detectors") or []
    for name in elevated:
        if not any(r["detector"].lower().replace(" ", "_") == str(name).lower() for r in rows):
            rows.append({
                "detector": str(name).replace("_", " ").upper(),
                "score": None,
                "confidence": None,
                "reliability": None,
                "status": "elevated",
                "verdict": "ELEVATED",
                "summary": "Elevated by fusion engine",
            })

    region_votes: List[Dict[str, Any]] = []
    for reg in (localization or {}).get("regions") or []:
        votes = reg.get("detector_votes") or {}
        if votes:
            region_votes.append({
                "region_id": reg.get("id") or reg.get("label"),
                "label": reg.get("label") or reg.get("manipulation"),
                "votes": {k: bool(v) for k, v in votes.items()},
                "confidence": reg.get("confidence"),
            })

    return {
        "detector_rows": sorted(rows, key=lambda r: float(r.get("score") or 0), reverse=True),
        "region_vote_summary": region_votes[:20],
        "elevated_count": sum(1 for r in rows if r.get("verdict") == "ELEVATED"),
        "total_detectors": len(rows),
    }


def build_evidence_table(
    evidence_summary: Dict[str, Any],
    localization: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Primary evidence record + localized region evidence rows."""
    primary = {
        "evidence_id": evidence_summary.get("evidence_id"),
        "filename": evidence_summary.get("original_filename"),
        "media_type": evidence_summary.get("media_type"),
        "sha256": evidence_summary.get("sha256"),
        "sha512": evidence_summary.get("sha512"),
        "size_bytes": evidence_summary.get("size_bytes"),
        "intake_timestamp": evidence_summary.get("intake_timestamp"),
        "intake_user": evidence_summary.get("intake_user"),
        "chain_verified": evidence_summary.get("chain_verified"),
        "custody_events": evidence_summary.get("custody_events"),
    }
    region_rows = []
    for reg in (localization or {}).get("regions") or []:
        from backend.utils.bbox_schema import region_bbox as _rb  # noqa
        coords = _rb(reg)
        region_rows.append({
            "region_id": reg.get("id"),
            "label": reg.get("label") or reg.get("manipulation"),
            "type": reg.get("type") or reg.get("manipulation"),
            "confidence": reg.get("confidence") or reg.get("score"),
            "bounding_box": {
                "x": coords.get("x"),
                "y": coords.get("y"),
                "width": coords.get("width"),
                "height": coords.get("height"),
            },
            "mask_pixels": reg.get("mask_pixel_count"),
            "detector_votes": reg.get("detector_votes") or {},
            "explanation": reg.get("plain_english_explanation") or reg.get("reason"),
        })
    return {"primary": primary, "regions": region_rows}


def build_metadata_section(
    analysis: Dict[str, Any],
    technical_summary: Dict[str, Any],
) -> Dict[str, Any]:
    meta = analysis.get("metadata_forensics") or technical_summary.get("metadata_forensics") or {}
    exif = analysis.get("exif") or analysis.get("metadata") or meta.get("exif") or {}
    if isinstance(exif, dict) and exif.get("exif_summary"):
        exif = {**exif, **(exif.get("exif_summary") or {})}
    fields = []
    if isinstance(exif, dict):
        for k, v in snapshot_items(exif)[:40]:
            if k in ("exif_summary",):
                continue
            fields.append({"field": str(k), "value": str(v)[:500]})
    editing = meta.get("editing_software") or meta.get("software") or analysis.get("editing_software")
    return {
        "exif_fields": fields,
        "editing_software_detected": editing,
        "metadata_risk": meta.get("risk_score") or meta.get("score"),
        "metadata_flags": meta.get("flags") or meta.get("anomalies") or [],
        "camera_make": exif.get("Make") or exif.get("make") if isinstance(exif, dict) else None,
        "camera_model": exif.get("Model") or exif.get("model") if isinstance(exif, dict) else None,
        "software": exif.get("Software") or exif.get("software") if isinstance(exif, dict) else None,
        "created": exif.get("DateTimeOriginal") or exif.get("created") if isinstance(exif, dict) else None,
    }


def build_technical_findings(
    analysis: Dict[str, Any],
    tampering: Dict[str, Any],
    forensic_reasoning: Dict[str, Any],
    technical_summary: Dict[str, Any],
) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for f in (forensic_reasoning.get("findings") or [])[:12]:
        findings.append({
            "finding": f.get("finding"),
            "confidence": f.get("confidence"),
            "severity": f.get("severity"),
            "supporting": [
                f"{s.get('detector', '').upper()}: {s.get('observation', '')}"
                for s in (f.get("supporting_evidence") or [])[:6]
            ],
            "contradictory": [
                f"{c.get('detector', '').upper()}: {c.get('observation', '')}"
                for c in (f.get("contradictory_evidence") or [])[:4]
            ],
            "recommendation": f.get("recommendation"),
        })
    if not findings:
        for mod in (technical_summary.get("module_scores") or [])[:10]:
            findings.append({
                "finding": f"{mod.get('module')} signal detected",
                "confidence": round(float(mod.get("score") or 0) * 100, 1),
                "severity": "elevated" if float(mod.get("score") or 0) >= 0.5 else "normal",
                "supporting": [f"Module score: {mod.get('score')}"],
                "contradictory": [],
                "recommendation": None,
            })
    if tampering.get("verdict"):
        findings.insert(0, {
            "finding": f"Tampering analysis: {tampering.get('verdict')}",
            "confidence": tampering.get("confidence"),
            "severity": tampering.get("severity"),
            "supporting": [str(tampering.get("signals", tampering.get("reason", "")))[:300]],
            "contradictory": [],
            "recommendation": "Review tampering module output in technical appendix.",
        })
    return findings


def build_recommendations(
    executive_summary: Dict[str, Any],
    forensic_reasoning: Dict[str, Any],
    jury: Dict[str, Any],
) -> List[str]:
    recs: List[str] = []
    fusion = (jury or {}).get("fusion") or jury or {}
    for r in fusion.get("recommendations") or []:
        if r and str(r) not in recs:
            recs.append(str(r))
    for f in (forensic_reasoning.get("findings") or []):
        rec = f.get("recommendation")
        if rec and rec not in recs:
            recs.append(str(rec))
    if executive_summary.get("recommendation") and executive_summary["recommendation"] not in recs:
        recs.insert(0, str(executive_summary["recommendation"]))
    if not recs:
        risk = executive_summary.get("risk_level", "LOW")
        if risk == "HIGH":
            recs.append("Escalate to senior forensic examiner and preserve original evidence.")
            recs.append("Submit findings for legal review before court submission.")
        elif risk == "MEDIUM":
            recs.append("Conduct independent verification of elevated detector signals.")
        else:
            recs.append("No immediate escalation required; maintain chain of custody records.")
    return recs[:12]


def build_legal_sections(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Assemble all court-oriented structured sections."""
    return {
        "detector_votes": build_detector_votes_table(
            bundle.get("detector_outputs") or [],
            bundle.get("localization"),
            bundle.get("evidence_fusion"),
        ),
        "evidence_table": build_evidence_table(
            bundle.get("evidence_summary") or {},
            bundle.get("localization"),
        ),
        "metadata_section": build_metadata_section(
            bundle.get("analysis") or {},
            bundle.get("technical_summary") or {},
        ),
        "technical_findings": build_technical_findings(
            bundle.get("analysis") or {},
            bundle.get("tampering") or {},
            bundle.get("forensic_reasoning") or {},
            bundle.get("technical_summary") or {},
        ),
        "recommendations": build_recommendations(
            bundle.get("executive_summary") or {},
            bundle.get("forensic_reasoning") or {},
            bundle.get("jury") or {},
        ),
    }
