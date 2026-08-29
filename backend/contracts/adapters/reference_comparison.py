"""Canonical adapter for evidence-grounded reference comparisons."""

from __future__ import annotations

from typing import Any, Dict, List

from backend.contracts.adapters.investigator_language import investigator_title
from backend.contracts.forensic_finding import ForensicFinding, build_finding


def adapt_reference_comparison(
    data: Dict[str, Any], evidence_id: str, source: str = "reference_link.json"
) -> List[ForensicFinding]:
    reference = data.get("reference") or data
    reference_id = str(reference.get("reference_id") or "")
    comparison = reference.get("comparison") or {}
    status = str(reference.get("authenticity_status") or "unknown")
    findings: List[ForensicFinding] = []
    for field in comparison.get("field_comparisons") or []:
        if not isinstance(field, dict) or field.get("values_match") is not False:
            continue
        if field.get("correspondence") != "reliable_field_label_match":
            continue
        name = str(field.get("field") or "document field")
        observed = (
            f"Reliable field-label correspondence found differing values for {name}: "
            f"examined={field.get('examined_value')!r}, reference={field.get('reference_value')!r}."
        )
        findings.append(build_finding(
            evidence_id=evidence_id,
            title=investigator_title(
                finding_type="reference_field_difference",
                field=name,
                supplied_title=f"The examined {name.lower()} differs from the supplied reference document.",
            ),
            finding_type="reference_field_difference",
            verdict="A corresponding field differs and warrants source review",
            severity="MEDIUM",
            confidence=0.8,
            media_type="document",
            page=field.get("examined_page"),
            bbox=field.get("examined_bbox"),
            location=name,
            observed_evidence=[observed],
            short_explanation=observed,
            detailed_explanation=(
                f"The comparison uses matching field labels only. The reference authenticity "
                f"status is {status}; this difference alone does not establish alteration."
            ),
            original_comparison={
                "reference_evidence_id": reference_id,
                "reference_value": field.get("reference_value"),
                "examined_value": field.get("examined_value"),
                "correspondence": field.get("correspondence"),
            },
            potential_impact="The examined field may not agree with the linked supporting record.",
            recommended_review="Verify both values against the issuing authority or authenticated original.",
            provenance=[
                {"evidence_id": evidence_id, "source_artifact": source,
                 "method": "reference_ocr_field_comparison"},
                {"evidence_id": reference_id, "source_artifact": source,
                 "method": "supporting_reference_comparison"},
            ],
        ))
    return findings
