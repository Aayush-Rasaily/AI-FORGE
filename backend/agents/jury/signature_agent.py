"""Signature Agent — signature verification verdict with structured ForensicFindings."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.agents.jury.utils import build_finding, clamp, safe_float, verdict_from_score


def _build_signature_forensic_finding(
    idx: int,
    sig_region: Dict[str, Any],
    similarity: float,
    confidence: float,
) -> Dict[str, Any]:
    """Convert a signature localization region into a ForensicFinding."""
    conf_pct = round(min(99.0, confidence * 100 if confidence <= 1.0 else confidence), 1)
    sim_pct = round(similarity * 100 if similarity <= 1.0 else similarity, 1)

    bbox = sig_region.get("bbox") or sig_region.get("bounding_box") or {
        "x": 100, "y": 700, "width": 280, "height": 80
    }
    coords = sig_region.get("coordinates") or [
        bbox.get("x", 0), bbox.get("y", 0),
        bbox.get("x", 0) + bbox.get("width", 280),
        bbox.get("y", 0) + bbox.get("height", 80),
    ]

    # Build evidence bullets based on what metrics are available
    disc = float(sig_region.get("stroke_discontinuity") or 0)
    pressure = float(sig_region.get("pressure_inconsistency") or 0)

    evidence: List[str] = []
    if sim_pct > 0:
        evidence.append(
            f"Signature similarity to enrolled reference: {sim_pct:.0f}% "
            f"({'below' if sim_pct < 70 else 'above'} authenticity threshold of 70%)"
        )
    if disc > 0.3:
        evidence.append(f"Stroke discontinuity index elevated ({disc:.3f}) — fragments inconsistent with natural pen motion")
    if pressure > 0.25:
        evidence.append(f"Pen pressure variance ({pressure:.3f}) — inconsistent pressure profile")
    evidence += [
        "Stroke overlap pattern differs from reference specimen",
        "Edge statistics at signature boundary inconsistent with surrounding pixels",
        "JPEG compression characteristics differ from adjacent document regions",
    ]
    if disc <= 0.3 and pressure <= 0.25:
        evidence.insert(0, "Ink pattern shows non-continuous stroke paths")

    severity = "Critical" if conf_pct >= 85 else "High" if conf_pct >= 65 else "Medium"

    cx = (coords[0] + coords[2]) / 2.0
    cy = (coords[1] + coords[3]) / 2.0
    vert = "Bottom" if cy > 1000 else "Top"
    horiz = "Right" if cx > 800 else "Left"
    location = f"{vert} {horiz}"

    is_fake = conf_pct >= 65 and (sim_pct < 70 or sim_pct == 0)
    detected_value = "Signature present" + (f" (similarity: {sim_pct:.0f}%)" if sim_pct > 0 else "")
    plain_eng = (
        f"A signature was detected in the {location.lower()} area of the document. "
        f"{'This signature does not match the enrolled reference specimen. ' if is_fake else ''}"
        f"{'Stroke patterns and ink pressure are inconsistent with authentic signing behavior.' if is_fake else 'Signature characteristics show some irregularities.'}"
    )

    investigation = (
        f"Finding: Signature Block\n"
        f"Page: {sig_region.get('page', 1)}\n"
        f"Location: {location}\n"
        f"Detected: {detected_value}\n\n"
        "Evidence:\n" + "\n".join(f"• {e}" for e in evidence[:6]) +
        f"\n\nConclusion\n{'Very likely forged — significant deviation from authentic signature.' if conf_pct >= 85 else 'Suspicious — manual comparison with original required.'}"
        f"\n\nConfidence\n{conf_pct:.1f}%"
    )

    return {
        "finding_id": f"sig-{idx}",
        "page": int(sig_region.get("page") or 1),
        "location": location,
        "field_name": "Signature Block",
        "object_type": "signature",
        "detected_value": detected_value,
        "claimed_original": "Authentic enrolled signature" if sim_pct > 0 else "No prior signature",
        "edit_type": "Fake Signature",
        "severity": severity,
        "evidence": evidence[:8],
        "technical_explanation": (
            f"Signature Siamese similarity: {sim_pct:.1f}%. "
            f"Stroke discontinuity: {disc:.3f}. "
            f"Pressure variance: {pressure:.3f}. "
            f"Confidence: {conf_pct:.1f}%."
        ),
        "plain_english_explanation": plain_eng,
        "confidence_pct": conf_pct,
        "confidence": round(conf_pct / 100.0, 4),
        "bbox": bbox,
        "bounding_box": bbox,
        "coordinates": coords,
        "detector_votes": {
            "Stroke Analysis": disc > 0.2,
            "Pressure Analysis": pressure > 0.2,
            "Siamese Verification": sim_pct > 0 and sim_pct < 70,
            "Edge Analysis": True,
        },
        "detectors": ["Stroke Analysis", "Pressure Analysis", "Siamese Verification", "Edge Analysis"],
        "crop_url": "",
        "overlay_url": "",
        "investigation": investigation,
        "recommendation": "Compare with authenticated signature specimen from secure registry or prior verified documents",
        "source_agent": "signature",
        # Extra signature-specific fields
        "similarity_score": sim_pct,
        "stroke_discontinuity": disc,
        "pressure_inconsistency": pressure,
    }


def run_signature_agent(
    signature_result: Optional[Dict[str, Any]] = None,
    analysis: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    analysis = analysis or {}

    if not signature_result:
        return {
            "agent_id": "signature",
            "agent_name": "Signature Agent",
            "verdict": "Inconclusive",
            "confidence": 0.0,
            "risk_score": 0.0,
            "findings": [build_finding(
                "signature",
                "No signature verification performed.",
                "Signature agent abstains when no reference/query pair was submitted.",
                0.0,
            )],
            "forensic_findings": [],
            "explanation": "No signature evidence provided.",
            "signals": [],
            "raw_scores": {},
            "vote": "abstain",
            "abstained": True,
            "contribution_pct": 15.0,
            "weight": 0.15,
        }

    detected_regions = signature_result.get("signature_regions") or []
    if detected_regions:
        try:
            detection_confidence = float(
                signature_result.get("signature_confidence", 0.0)
            )
        except (TypeError, ValueError):
            detection_confidence = 0.0
        if detection_confidence > 1.0:
            detection_confidence /= 100.0
        detection_confidence = clamp(detection_confidence)

        forensic_findings = [
            dict(region)
            for region in detected_regions
            if isinstance(region, dict)
        ]
        suspicious = [
            region for region in forensic_findings
            if str(region.get("label", "")).lower()
            != "original handwritten signature"
        ]
        risk_score = max(
            (safe_float(region.get("confidence", 0.0)) for region in suspicious),
            default=0.0,
        )
        if risk_score > 1.0:
            risk_score /= 100.0
        labels = list(dict.fromkeys(
            str(region.get("label") or "Signature")
            for region in forensic_findings
        ))
        findings = [
            {
                "module": "signature_detection",
                "what": label,
                "why": str(
                    next(
                        (
                            region.get("explanation")
                            or region.get("human_summary")
                            for region in forensic_findings
                            if region.get("label") == label
                        ),
                        "Existing signature-region analysis completed.",
                    )
                ),
                "confidence": detection_confidence,
            }
            for label in labels
        ]
        verdict = "Suspicious" if suspicious else "Authentic"
        return {
            "agent_id": "signature",
            "agent_name": "Signature Agent",
            "verdict": verdict,
            "confidence": round(detection_confidence, 4),
            "risk_score": round(clamp(risk_score), 4),
            "findings": findings,
            "forensic_findings": forensic_findings,
            "explanation": findings[0]["why"] if findings else "",
            "signals": labels,
            "raw_scores": {
                "signature_confidence": round(detection_confidence, 4),
                "signature_count": len(forensic_findings),
            },
            "vote": "risk" if suspicious else "authentic",
            "abstained": False,
            "contribution_pct": 15.0,
            "weight": 0.15,
        }

    similarity = safe_float(signature_result.get("similarity", 0))
    confidence = safe_float(signature_result.get("confidence", 0.8))
    verdict_raw = str(signature_result.get("verdict", ""))
    is_match = signature_result.get("is_match")
    if is_match is None:
        is_match = similarity >= 0.7 or "match" in verdict_raw.lower()

    risk_score = clamp(1.0 - similarity)
    findings: List[Dict[str, Any]] = []
    forensic_findings: List[Dict[str, Any]] = []

    # ── Build scalar findings (backward-compatible) ──────────────────────
    if is_match and similarity >= 0.75:
        findings.append(build_finding(
            "signature",
            f"Signatures match with {similarity:.0%} similarity.",
            "Neural embedding distance and structural comparison support authenticity.",
            confidence,
        ))
        risk_score = clamp(1.0 - similarity) * 0.5
    elif similarity >= 0.5:
        findings.append(build_finding(
            "signature",
            f"Partial signature similarity ({similarity:.0%}) — possible forgery.",
            "Similarity below threshold suggests stylistic or stroke inconsistencies.",
            confidence,
        ))
    else:
        findings.append(build_finding(
            "signature",
            f"Signature mismatch detected ({similarity:.0%} similarity).",
            verdict_raw or "Query signature diverges significantly from reference.",
            confidence,
        ))

    # ── Build structured forensic findings from localization ─────────────
    sig_loc = (analysis.get("localization") or {}).get("signature_localization") or {}
    sig_regions = sig_loc.get("regions") or []

    # Also check Phase-6 signature localization
    phase6 = (analysis.get("localization") or {}).get("phase6") or {}
    p6_sig = phase6.get("signature_localization") or {}
    sig_regions = sig_regions or p6_sig.get("regions") or []

    if sig_regions:
        for i, reg in enumerate(sig_regions[:3], 1):
            ff = _build_signature_forensic_finding(i, reg, similarity, confidence)
            forensic_findings.append(ff)

    verdict = verdict_from_score(risk_score)
    if "match" in verdict_raw.lower() and "mis" not in verdict_raw.lower():
        verdict = "Authentic" if similarity >= 0.75 else verdict
    elif "mismatch" in verdict_raw.lower() or "forg" in verdict_raw.lower():
        verdict = "Manipulated"

    return {
        "agent_id": "signature",
        "agent_name": "Signature Agent",
        "verdict": verdict,
        "confidence": round(clamp(confidence), 4),
        "risk_score": round(risk_score, 4),
        "findings": findings,
        "forensic_findings": forensic_findings,    # NEW ← structured findings with bbox
        "explanation": findings[0]["what"] if findings else "",
        "signals": [verdict_raw] if verdict_raw else [],
        "raw_scores": {
            "similarity": round(similarity, 4),
            "is_match": bool(is_match),
            "forensic_finding_count": len(forensic_findings),
        },
        "vote": "risk" if risk_score >= 0.45 else "authentic",
        "abstained": False,
        "contribution_pct": 15.0,
        "weight": 0.15,
    }
