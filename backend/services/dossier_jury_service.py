"""Evidence-backed forensic Jury review.

This service is deliberately a reasoning and consensus layer. It reads the
persisted ``forensic_dossier.json`` and never invokes a detector, creates a
finding, or invents a measurement. Each specialist receives only the
finding rows relevant to its remit; the sixth specialist independently
reviews the complete finding set for corroboration and contradiction.
"""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

_VOTES = ("AUTHENTIC", "SUSPICIOUS", "MANIPULATED", "INCONCLUSIVE")
_DISPLAY_VOTES = {
    "AUTHENTIC": "Clean",
    "SUSPICIOUS": "Suspicious",
    "MANIPULATED": "Manipulated",
    "INCONCLUSIVE": "Inconclusive",
}
_RISK_LABELS = {
    "AUTHENTIC": "Low",
    "SUSPICIOUS": "Medium",
    "MANIPULATED": "High",
    "INCONCLUSIVE": "Inconclusive",
}
_SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}
_RISK_TERMS = (
    "manipulat",
    "tamper",
    "forg",
    "insert",
    "replace",
    "modif",
    "edit",
    "copied",
    "pasted",
    "anomal",
    "inconsisten",
    "suspicious",
    "different",
)
_CLEAN_TERMS = (
    "authentic",
    "consistent",
    "unchanged",
    "verified",
    "normal",
    "genuine",
    "original",
    "handwritten",
)

# The legacy tuple shape is retained for callers that imported EXPERTS.
# The first six fields define the new Jury panel; legacy_id is only an
# interoperability alias for existing presentation code.
EXPERTS: Tuple[
    Tuple[str, str, Tuple[str, ...], Tuple[str, ...], str, float], ...
] = (
    (
        "expert_01",
        "Document Integrity Expert",
        (
            "ocr", "text", "number", "amount", "date", "policy", "invoice",
            "font", "spacing", "baseline", "alignment", "layout",
            "structure", "object", "placement", "line break",
        ),
        (
            "ocr", "text", "document", "structure", "font", "layout",
            "tampering", "text_forensics",
        ),
        "ocr_text",
        0.20,
    ),
    (
        "expert_02",
        "Image Forensics Expert",
        (
            "ela", "compression", "noise", "edge", "clone", "copy", "resampling",
            "jpeg", "pixel", "wavelet", "splicing",
        ),
        (
            "image", "ela", "noise", "compression", "copy_move", "pixel",
            "forgery_localization",
        ),
        "image_forensics",
        0.20,
    ),
    (
        "expert_03",
        "Signature & Identity Expert",
        (
            "signature", "stroke", "curvature", "slant", "writer", "embedding",
            "ink", "handwriting", "genuine signature",
        ),
        ("signature", "identity", "signature_analysis", "signature_verification"),
        "signature_identity",
        0.15,
    ),
    (
        "expert_04",
        "Metadata & Provenance Expert",
        (
            "metadata", "exif", "timestamp", "software", "author", "producer",
            "editing history", "provenance", "chain of custody", "custody",
        ),
        ("metadata", "exif", "provenance", "custody"),
        "metadata",
        0.15,
    ),
    (
        "expert_05",
        "AI / Deepfake Expert",
        (
            "deepfake", "synthetic", "gan", "diffusion", "generative", "face",
            "facial", "face swap", "temporal", "generated", "blend",
        ),
        ("deepfake", "synthetic", "video", "generative", "gan"),
        "deepfake_synthetic",
        0.15,
    ),
    (
        "expert_06",
        "Evidence Correlation Expert",
        (
            "ocr", "text", "font", "ela", "compression", "noise", "edge",
            "copy", "signature", "metadata", "deepfake", "tamper", "logo",
            "seal", "object", "resampling",
        ),
        (),
        "evidence_correlation",
        0.15,
    ),
)


def _as_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number > 1:
        number /= 100.0
    return max(0.0, min(1.0, number))


def _load_dossier(analysis_dir: Path) -> Dict[str, Any]:
    path = analysis_dir / "forensic_dossier.json"
    if not path.is_file():
        raise FileNotFoundError(f"forensic_dossier.json not found in {analysis_dir}")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def _row_id(row: Mapping[str, Any]) -> str:
    return str(row.get("finding_id") or row.get("id") or "")


