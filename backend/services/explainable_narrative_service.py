"""Court-ready narrative projection of localized forensic findings.

This module only translates persisted detector observations into plain,
calibrated language. It does not run or alter any forensic detector.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

_FORBIDDEN_TERMS = (
    (re.compile(r"\bAI\s+Model\b", re.IGNORECASE), "forensic analysis"),
    (re.compile(r"\bNeural\s+Network\b", re.IGNORECASE), "pattern analysis"),
    (re.compile(r"\bTransformer\b", re.IGNORECASE), "text analysis"),
    (re.compile(r"\bDetector\s+Confidence\b", re.IGNORECASE), "measured confidence"),
    (re.compile(r"\bMachine\s+Learning\b", re.IGNORECASE), "automated analysis"),
    (re.compile(r"\bPrediction\b", re.IGNORECASE), "assessment"),
)

_TYPE_RULES = (
    (("amount", "invoice", "currency", "total", "modified_numbers", "number_modification"),
     "amount"),
    (("date",), "date"),
    (("policy",), "policy"),
    (("logo",), "logo"),
    (("seal", "stamp"), "seal"),
    (("signature",), "signature"),
    (("font", "spacing", "baseline", "alignment", "line_break"), "font"),
    (("copy", "clone", "duplicat"), "copy_move"),
    (("remov", "delet"), "removal"),
    (("insert", "object_insertion"), "insertion"),
    (("noise",), "noise"),
    (("compression", "jpeg", "ela"), "compression"),
    (("metadata",), "metadata"),
    (("deepfake", "face", "synthetic"), "deepfake"),
    (("text", "ocr", "character", "replacement"), "text"),
)

_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "amount": {
        "title": "Edited Invoice Amount",
        "observation": "The numerical amount in the localized region appears to have been modified.",
        "reason": "The localized value is inconsistent with the surrounding text rendering, spacing, or character structure.",
        "impact": "The stated financial amount may not represent the original transaction or document.",
        "recommendation": "Verify the amount against the issuer's original invoice or financial record.",
    },
    "date": {
        "title": "Modified Date",
        "observation": "The date in the localized region shows signs of post-creation alteration.",
        "reason": "The date presentation differs from adjacent document content or other recorded date evidence.",
        "impact": "The document's chronology and validity period may be misstated.",
        "recommendation": "Confirm the date against the issuing system, correspondence, or original document.",
    },
    "policy": {
        "title": "Edited Policy Number",
        "observation": "The policy identifier in the localized region appears to have been edited.",
        "reason": "The identifier has localized text or rendering characteristics inconsistent with surrounding content.",
        "impact": "The document may be associated with the wrong policy or claim record.",
        "recommendation": "Reconcile the identifier with the insurer's authoritative policy record.",
    },
    "logo": {
        "title": "Logo Replacement",
        "observation": "The company logo appears to have been inserted or replaced.",
        "reason": "The localized logo region differs from the surrounding document in rendering or compression characteristics.",
        "impact": "The document's stated source or institutional identity may be misrepresented.",
        "recommendation": "Verify the logo and document with the issuing organization.",
    },
    "seal": {
        "title": "Seal or Stamp Replacement",
        "observation": "The seal or stamp in the localized region appears to have been added or replaced.",
        "reason": "The seal boundary and local image characteristics are inconsistent with the surrounding page.",
        "impact": "The apparent authorization or certification may not be genuine.",
        "recommendation": "Request the original certified document and confirm the seal with its issuing authority.",
    },
    "signature": {
        "title": "Signature Insertion",
        "observation": "A signature in the localized region appears to have been digitally inserted or altered.",
        "reason": "The signature boundary, blending, or local paper texture differs from the surrounding document.",
        "impact": "The document may not have been signed in the manner or by the person indicated.",
        "recommendation": "Request the original signed document and compare it with an authenticated specimen.",
    },
    "font": {
        "title": "Font or Text Layout Change",
        "observation": "The localized text uses rendering or layout characteristics that differ from adjacent text.",
        "reason": "Font metrics, spacing, baseline, or alignment are inconsistent within the same document context.",
        "impact": "The affected wording or value may have been added or replaced after the document was created.",
        "recommendation": "Compare the affected text with the original source file or a verified copy.",
    },
    "copy_move": {
        "title": "Duplicated Image Region",
        "observation": "The localized regions contain visual features consistent with duplicated content.",
        "reason": "Matching local features or repeated image structure links the highlighted regions.",
        "impact": "Content may have been copied, cloned, or repositioned to change the apparent record.",
        "recommendation": "Review both localized regions against the original image or document source.",
    },
    "removal": {
        "title": "Removed Document Content",
        "observation": "The localized region is consistent with removal or concealment of document content.",
        "reason": "The region shows an interruption or replacement pattern inconsistent with nearby content.",
        "impact": "Relevant wording, values, or visual evidence may no longer be present.",
        "recommendation": "Obtain the original document and inspect the affected area independently.",
    },
    "insertion": {
        "title": "Inserted Document Object",
        "observation": "An object or text element appears to have been inserted into the localized region.",
        "reason": "The inserted region has boundaries or rendering characteristics that differ from its surroundings.",
        "impact": "The inserted content may change the meaning or apparent authenticity of the document.",
        "recommendation": "Verify the affected object against the original source and issuing organization.",
    },
    "noise": {
        "title": "Noise Inconsistency",
        "observation": "The localized region has a different noise pattern from surrounding content.",
        "reason": "Local image residuals are inconsistent with the neighboring document or image background.",
        "impact": "The region may have undergone separate editing, recompression, or insertion.",
        "recommendation": "Review the original file and preserve the source media for further examination.",
    },
    "compression": {
        "title": "Compression Inconsistency",
        "observation": "The localized region has compression characteristics that differ from surrounding content.",
        "reason": "The measured compression or resampling response is inconsistent within the same image or page.",
        "impact": "The region may have been edited or recompressed after the rest of the material was created.",
        "recommendation": "Verify the region against the original uncompressed or issuer-provided source.",
    },
    "metadata": {
        "title": "Metadata Inconsistency",
        "observation": "The file metadata contains an inconsistency relevant to the stated document history.",
        "reason": "Recorded creation, modification, software, or producer information does not align with the available context.",
        "impact": "The file history cannot be accepted as consistent without independent verification.",
        "recommendation": "Preserve the original file and verify its timeline with custodial or source records.",
    },
    "deepfake": {
        "title": "Potential Synthetic Media Region",
        "observation": "The localized media region contains characteristics requiring review for synthetic alteration.",
        "reason": "The affected region differs from surrounding temporal, visual, or facial content.",
        "impact": "The apparent event or subject representation may not reflect the original recording.",
        "recommendation": "Preserve the source recording and obtain the original capture and device evidence.",
    },
    "text": {
        "title": "Text Replacement",
        "observation": "The localized text appears to have been added or replaced.",
        "reason": "The text differs from surrounding content in OCR interpretation, rendering, spacing, or alignment.",
        "impact": "The affected wording may alter the meaning of the submitted material.",
        "recommendation": "Verify the wording against the original file or an independent authoritative record.",
    },
    "unknown": {
        "title": "Localized Forensic Finding",
        "observation": "A measurable forensic inconsistency was identified in the localized region.",
        "reason": "The recorded examination identified a localized difference from surrounding content.",
        "impact": "The affected region requires verification before the material is relied upon.",
        "recommendation": "Compare the localized region with the original source and retain both files for review.",
    },
}


def _clean(value: Any) -> str:
    text = str(value or "").strip()
    for pattern, replacement in _FORBIDDEN_TERMS:
        text = pattern.sub(replacement, text)
    return text


def _load_dossier(analysis_dir: Path) -> Dict[str, Any]:
    try:
        loaded = json.loads((analysis_dir / "forensic_dossier.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {"findings": loaded}


def _iter_findings(
    dossier: Mapping[str, Any],
    analysis: Optional[Mapping[str, Any]],
) -> Iterable[Mapping[str, Any]]:
    localized = dossier.get("localized_regions")
    if isinstance(localized, Mapping):
        localized = localized.get("regions")
    if isinstance(localized, list):
        for finding in localized:
            if isinstance(finding, Mapping):
                yield finding

    if not localized:
        for section_name in ("document_tampering", "signature_analysis"):
            section = dossier.get(section_name)
            if not isinstance(section, Mapping):
                continue
            rows = section.get("findings") or section.get("signature_regions") or []
            for finding in rows:
                if isinstance(finding, Mapping) and finding.get("bbox"):
                    yield finding

    localized_analysis = (analysis or {}).get("localization") or {}
    if not localized and isinstance(localized_analysis, Mapping):
        for finding in localized_analysis.get("regions") or []:
            if isinstance(finding, Mapping) and finding.get("bbox"):
                yield finding


def _kind(row: Mapping[str, Any]) -> str:
    text = " ".join(
        _clean(row.get(key)).lower()
        for key in ("type", "category", "label", "edit_type", "title")
    )
    for terms, kind in _TYPE_RULES:
        if any(term in text for term in terms):
            return kind
    return "unknown"


def _bbox(row: Mapping[str, Any]) -> List[float]:
    raw = row.get("bbox") or row.get("bounding_box") or [0, 0, 0, 0]
    if isinstance(raw, Mapping):
        raw = [
            raw.get("x", raw.get("left", 0)),
            raw.get("y", raw.get("top", 0)),
            raw.get("width", raw.get("w", 0)),
            raw.get("height", raw.get("h", 0)),
        ]
    try:
        return [round(float(value), 2) for value in raw[:4]]
    except (TypeError, ValueError):
        return [0, 0, 0, 0]


def _location(row: Mapping[str, Any], bbox: List[float]) -> Dict[str, Any]:
    page = row.get("page") or row.get("page_number") or 1
    try:
        page = int(page)
    except (TypeError, ValueError):
        page = 1
    label = _clean(row.get("location") or row.get("label") or row.get("region"))
    center = row.get("center") or row.get("center_point")
    if not isinstance(center, (list, tuple)) or len(center) < 2:
        center = [
            round(bbox[0] + bbox[2] / 2, 2),
            round(bbox[1] + bbox[3] / 2, 2),
        ]
    else:
        try:
            center = [round(float(center[0]), 2), round(float(center[1]), 2)]
        except (TypeError, ValueError):
            center = [
                round(bbox[0] + bbox[2] / 2, 2),
                round(bbox[1] + bbox[3] / 2, 2),
            ]
    return {
        "page": page,
        "description": label or f"Page {page} localized region",
        "bbox": bbox,
        "center": center,
    }


def _evidence(row: Mapping[str, Any], reason: str) -> List[str]:
    values = (
        row.get("evidence")
        or row.get("supporting_methods")
        or row.get("source_signals")
        or row.get("detectors")
    )
    if isinstance(values, str):
        values = [values]
    evidence = [_clean(value) for value in (values or []) if _clean(value)]
    if not evidence:
        evidence = [reason]
    return list(dict.fromkeys(evidence))


def _build_finding(row: Mapping[str, Any], index: int, used_reasons: set[str]) -> Dict[str, Any]:
    kind = _kind(row)
    template = _TEMPLATES[kind]
    bbox = _bbox(row)
    location = _location(row, bbox)
    location_text = location["description"]
    reason = _clean(row.get("technical_reason") or row.get("technical_explanation") or "")
    if not reason:
        reason = template["reason"]
    if reason in used_reasons:
        reason = f"{reason} The observation is confined to {location_text}."
    used_reasons.add(reason)
    observation = _clean(row.get("human_summary") or row.get("description") or "")
    if not observation:
        observation = template["observation"]
    confidence = row.get("confidence")
    try:
        confidence = float(confidence) if confidence is not None else None
        if confidence is not None and confidence > 1:
            confidence /= 100.0
        if confidence is not None:
            confidence = round(max(0.0, min(1.0, confidence)), 4)
    except (TypeError, ValueError):
        confidence = None
    return {
        "id": _clean(row.get("id") or row.get("finding_id") or f"finding-{index:03d}"),
        "finding_id": _clean(row.get("finding_id") or row.get("id") or f"finding-{index:03d}"),
        "title": _clean(row.get("title") or template["title"]),
        "category": _clean(row.get("category") or kind),
        "type": _clean(row.get("type") or kind),
        "severity": _clean(row.get("severity") or "LOW").lower(),
        "confidence": confidence,
        "location": location,
        "observation": observation,
        "reason": reason,
        "evidence": _evidence(row, reason),
        "impact": _clean(row.get("impact") or row.get("potential_impact") or template["impact"]),
        "recommendation": _clean(row.get("recommendation") or row.get("recommended_action") or template["recommendation"]),
    }


def _overall_narrative(findings: List[Mapping[str, Any]]) -> str:
    if not findings:
        return (
            "The submitted material was examined using the available localized forensic "
            "records. No localized finding with a usable evidentiary region was available "
            "for a conclusion. The material should be verified against its original source "
            "before it is relied upon."
        )
    titles: List[str] = []
    for finding in findings:
        title = str(finding["title"])
        if title not in titles:
            titles.append(title)
    strongest = ", ".join(titles[:2])
    high_count = sum(
        1 for finding in findings
        if str(finding.get("severity", "")).lower() in {"critical", "high"}
    )
    if high_count:
        conclusion = (
            "Based on the available evidence, the material should be treated as "
            "potentially digitally manipulated until verified against its original source."
        )
    else:
        conclusion = (
            "The localized observations require corroboration against the original source "
            "before a definitive conclusion is reached."
        )
    return (
        "The submitted material was examined using the independent forensic observations "
        "recorded in the case dossier. "
        f"{len(findings)} localized finding(s) were identified. "
        f"The strongest observations relate to {strongest}. "
        "The findings are localized so that each affected region can be reviewed directly. "
        f"{conclusion}"
    )


def build_explainable_narrative(
    evidence_id: str,
    analysis_dir: str | Path,
    *,
    dossier: Optional[Dict[str, Any]] = None,
    analysis: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Write human-readable finding, summary, and narrative artifacts."""
    analysis_dir = Path(analysis_dir)
    dossier = dossier if isinstance(dossier, dict) else _load_dossier(analysis_dir)
    used_reasons: set[str] = set()
    findings = [
        _build_finding(row, index, used_reasons)
        for index, row in enumerate(_iter_findings(dossier, analysis), start=1)
    ]
    narrative = _overall_narrative(findings)
    severity_counts = {
        level: sum(1 for finding in findings if finding["severity"] == level)
        for level in ("critical", "high", "medium", "low")
    }
    summary = {
        "status": "completed",
        "evidence_id": evidence_id,
        "total_findings": len(findings),
        "severity_counts": severity_counts,
        "primary_findings": [finding["title"] for finding in findings[:5]],
        "overall_narrative": narrative,
        "recommendations": list(dict.fromkeys(finding["recommendation"] for finding in findings)),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    explainable = {
        "schema_version": "1.0",
        "evidence_id": evidence_id,
        "findings": findings,
        "investigation_summary": summary,
        "overall_narrative": narrative,
    }
    narrative_output = {
        "schema_version": "1.0",
        "evidence_id": evidence_id,
        "overall_narrative": narrative,
        "findings": findings,
    }
    for name, payload in (
        ("investigation_summary.json", summary),
        ("explainable_ai.json", explainable),
        ("forensic_narrative.json", narrative_output),
    ):
        temporary = analysis_dir / f"{name}.tmp"
        temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        temporary.replace(analysis_dir / name)

    dossier = dict(dossier)
    dossier["investigation_summary"] = summary
    dossier["overall_narrative"] = narrative
    dossier["human_findings"] = findings
    dossier_path = analysis_dir / "forensic_dossier.json"
    temporary = dossier_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(dossier, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(dossier_path)
    return explainable


__all__ = ["build_explainable_narrative"]