def _section_rows(section: Any) -> List[Mapping[str, Any]]:
    if not isinstance(section, Mapping):
        return []
    for key in ("findings", "signature_regions", "regions", "anomalies", "detections", "items"):
        rows = section.get(key)
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, Mapping) and _row_id(row)]
    return []


def _finding_rows(dossier: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    """Collect unique evidence rows from all dossier modules.

    The recursive walk handles new detector sections without requiring the
    Jury to know every detector's exact nesting. Jury output is excluded so
    rerunning the endpoint cannot vote on its own previous output.
    """
    rows: List[Mapping[str, Any]] = []
    seen: set[str] = set()
    excluded = {
        "ai_jury", "jury_analysis", "jury_experts", "jury_votes",
        "jury_consensus", "jury_summary", "jury_report",
    }

    def visit(value: Any, key: str = "", depth: int = 0) -> None:
        if depth > 10 or key.lower() in excluded:
            return
        if isinstance(value, Mapping):
            identifier = _row_id(value)
            if identifier and any(
                value.get(field) is not None
                for field in (
                    "type", "category", "title", "label", "description",
                    "human_summary", "technical_reason", "reason",
                    "severity", "confidence", "bbox", "polygon",
                )
            ) and identifier not in seen:
                seen.add(identifier)
                rows.append(value)
            for child_key, child in value.items():
                visit(child, str(child_key), depth + 1)
        elif isinstance(value, list):
            for child in value:
                visit(child, key, depth + 1)

    visit(dossier)
    return rows


def _row_text(row: Mapping[str, Any]) -> str:
    values = [
        row.get("module"), row.get("type"), row.get("category"), row.get("label"),
        row.get("title"), row.get("description"), row.get("human_summary"),
        row.get("technical_reason"), row.get("reason"), row.get("verdict"),
    ]
    return " ".join(str(value or "").lower() for value in values)


def _relevant_rows(
    rows: Sequence[Mapping[str, Any]],
    keywords: Sequence[str],
) -> List[Mapping[str, Any]]:
    return [row for row in rows if any(keyword in _row_text(row) for keyword in keywords)]


def _section_for_expert(
    dossier: Mapping[str, Any],
    aliases: Sequence[str],
) -> List[Mapping[str, Any]]:
    rows: List[Mapping[str, Any]] = []
    for key, value in dossier.items():
        if any(alias in str(key).lower() for alias in aliases):
            rows.extend(_section_rows(value))
    return rows


def _explicit_vote(row: Mapping[str, Any]) -> str:
    text = _row_text(row)
    verdict = str(row.get("verdict") or row.get("vote") or "").upper().replace(" ", "_")
    if verdict in _VOTES:
        return verdict
    if verdict in {"CLEAN", "AUTHENTIC"}:
        return "AUTHENTIC"
    if any(term in text for term in _CLEAN_TERMS) and not any(term in text for term in _RISK_TERMS):
        return "AUTHENTIC"
    severity = str(row.get("severity") or "").lower()
    if severity in {"critical", "high"}:
        return "MANIPULATED"
    if severity in {"medium", "low"}:
        return "SUSPICIOUS"
    risk = _as_float(
        row.get("risk_score")
        or row.get("metadata_risk_score")
        or row.get("forgery_probability")
        or row.get("tampering_probability")
    )
    if risk is not None:
        if risk >= 0.65:
            return "MANIPULATED"
        if risk >= 0.35:
            return "SUSPICIOUS"
        return "AUTHENTIC"
    similarity = _as_float(row.get("similarity_score") or row.get("similarity"))
    if similarity is not None and "signature" in text:
        if similarity >= 0.80:
            return "AUTHENTIC"
        if similarity >= 0.50:
            return "SUSPICIOUS"
        return "MANIPULATED"
    return "MANIPULATED" if any(term in text for term in _RISK_TERMS) else "INCONCLUSIVE"


def _row_confidence(row: Mapping[str, Any]) -> Optional[float]:
    for field in ("confidence", "confidence_pct", "score", "risk_score", "forgery_probability"):
        value = _as_float(row.get(field))
        if value is not None:
            return value
    similarity = _as_float(row.get("similarity_score") or row.get("similarity"))
    return similarity


def _module_confidence(
    dossier: Mapping[str, Any],
    aliases: Sequence[str],
) -> Optional[float]:
    values: List[float] = []
    for key, section in dossier.items():
        if not any(alias in str(key).lower() for alias in aliases) or not isinstance(section, Mapping):
            continue
        for field in ("confidence", "module_confidence", "analysis_confidence"):
            value = _as_float(section.get(field))
            if value is not None:
                values.append(value)
                break
    return round(sum(values) / len(values), 4) if values else None


def _risk_for_vote(vote: str) -> str:
    return _RISK_LABELS.get(vote, "Inconclusive")


def _recommendation(name: str, vote: str, evidence_ids: Sequence[str]) -> str:
    if vote == "MANIPULATED":
        if "Signature" in name:
            return "Obtain the original signed specimen and verify the questioned signature through documented comparison."
        if "Metadata" in name:
            return "Preserve the source file and compare its metadata and custody record with the issuing system."
        if "Image" in name or "Deepfake" in name:
            return "Retain the original media and examine the highlighted regions against a verified source."
        return "Verify the affected content against the original document or issuing record."
    if vote == "SUSPICIOUS":
        return "Conduct targeted review of the referenced regions and obtain an independent source for comparison."
    if vote == "AUTHENTIC":
        return "No adverse action is recommended from this specialty alone; retain the source and custody records."
    if evidence_ids:
        return "Obtain additional source evidence before reaching a conclusion."
    return "No recommendation can be made because this specialty has no corresponding dossier evidence."


def _make_expert_assessment(
    dossier: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    expert_id: str,
    expert_name: str,
    keywords: Sequence[str],
    aliases: Sequence[str],
    legacy_id: str,
    weight: float,
) -> Dict[str, Any]:
    relevant = _relevant_rows(rows, keywords)
    if not relevant and aliases:
        relevant = _section_for_expert(dossier, aliases)

    risk_rows = [row for row in relevant if _explicit_vote(row) in {"MANIPULATED", "SUSPICIOUS"}]
    clean_rows = [row for row in relevant if _explicit_vote(row) == "AUTHENTIC"]
    evidence_ids = [_row_id(row) for row in relevant if _row_id(row)]
    risk_ids = [_row_id(row) for row in risk_rows if _row_id(row)]
    clean_ids = [_row_id(row) for row in clean_rows if _row_id(row)]
    confidence_values = [
        confidence for row in relevant
        if (confidence := _row_confidence(row)) is not None
    ]

    module_confidence = _module_confidence(dossier, aliases)
    if not relevant and module_confidence is not None:
        # This is a measured module-level result, not an invented finding.
        vote = "AUTHENTIC"
        confidence = module_confidence
        evidence_basis = [alias for alias in aliases if any(alias in str(key).lower() for key in dossier)]
        reasoning = [
            f"{expert_name} found no adverse finding in the recorded module output.",
            f"The module reported measured evidence strength {confidence:.2f}.",
        ]
        summary = "The corresponding module reported no adverse finding."
        supporting = []
        contradicting: List[str] = []
        basis = evidence_basis
    elif not relevant:
        vote = "INCONCLUSIVE"
        confidence = 0.0
        reasoning = [f"{expert_name} found no corresponding evidence rows in the forensic dossier."]
        summary = "No relevant evidence was recorded for this specialty."
        supporting = []
        contradicting = []
        basis = []
    elif not confidence_values:
        vote = "INCONCLUSIVE"
        confidence = 0.0
        reasoning = [
            f"{expert_name} identified {len(relevant)} relevant dossier row(s),",
            "but no usable measured confidence was recorded for those rows.",
        ]
        summary = "Relevant evidence was recorded without a usable measurement."
        supporting = evidence_ids
        contradicting = []
        basis = []
    else:
        confidence = round(sum(confidence_values) / len(confidence_values), 4)
        if risk_rows and clean_rows:
            vote = "MANIPULATED" if any(
                _SEVERITY_RANK.get(str(row.get("severity") or "").lower(), 0) >= 3
                or _explicit_vote(row) == "MANIPULATED"
                for row in risk_rows
            ) else "SUSPICIOUS"
        elif risk_rows:
            vote = (
                "MANIPULATED"
                if any(
                    _SEVERITY_RANK.get(str(row.get("severity") or "").lower(), 0) >= 3
                    or _explicit_vote(row) == "MANIPULATED"
                    for row in risk_rows
                )
                else "SUSPICIOUS"
            )
        elif clean_rows and len(clean_rows) == len(relevant):
            vote = "AUTHENTIC"
        else:
            vote = "INCONCLUSIVE"
        labels = [
            str(row.get("type") or row.get("category") or "recorded finding")
            for row in relevant[:4]
        ]
        reasoning = [
            f"{expert_name} reviewed {', '.join(labels)}.",
            f"The relevant rows support a {_DISPLAY_VOTES[vote].lower()} assessment "
            f"with measured evidence strength {confidence:.2f}.",
        ]
        if risk_rows and clean_rows:
            reasoning.append("The specialty contains both adverse and consistent observations.")
        summary = (
            f"{len(risk_rows)} adverse and {len(clean_rows)} consistent "
            f"finding(s) were relevant to this specialty."
        )
        supporting = risk_ids if risk_ids else (clean_ids if vote == "AUTHENTIC" else evidence_ids)
        contradicting = clean_ids if risk_ids else []
        basis = []

    return {
        "id": expert_id,
        "name": expert_name,
        "vote": vote,
        "risk": _risk_for_vote(vote),
        "confidence": confidence,
        "summary": summary,
        "supporting_evidence": supporting,
        "reasoning": reasoning,
        "recommendation": _recommendation(expert_name, vote, supporting),
        # Compatibility fields used by the existing Jury presentation/API.
        "expert_id": legacy_id,
        "expert_name": expert_name,
        "supporting_findings": supporting,
        "contradicting_findings": contradicting,
        "reasoning_text": " ".join(reasoning),
        "evidence_basis": basis,
        "weight": weight,
    }


def _correlation_assessment(
    dossier: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    expert_id: str,
    expert_name: str,
    weight: float,
) -> Dict[str, Any]:
    measured = [row for row in rows if _row_confidence(row) is not None]
    risk_rows = [row for row in measured if _explicit_vote(row) in {"MANIPULATED", "SUSPICIOUS"}]
    clean_rows = [row for row in measured if _explicit_vote(row) == "AUTHENTIC"]
    inconclusive_rows = [row for row in rows if _explicit_vote(row) == "INCONCLUSIVE"]
    risk_ids = [_row_id(row) for row in risk_rows if _row_id(row)]
    clean_ids = [_row_id(row) for row in clean_rows if _row_id(row)]
    all_ids = [_row_id(row) for row in rows if _row_id(row)]
    confidence_values = [_row_confidence(row) for row in measured]
    confidence_values = [value for value in confidence_values if value is not None]

    if not measured:
        vote = "INCONCLUSIVE"
        confidence = 0.0
        summary = "The dossier contains no measured finding rows to correlate."
        reasoning = [f"{expert_name} could not correlate unmeasured or absent evidence."]
        supporting = all_ids
    elif risk_rows and not clean_rows:
        vote = "MANIPULATED" if any(
            _explicit_vote(row) == "MANIPULATED"
            or _SEVERITY_RANK.get(str(row.get("severity") or "").lower(), 0) >= 3
            for row in risk_rows
        ) else "SUSPICIOUS"
        confidence = round(sum(confidence_values) / len(confidence_values), 4)
        summary = (
            f"{len(risk_rows)} measured adverse finding(s) corroborate the same "
            "overall concern across the dossier."
        )
        reasoning = [
            f"{expert_name} correlated {len(measured)} measured finding row(s).",
            f"{len(risk_rows)} adverse row(s) support a {_DISPLAY_VOTES[vote].lower()} assessment.",
        ]
        supporting = risk_ids
    elif clean_rows and not risk_rows:
        vote = "AUTHENTIC"
        confidence = round(sum(confidence_values) / len(confidence_values), 4)
        summary = f"{len(clean_rows)} measured finding(s) were consistent with an unaltered record."
        reasoning = [
            f"{expert_name} found no adverse finding among {len(measured)} measured row(s).",
            "The recorded observations are mutually consistent.",
        ]
        supporting = clean_ids
    else:
        vote = "SUSPICIOUS"
        confidence = round(sum(confidence_values) / len(confidence_values), 4)
        summary = (
            f"The dossier contains {len(risk_rows)} adverse and {len(clean_rows)} "
            "consistent measured finding(s), requiring targeted review."
        )
        reasoning = [
            f"{expert_name} identified corroborating and contradictory observations.",
            "The mixed evidence prevents a clean assessment of the complete record.",
        ]
        supporting = risk_ids

    if inconclusive_rows:
        reasoning.append(f"{len(inconclusive_rows)} additional row(s) could not be measured.")
    return {
        "id": expert_id,
        "name": expert_name,
        "vote": vote,
        "risk": _risk_for_vote(vote),
        "confidence": confidence,
        "summary": summary,
        "supporting_evidence": supporting,
        "reasoning": reasoning,
        "recommendation": _recommendation(expert_name, vote, supporting),
        "expert_id": "evidence_correlation",
        "expert_name": expert_name,
        "supporting_findings": supporting,
        "contradicting_findings": clean_ids if risk_ids else [],
        "reasoning_text": " ".join(reasoning),
        "evidence_basis": [],
        "weight": weight,
    }


def _build_experts(
    dossier: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    assessments: List[Dict[str, Any]] = []
    for expert_id, name, keywords, aliases, legacy_id, weight in EXPERTS:
        if expert_id == "expert_06":
            assessment = _correlation_assessment(dossier, rows, expert_id, name, weight)
        else:
            assessment = _make_expert_assessment(
                dossier, rows, expert_id, name, keywords, aliases, legacy_id, weight
            )
        assessments.append(assessment)
    return assessments


def validate_finding_references(
    assessments: Iterable[Mapping[str, Any]],
    valid_finding_ids: Iterable[str],
) -> List[Dict[str, Any]]:
    """Remove references that are not present in the dossier."""
    valid = {str(identifier) for identifier in valid_finding_ids}
    cleaned: List[Dict[str, Any]] = []
    for assessment in assessments:
        item = dict(assessment)
        supporting = [
            str(identifier)
            for identifier in assessment.get("supporting_evidence")
            or assessment.get("supporting_findings")
            or []
            if str(identifier) in valid
        ]
        contradicting = [
            str(identifier)
            for identifier in assessment.get("contradicting_evidence")
            or assessment.get("contradicting_findings")
            or []
            if str(identifier) in valid
        ]
        item["supporting_evidence"] = supporting
        item["supporting_findings"] = supporting
        item["contradicting_evidence"] = contradicting
        item["contradicting_findings"] = contradicting
        cleaned.append(item)
    return cleaned


def _agreement_label(agreement: float, active_count: int, disagreement_count: int) -> str:
    if active_count == 0:
        return "Inconclusive"
    if agreement >= 83.0 and disagreement_count == 0:
        return "Very High"
    if agreement >= 66.0:
        return "High"
    if agreement >= 50.0:
        return "Medium"
    return "Low"


def _consensus(
    experts: List[Dict[str, Any]],
    valid_ids: set[str],
    evidence_id: str = "",
) -> Dict[str, Any]:
    counts = {vote: 0 for vote in _VOTES}
    for expert in experts:
        vote = str(expert.get("vote") or "INCONCLUSIVE").upper()
        if vote not in counts:
            vote = "INCONCLUSIVE"
        counts[vote] += 1
    active = [vote for vote in (str(expert.get("vote") or "").upper() for expert in experts) if vote != "INCONCLUSIVE"]

    if active:
        majority = max(("AUTHENTIC", "SUSPICIOUS", "MANIPULATED"), key=lambda vote: counts[vote])
        if counts[majority] <= len(active) / 2:
            majority = "INCONCLUSIVE"
    else:
        majority = "INCONCLUSIVE"

    evidence_weight = {vote: 0.0 for vote in _VOTES}
    for expert in experts:
        vote = str(expert.get("vote") or "INCONCLUSIVE").upper()
        if vote not in evidence_weight or vote == "INCONCLUSIVE":
            continue
        references = [
            identifier for identifier in expert.get("supporting_evidence") or []
            if identifier in valid_ids
        ]
        # Weight is based on measured evidence references and specialty
        # relevance, not on confidence alone.
        evidence_factor = 1.0 + min(len(references), 5) * 0.10
        evidence_weight[vote] += (
            float(expert.get("confidence") or 0.0)
            * float(expert.get("weight") or 0.0)
            * evidence_factor
        )
    weighted_vote = max(
        ("AUTHENTIC", "SUSPICIOUS", "MANIPULATED"),
        key=lambda vote: evidence_weight[vote],
    ) if any(evidence_weight.values()) else "INCONCLUSIVE"
    final_verdict = majority if majority != "INCONCLUSIVE" else weighted_vote
    if final_verdict == "INCONCLUSIVE" or evidence_weight.get(final_verdict, 0.0) == 0:
        final_verdict = "INCONCLUSIVE"

    disagreements: List[Dict[str, Any]] = []
    risk_experts = [expert for expert in experts if expert.get("vote") in {"MANIPULATED", "SUSPICIOUS"}]
    clean_experts = [expert for expert in experts if expert.get("vote") == "AUTHENTIC"]
    if risk_experts and clean_experts:
        risk_names = ", ".join(str(expert.get("name") or expert.get("expert_name")) for expert in risk_experts)
        clean_names = ", ".join(str(expert.get("name") or expert.get("expert_name")) for expert in clean_experts)
        risk_refs = sorted({
            identifier for expert in risk_experts
            for identifier in expert.get("supporting_evidence") or []
            if identifier in valid_ids
        })
        clean_refs = sorted({
            identifier for expert in clean_experts
            for identifier in expert.get("supporting_evidence") or []
            if identifier in valid_ids
        })
        disagreements.append({
            "type": "specialty_contradiction",
            "experts": [
                str(expert.get("id") or expert.get("expert_id"))
                for expert in risk_experts + clean_experts
            ],
            "supporting_findings": risk_refs,
            "contradicting_findings": clean_refs,
            "explanation": (
                f"{clean_names} found consistent evidence while {risk_names} identified "
                "adverse evidence. This indicates that the adverse signal may be localized "
                "or may reflect post-processing without a corresponding clean-module change."
            ),
        })

    disagreement_count = len(disagreements)
    agreement = round((max(counts.values()) / len(experts) * 100), 1) if experts else 0.0
    confidence_values = [
        float(expert.get("confidence") or 0.0)
        for expert in experts
        if str(expert.get("vote") or "").upper() != "INCONCLUSIVE"
    ]
    total_weight = sum(evidence_weight.values())
    winning_share = (
        evidence_weight.get(final_verdict, 0.0) / total_weight
        if total_weight and final_verdict != "INCONCLUSIVE"
        else 0.0
    )
    winning_confidence = max(
        [
            float(expert.get("confidence") or 0.0)
            for expert in experts
            if expert.get("vote") == final_verdict
        ] or [0.0]
    )
    overall_confidence = round(
        winning_share * (0.5 + 0.5 * winning_confidence), 4
    ) if final_verdict != "INCONCLUSIVE" else 0.0

    final_refs = sorted({
        identifier for expert in experts
        if expert.get("vote") == final_verdict
        for identifier in expert.get("supporting_evidence") or []
        if identifier in valid_ids
    })
    disputed_refs = sorted({
        identifier for item in disagreements
        for identifier in item.get("contradicting_findings") or []
        if identifier in valid_ids
    })
    if disagreements:
        final_reasoning = (
            f"{counts.get(final_verdict, 0)} experts supported "
            f"{_DISPLAY_VOTES.get(final_verdict, 'an inconclusive')} findings. "
            f"Disagreement was recorded: {disagreements[0]['explanation']}"
        )
    elif final_verdict == "INCONCLUSIVE":
        final_reasoning = (
            "The dossier does not contain sufficient consistent, measured evidence "
            "for a reliable Jury assessment."
        )
    else:
        final_reasoning = (
            f"{counts.get(final_verdict, 0)} independent forensic reviewers supported "
            f"the {_DISPLAY_VOTES[final_verdict].lower()} assessment using recorded evidence."
        )

    display_counts = {
        _DISPLAY_VOTES[vote]: counts[vote]
        for vote in _VOTES
    }
    return {
        "jury_id": "jury-" + hashlib.sha256(
            f"{evidence_id}|{'|'.join(sorted(valid_ids))}".encode("utf-8")
        ).hexdigest()[:12],
        "votes": display_counts,
        "vote_counts": counts,
        "overall_verdict": _DISPLAY_VOTES[final_verdict],
        "overall_confidence": overall_confidence,
        "jury_agreement": _agreement_label(agreement, len(active), disagreement_count),
        "primary_reason": final_reasoning,
        "supporting_evidence": final_refs,
        "disputed_evidence": disputed_refs,
        "disagreement_areas": disagreements,
        "recommendation": _recommendation("Jury", final_verdict, final_refs),
        "majority_verdict": majority,
        "weighted_consensus": {
            "verdict": weighted_vote,
            "display_verdict": _DISPLAY_VOTES[weighted_vote],
            "evidence_weight": {
                key: round(value, 4) for key, value in evidence_weight.items()
            },
        },
        "consensus_level": (
            "INCONCLUSIVE"
            if final_verdict == "INCONCLUSIVE"
            else _agreement_label(agreement, len(active), disagreement_count).upper()
        ),
        "agreement_percentage": agreement,
        "confidence_range": {
            "min": round(min(confidence_values), 4) if confidence_values else 0.0,
            "max": round(max(confidence_values), 4) if confidence_values else 0.0,
        },
        "final_reasoning": final_reasoning,
        "final_verdict": final_verdict,
        "risk_level": {
            "MANIPULATED": "HIGH RISK",
            "SUSPICIOUS": "MEDIUM RISK",
            "AUTHENTIC": "LOW RISK",
            "INCONCLUSIVE": "INCONCLUSIVE",
        }[final_verdict],
    }


def _atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary.replace(path)


def run_dossier_jury(
    evidence_id: str,
    analysis_dir: str | Path,
    *,
    dossier: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Evaluate a persisted dossier and append the reproducible Jury result."""
    analysis_dir = Path(analysis_dir)
    dossier = dossier if isinstance(dossier, dict) else _load_dossier(analysis_dir)
    rows = _finding_rows(dossier)
    valid_ids = {_row_id(row) for row in rows if _row_id(row)}
    experts = validate_finding_references(_build_experts(dossier, rows), valid_ids)
    consensus = _consensus(experts, valid_ids, evidence_id)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    jury_summary = {
        "evidence_id": evidence_id,
        "generated_at": generated_at,
        "expert_count": len(experts),
        "finding_count": len(valid_ids),
        "experts": [
            {
                "id": expert["id"],
                "name": expert["name"],
                "vote": _DISPLAY_VOTES[expert["vote"]],
                "risk": expert["risk"],
                "confidence": expert["confidence"],
                "summary": expert["summary"],
                "supporting_evidence": expert["supporting_evidence"],
            }
            for expert in experts
        ],
        "overall_verdict": consensus["overall_verdict"],
        "overall_confidence": consensus["overall_confidence"],
        "jury_agreement": consensus["jury_agreement"],
        "primary_reason": consensus["primary_reason"],
    }
    jury_report = {
        "report_type": "Forensic Jury Review",
        "evidence_id": evidence_id,
        "generated_at": generated_at,
        "executive_summary": consensus["primary_reason"],
        "expert_assessments": experts,
        "consensus": consensus,
        "contradictions": consensus["disagreement_areas"],
        "recommendation": consensus["recommendation"],
        "evidence_references": sorted(valid_ids),
    }
    ai_jury = {
        "jury_id": consensus["jury_id"],
        "evidence_id": evidence_id,
        "experts": experts,
        "consensus": consensus,
        "summary": jury_summary,
        "report": jury_report,
        "generated_at": generated_at,
    }
    jury_analysis = {
        "expert_count": len(experts),
        "evidence_count": len(valid_ids),
        "independent": True,
        "final_verdict": consensus["final_verdict"],
        "risk_level": consensus["risk_level"],
        "final_reasoning": consensus["final_reasoning"],
    }
    result = {
        "schema_version": "2.0",
        "evidence_id": evidence_id,
        "ai_jury": ai_jury,
        "jury_summary": jury_summary,
        "jury_consensus": consensus,
        "jury_report": jury_report,
        "jury_analysis": jury_analysis,
        "jury_experts": experts,
        "jury_votes": experts,
        "final_verdict": consensus["final_verdict"],
        "risk_level": consensus["risk_level"],
        "generated_at": generated_at,
    }

    analysis_dir.mkdir(parents=True, exist_ok=True)
    _atomic_write(analysis_dir / "jury_summary.json", jury_summary)
    _atomic_write(analysis_dir / "jury_consensus.json", consensus)
    _atomic_write(analysis_dir / "jury_report.json", jury_report)
    # Keep the existing artifact for consumers that already use it.
    _atomic_write(analysis_dir / "jury_analysis.json", result)

    persisted = dict(dossier)
    persisted.update({
        "ai_jury": ai_jury,
        "jury_summary": jury_summary,
        "jury_report": jury_report,
        "jury_analysis": jury_analysis,
        "jury_experts": experts,
        "jury_votes": experts,
        "jury_consensus": consensus,
        "final_verdict": consensus["final_verdict"],
        "risk_level": consensus["risk_level"],
    })
    _atomic_write(analysis_dir / "forensic_dossier.json", persisted)
    return result


__all__ = [
    "EXPERTS",
    "run_dossier_jury",
    "validate_finding_references",
]
