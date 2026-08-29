"""Human-readable forensic report presentation.

This module is deliberately presentation-only. It converts the existing report
bundle into neutral examiner language without changing analysis results.
"""

from __future__ import annotations
import json
import html
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional
from xml.sax.saxutils import escape


FORBIDDEN_TERMS = re.compile(
    r"\b(ai|artificial intelligence|neural networks?|deep learning|models?|"
    r"detectors?|inference|confidence(?: scores?)?|probability(?: scores?)?)\b",
    re.IGNORECASE,
)


def _text(value: Any, default: str = "Not recorded", limit: int = 500) -> str:
    value = default if value is None or value == "" else str(value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:limit]


def _professionalize(value: Any, default: str = "") -> str:
    """Remove implementation terminology from examiner-facing prose."""
    text = _text(value, default=default, limit=1000)
    replacements = (
        (r"\bour AI (?:detected|identified|found)\b", "The forensic examination identified"),
        (r"\bthe (?:AI |analysis )?model (?:predicts|indicates|found)\b", "The investigation indicates"),
        (r"\bdetector confidence\b", "strength of the available evidence"),
        (r"\bAI jury\b", "independent evidence review"),
        (r"\bensemble\b", "combined examination"),
        (r"\bELA\b", "compression consistency"),
        (r"\bOCR\b", "text recognition"),
    )
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    text = re.sub(r"\b\d+(?:\.\d+)?\s*%", "", text)
    text = FORBIDDEN_TERMS.sub("", text)
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    text = re.sub(r"\s{2,}", " ", text).strip(" -:;,")
    return text or default


def _date_time(value: Any) -> tuple[str, str]:
    raw = _text(value, default=datetime.now().isoformat(), limit=40)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return parsed.strftime("%d %B %Y"), parsed.strftime("%H:%M:%S %Z").strip()
    except ValueError:
        return raw[:10], raw[11:19] or "Not recorded"


def _risk_is_elevated(risk: Any, verdict: Any) -> bool:
    combined = f"{risk} {verdict}".upper()
    return any(word in combined for word in ("HIGH", "CRITICAL", "TAMPER", "FORG", "SUSPIC"))


def _split_evidence(value: Any) -> List[str]:
    if isinstance(value, (list, tuple)):
        values = value
    else:
        values = re.split(r"[;|]\s*", _text(value, default="", limit=1200))
    cleaned: List[str] = []
    translations = {
        "ela": "Compression inconsistency",
        "ocr": "Text recognition inconsistency",
        "noise": "Local pixel-pattern inconsistency",
        "copy move": "Duplicated image-content characteristics",
        "font": "Font or spacing inconsistency",
        "edge": "Edge blending inconsistency",
        "metadata": "File-history inconsistency",
        "signature": "Signature consistency mismatch",
    }
    for item in values:
        source = _text(item, default="", limit=180)
        if not source:
            continue
        lower = source.lower().replace("_", " ")
        label = next((v for k, v in translations.items() if k in lower), None)
        label = label or _professionalize(source)
        if label and label not in cleaned:
            cleaned.append(label)
    return cleaned[:5] or ["Local consistency anomaly"]


def _finding_language(manipulation: str, location: str) -> tuple[str, str, str]:
    lower = manipulation.lower()
    if any(k in lower for k in ("number", "numeric", "amount", "value", "text")):
        return (
            "The text or numeric content at this location appears to have been modified after the document was created.",
            "The affected content may no longer accurately represent the original document.",
            "Verify the value against the issuer's original record before relying on it.",
        )
    if "signature" in lower:
        return (
            "The signature appears inconsistent with naturally written or originally captured signature content.",
            "The authorization represented by the signature may not be reliable.",
            "Request the original signed document and compare it with an authenticated specimen.",
        )
    if any(k in lower for k in ("logo", "seal", "stamp")):
        return (
            "The identifying mark appears inconsistent with the surrounding document content.",
            "The issuing organization or document origin may be misrepresented.",
            "Confirm the document directly with the issuing organization.",
        )
    if any(k in lower for k in ("insert", "replace", "object", "image")):
        return (
            "Visual content at this location appears to have been inserted or replaced.",
            "The document may present content that was not present in the original.",
            "Compare this area with an archived or source copy of the document.",
        )
    return (
        f"The examination identified signs of localized alteration at {location}.",
        "The affected area may not reliably represent the original evidence.",
        "Verify this area against the original source document.",
    )


def _confidence_label(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "Not recorded"
    if number <= 1:
        number *= 100
    return f"{max(0, min(100, round(number)))}%"


def _risk_label(value: Any, confidence: Any = None) -> str:
    text = _text(value, default="", limit=30).upper()
    for label in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        if label in text:
            return label.title()
    try:
        number = float(confidence)
        if number <= 1:
            number *= 100
        if number >= 80:
            return "High"
        if number >= 50:
            return "Medium"
        return "Low"
    except (TypeError, ValueError):
        return "Not rated"


def _models_used(bundle: Dict[str, Any]) -> str:
    analysis = bundle.get("analysis") or {}
    technical = bundle.get("technical_summary") or {}
    names: List[str] = []
    labels = {
        "copy_move": "Duplicated-content analysis",
        "ela": "Compression consistency analysis",
        "wavelet": "Texture consistency analysis",
        "noise": "Pixel-pattern consistency analysis",
        "metadata": "Metadata examination",
        "ocr": "Text recognition comparison",
        "tampering": "Alteration analysis",
        "signature": "Signature examination",
        "document_consistency": "Document layout examination",
        "jpeg_block": "JPEG structure analysis",
    }
    for item in analysis.get("detector_outputs") or []:
        key = _text(item.get("detector_name"), default="", limit=50).lower()
        if not key or item.get("status") == "skipped":
            continue
        label = labels.get(key, key.replace("_", " ").title())
        if label not in names:
            names.append(label)
    for item in technical.get("module_scores") or []:
        key = _text(item.get("module"), default="", limit=50).lower().replace(" score", "")
        label = next((value for name, value in labels.items() if name.replace("_", " ") in key), None)
        label = label or key.title()
        if label and label not in names:
            names.append(label)
    return ", ".join(names[:8]) or "Forensic examination methods were not recorded."


def _append_unique(findings: List[Dict[str, Any]], finding: Dict[str, Any]) -> None:
    key = (
        finding["manipulation_type"].lower(),
        finding["location"].lower(),
        str(finding["page"]),
    )
    existing = {
        (f["manipulation_type"].lower(), f["location"].lower(), str(f["page"]))
        for f in findings
    }
    if key not in existing:
        finding["number"] = len(findings) + 1
        findings.append(finding)


def _normalize_findings(bundle: Dict[str, Any]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []

    for raw in bundle.get("canonical_findings") or []:
        chain = raw.get("evidence_chain") or []
        provenance = "; ".join(
            f"{item.get('method', 'method')} ({item.get('source_artifact') or item.get('source_file') or 'recorded source'})"
            for item in chain[:3] if isinstance(item, dict)
        )
        comparison = raw.get("original_comparison")
        comparison_text = ""
        if isinstance(comparison, dict):
            comparison_text = "; ".join(
                f"{key.replace('_', ' ').title()}: {_text(value, limit=100)}"
                for key, value in comparison.items() if value not in (None, "")
            )
        _append_unique(findings, {
            "finding_id": _text(raw.get("finding_id"), default="Not recorded", limit=64),
            "manipulation_type": _professionalize(raw.get("title") or raw.get("type"), default="Forensic Indicator").title(),
            "location": _text(raw.get("location"), default="Document-wide"),
            "page": _text(raw.get("page"), default="Document-wide"),
            "confidence": _confidence_label(raw.get("confidence")),
            "risk": _risk_label(raw.get("severity")),
            "observation": _professionalize(raw.get("detailed_explanation") or raw.get("short_explanation")),
            "evidence": _split_evidence(raw.get("observed_evidence")),
            "comparison": comparison_text or "No reliable source comparison was available.",
            "impact": _professionalize(raw.get("potential_impact"), default="Significance requires contextual review."),
            "recommendation": _professionalize(raw.get("recommended_review"), default="Review against an authenticated source."),
            "provenance": provenance or "Provenance details were not recorded.",
        })

    if findings:
        risk_order = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1, "Not rated": 0}
        findings.sort(key=lambda item: risk_order.get(item["risk"], 0), reverse=True)
        return findings[:10]

    for raw in bundle.get("region_findings") or []:
        where = _text(raw.get("where"), default="Area identified during examination")
        page_match = re.search(r"\bPage\s+(\d+)", where, re.IGNORECASE)
        page = page_match.group(1) if page_match else _text(raw.get("page"), default="1")
        location = re.sub(r"^\s*Page\s+\d+\s*[—-]\s*", "", where, flags=re.IGNORECASE)
        # Raw coordinates are intentionally excluded from the report.
        location = re.sub(r"\s*\(\s*\d+\s*,\s*\d+\s*\)\s*$", "", location).strip()
        manipulation = _professionalize(
            raw.get("what"), default="Localized Content Alteration"
        ).title()
        observation, impact, recommendation = _finding_language(manipulation, location)
        _append_unique(findings, {
            "manipulation_type": manipulation,
            "location": location or "Area identified during examination",
            "page": page,
            "confidence": _confidence_label(raw.get("confidence")),
            "risk": _risk_label(raw.get("risk") or raw.get("severity"), raw.get("confidence")),
            "observation": _professionalize(raw.get("why"), default=observation),
            "evidence": _split_evidence(raw.get("evidence") or raw.get("why")),
            "impact": _professionalize(raw.get("potential_impact"), default=impact),
            "recommendation": recommendation,
        })

    if not findings:
        for raw in (bundle.get("forensic_dossier") or {}).get("explanations") or []:
            manipulation = _professionalize(
                raw.get("title"), default="Localized Content Alteration"
            ).title()
            location = _text(raw.get("location"), default="Area identified during examination")
            observation, impact, recommendation = _finding_language(manipulation, location)
            _append_unique(findings, {
                "manipulation_type": manipulation,
                "location": location,
                "page": _text(raw.get("page"), default="1"),
                "confidence": _confidence_label(raw.get("confidence")),
                "risk": _risk_label(raw.get("risk") or raw.get("severity"), raw.get("confidence")),
                "observation": _professionalize(raw.get("reason"), default=observation),
                "evidence": _split_evidence(raw.get("reason")),
                "impact": _professionalize(raw.get("impact"), default=impact),
                "recommendation": _professionalize(
                    raw.get("recommendation"), default=recommendation
                ),
            })

    for raw in bundle.get("ocr_field_findings") or []:
        location = _text(raw.get("field_name"), default="Document text")
        manipulation = "Edited Text or Numeric Value"
        observation, impact, recommendation = _finding_language(manipulation, location)
        _append_unique(findings, {
            "manipulation_type": manipulation,
            "location": location,
            "page": _text(raw.get("page") or raw.get("page_number"), default="1"),
            "confidence": _confidence_label(raw.get("confidence")),
            "risk": _risk_label(raw.get("risk") or raw.get("severity"), raw.get("confidence")),
            "observation": observation,
            "evidence": ["Text recognition inconsistency", "Formatting inconsistency"],
            "impact": impact,
            "recommendation": recommendation,
        })

    signature = bundle.get("signature_analysis") or {}
    signature_verdict = _text(signature.get("verdict"), default="").lower()
    if signature and any(k in signature_verdict for k in ("mismatch", "forg", "susp", "invalid")):
        observation, impact, recommendation = _finding_language("Inserted Signature", "Signature area")
        _append_unique(findings, {
            "manipulation_type": "Inserted or Inconsistent Signature",
            "location": _text(signature.get("location"), default="Signature area"),
            "page": _text(signature.get("page"), default="1"),
            "confidence": _confidence_label(signature.get("confidence")),
            "risk": _risk_label(signature.get("risk") or signature.get("severity"), signature.get("confidence")),
            "observation": _professionalize(signature.get("reason"), default=observation),
            "evidence": ["Signature consistency mismatch", "Edge blending inconsistency"],
            "impact": impact,
            "recommendation": recommendation,
        })

    logo = bundle.get("logo_analysis") or {}
    logo_verdict = _text(logo.get("verdict") or logo.get("status"), default="").lower()
    if logo and any(k in logo_verdict for k in ("mismatch", "forg", "susp", "invalid")):
        observation, impact, recommendation = _finding_language("Edited Logo", "Document header")
        _append_unique(findings, {
            "manipulation_type": "Replaced or Inconsistent Logo",
            "location": _text(logo.get("location"), default="Document header"),
            "page": _text(logo.get("page"), default="1"),
            "confidence": _confidence_label(logo.get("confidence")),
            "risk": _risk_label(logo.get("risk") or logo.get("severity"), logo.get("confidence")),
            "observation": observation,
            "evidence": ["Compression inconsistency", "Color-profile inconsistency"],
            "impact": impact,
            "recommendation": recommendation,
        })

    risk_order = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1, "Not rated": 0}
    findings.sort(key=lambda item: risk_order.get(item["risk"], 0), reverse=True)
    return findings[:10]


def _recommendations(findings: List[Dict[str, Any]], elevated: bool) -> List[str]:
    recs: List[str] = []
    for finding in findings:
        rec = finding["recommendation"]
        if rec not in recs:
            recs.append(rec)
    defaults = (
        [
            "Obtain and preserve the original source document.",
            "Contact the issuing authority to confirm the recorded information.",
            "Compare the submitted evidence with an authenticated or archived copy.",
            "Do not rely on the disputed content until independent verification is complete.",
            "Maintain the documented chain of custody for all evidence.",
        ]
        if elevated
        else
        [
            "Retain the original evidence and its integrity records.",
            "Maintain the documented chain of custody.",
            "Seek source verification if the document will support a material decision.",
        ]
    )
    for rec in defaults:
        if rec not in recs:
            recs.append(rec)
    return recs[:5]


def build_professional_report(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Create the single examiner-facing view consumed by all human formats."""
    meta = bundle.get("meta") or {}
    evidence = bundle.get("evidence_summary") or {}
    executive = bundle.get("executive_summary") or {}
    case = bundle.get("case_context") or {}
    findings = _normalize_findings(bundle)
    elevated = _risk_is_elevated(executive.get("risk_level"), executive.get("verdict"))
    date, time = _date_time(meta.get("generated_at"))
    verdict = _professionalize(executive.get("verdict"), default="Examination Complete")
    risk = _text(executive.get("risk_level"), default="Not classified").title()

    if findings:
        summary = (
            "The submitted evidence was examined for signs of digital manipulation using a "
            "structured forensic investigation workflow. The examination included file-history "
            "review, document integrity assessment, text consistency checking, signature review "
            "where applicable, and correlation of independent forensic indicators. "
            f"The investigation identified {len(findings)} suspicious modification"
            f"{'s' if len(findings) != 1 else ''} that may affect the reliability of the submitted "
            "evidence. The strongest concerns are described in the numbered findings below. "
            "Verification against the original source is recommended before the evidence is relied upon."
        )
        strongest = ", ".join(f["manipulation_type"].lower() for f in findings[:2])
        conclusion = (
            "The forensic examination identified multiple independent indicators consistent with "
            f"digital modification. The strongest evidence relates to {strongest}. "
            "Based on the available forensic evidence, the submitted material should not be treated "
            "as authentic until it has been verified against its original source."
        )
    else:
        summary = (
            "The submitted evidence was examined for signs of digital manipulation using a "
            "structured forensic investigation workflow. The examination included file-history "
            "review, document integrity assessment, text consistency checking, signature review "
            "where applicable, and evidence correlation. The forensic examination did not identify "
            "confirmed evidence of digital manipulation. The analysed material appears internally "
            "consistent based on the available evidence. No suspicious modifications requiring "
            "further investigation were identified."
        )
        conclusion = (
            "The forensic examination did not identify confirmed evidence of digital manipulation. "
            "The submitted material appears internally consistent within the scope of the available "
            "evidence. This conclusion does not replace source verification where authenticity has "
            "legal, financial, or regulatory significance."
        )

    custody_events = evidence.get("custody_events", 0) or 0
    custody_status = "Verified" if evidence.get("chain_verified") else "Not independently verified"
    jury = bundle.get("jury") or {}
    fusion = jury.get("fusion") if isinstance(jury, dict) else {}
    consensus = _professionalize(
        (fusion or {}).get("majority_opinion")
        or (fusion or {}).get("reasoning")
        or (fusion or {}).get("verdict")
        or executive.get("verdict"),
        default="The independent evidence review was consistent with the overall investigation conclusion.",
    )
    consensus = (
        f"The independent evidence review reached a conclusion consistent with the overall finding: "
        f"{consensus.rstrip('.')}."
    )

    metadata = bundle.get("metadata_anomalies") or {}
    metadata_flags = metadata.get("warnings") or metadata.get("flags") or metadata.get("anomalies") or []
    metadata_summary = (
        f"{len(metadata_flags)} file-history irregularit{'y was' if len(metadata_flags) == 1 else 'ies were'} noted."
        if metadata_flags
        else "No material file-history irregularities were recorded."
    )
    finding_traceability = " | ".join(
        "{}: {}".format(
            finding.get("finding_id") or f"Finding {finding.get('number', index + 1)}",
            finding.get("provenance", "Recorded analysis source"),
        )
        for index, finding in enumerate(findings[:4])
    ) or "No supported finding records were produced."

    return {
        "title": "DIGITAL FORENSIC INVESTIGATION SUMMARY",
        "case_id": _text(case.get("case_id"), default="Not assigned"),
        "investigation_id": _text(
            case.get("case_id") or meta.get("evidence_id") or evidence.get("evidence_id")
        ),
        "evidence_id": _text(meta.get("evidence_id") or evidence.get("evidence_id")),
        "evidence_name": _text(evidence.get("original_filename"), default="Not recorded"),
        "investigation_date": date,
        "investigation_time": time,
        "examiner": "Digital Forensic Examination Service",
        "document_type": _text(evidence.get("media_type"), default="Not recorded"),
        "hash": _text(evidence.get("sha256"), default="Not recorded", limit=128),
        "status": "Complete",
        "verdict": verdict,
        "risk_level": risk,
        "evidence_count": len(findings),
        "jury_decision": consensus,
        "executive_summary": summary,
        "findings": findings,
        "conclusion": conclusion,
        "recommendations": _recommendations(findings, elevated),
        "appendix": {
            "models_used": _models_used(bundle),
            "metadata_summary": metadata_summary,
            "evidence_count": len(findings),
            "hash": _text(evidence.get("sha256"), default="Not recorded", limit=128),
            "timestamp": _text(meta.get("generated_at"), default="Not recorded", limit=60),
            "chain_of_custody": f"{custody_events} recorded event(s); integrity status: {custody_status}.",
            "finding_traceability": finding_traceability,
            "consensus_summary": consensus,
        },
    }


def _pdf_styles():
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

    styles = getSampleStyleSheet()
    ink = colors.HexColor("#202020")
    muted = colors.HexColor("#555555")
    styles.add(ParagraphStyle(
        "ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=17, leading=21, textColor=ink, alignment=TA_CENTER, spaceAfter=14,
    ))
    styles.add(ParagraphStyle(
        "ReportHeading", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=12, leading=15, textColor=ink, spaceBefore=8, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        "FindingHeading", parent=styles["Heading3"], fontName="Helvetica-Bold",
        fontSize=10.5, leading=13, textColor=ink, spaceBefore=5, spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        "ReportBody", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=9.3, leading=13, textColor=ink, alignment=TA_JUSTIFY, spaceAfter=5,
    ))
    styles.add(ParagraphStyle(
        "SmallBody", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=8.2, leading=10.5, textColor=muted, spaceAfter=3,
    ))
    return styles


def export_professional_pdf(bundle: Dict[str, Any], output_path: Path) -> str:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )

    report = build_professional_report(bundle)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    styles = _pdf_styles()
    story: List[Any] = []

    def para(value: Any, style: str = "ReportBody"):
        return Paragraph(escape(_text(value, limit=3000)), styles[style])

    def info_table(rows: Iterable[tuple[str, Any]]) -> Table:
        table = Table(
            [[para(label, "SmallBody"), para(value, "SmallBody")] for label, value in rows],
            colWidths=[43 * mm, 125 * mm],
        )
        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#b8b8b8")),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f2f2f2")),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return table

    # Page 1 — summary.
    story.append(para(report["title"], "ReportTitle"))
    story.append(info_table([
        ("Investigation ID", report["investigation_id"]),
        ("Document", report["evidence_name"]),
        ("Investigation Timestamp", f"{report['investigation_date']} {report['investigation_time']}"),
        ("Overall Verdict", report["verdict"]),
        ("Risk Level", report["risk_level"]),
        ("Evidence Count", report["evidence_count"]),
        ("AI Jury Decision", report["jury_decision"]),
    ]))
    story.append(Spacer(1, 6 * mm))
    story.append(para("Executive Summary", "ReportHeading"))
    story.append(para(report["executive_summary"]))
    story.append(PageBreak())

    # Page 2 — findings.
    story.append(para("INVESTIGATION FINDINGS", "ReportTitle"))
    if report["findings"]:
        compact = len(report["findings"]) > 4
        very_compact = len(report["findings"]) > 16
        finding_cells = []
        for finding in report["findings"]:
            if compact:
                body = (
                    f"<b>ID:</b> {escape(_text(finding.get('finding_id'), limit=28))}<br/>"
                    f"<b>Type:</b> {escape(_text(finding['manipulation_type'], limit=70))}<br/>"
                    f"<b>Location:</b> {escape(_text(finding['location'], limit=65))}; "
                    f"<b>Page:</b> {escape(_text(finding['page'], limit=10))}<br/>"
                    f"<b>Confidence:</b> {escape(_text(finding['confidence'], limit=20))}; "
                    f"<b>Risk:</b> {escape(_text(finding['risk'], limit=20))}<br/>"
                    f"<b>Explanation:</b> {escape(_text(finding['observation'], limit=75 if very_compact else 110))}<br/>"
                    f"<b>Evidence:</b> {escape(_text('; '.join(finding.get('evidence') or []), limit=70))}<br/>"
                    f"<b>Recommendation:</b> {escape(_text(finding['recommendation'], limit=70 if very_compact else 95))}"
                )
                cell = Table(
                    [[Paragraph(
                        f"<b>Finding {finding['number']}</b><br/>{body}",
                        type(styles["SmallBody"])(
                            "CondensedFinding",
                            parent=styles["SmallBody"],
                            fontSize=4.8 if very_compact else 6.1,
                            leading=5.5 if very_compact else 7.2,
                            spaceAfter=0,
                        ),
                    )]],
                    colWidths=[80 * mm],
                )
            else:
                cell = Table(
                    [
                        [para(
                            f"Finding {finding['number']} — {finding['manipulation_type']}",
                            "FindingHeading",
                        )],
                        [Table(
                            [[para(label, "SmallBody"), para(value, "SmallBody")] for label, value in [
                                ("Location", finding["location"]),
                                ("Page", finding["page"]),
                                ("Confidence", finding["confidence"]),
                                ("Risk", finding["risk"]),
                                ("Finding ID", finding.get("finding_id", "Not recorded")),
                                ("Observed Evidence", "; ".join(finding.get("evidence") or [])),
                                ("Comparison", finding.get("comparison", "Not available")),
                                ("Explanation", finding["observation"]),
                                ("Recommendation", finding["recommendation"]),
                                ("Provenance", finding.get("provenance", "Not recorded")),
                            ]],
                            colWidths=[22 * mm, 56 * mm],
                            style=TableStyle([
                                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f2f2f2")),
                                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#c6c6c6")),
                                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                ("TOPPADDING", (0, 0), (-1, -1), 2),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                            ]),
                        )],
                    ],
                    colWidths=[80 * mm],
                )
            cell.setStyle(TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#9a9a9a")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            finding_cells.append(cell)

        midpoint = (len(finding_cells) + 1) // 2
        left = finding_cells[:midpoint]
        right = finding_cells[midpoint:]
        two_column_rows = []
        for index in range(midpoint):
            two_column_rows.append([
                left[index],
                right[index] if index < len(right) else "",
            ])
        findings_table = Table(two_column_rows, colWidths=[84 * mm, 84 * mm])
        findings_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(findings_table)
    else:
        story.append(para(
            "The forensic examination did not identify any confirmed evidence of digital manipulation. "
            "The analysed document appears internally consistent based on the available evidence. "
            "No suspicious modifications requiring further investigation were identified."
        ))
    story.append(PageBreak())

    # Page 3 — technical appendix and conclusion.
    story.append(para("TECHNICAL APPENDIX", "ReportTitle"))
    story.append(para("Investigation Conclusion", "ReportHeading"))
    story.append(para(report["conclusion"]))
    story.append(para("Recommendations", "ReportHeading"))
    for recommendation in report["recommendations"]:
        story.append(para(f"• {recommendation}"))
    story.append(Spacer(1, 3 * mm))
    appendix = report["appendix"]
    story.append(info_table([
        ("Models / Methods Used", appendix["models_used"]),
        ("Metadata Summary", appendix["metadata_summary"]),
        ("Evidence Count", appendix["evidence_count"]),
        ("Evidence Hash", appendix["hash"]),
        ("Timestamp", appendix["timestamp"]),
        ("Chain of Custody", appendix["chain_of_custody"]),
        ("Finding Traceability", appendix["finding_traceability"]),
        ("Consensus Summary", appendix["consensus_summary"]),
    ]))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#b8b8b8"))
        canvas.line(20 * mm, 15 * mm, A4[0] - 20 * mm, 15 * mm)
        canvas.setFillColor(colors.HexColor("#555555"))
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(20 * mm, 10 * mm, f"Investigation ID: {report['investigation_id']} — Confidential")
        canvas.drawRightString(A4[0] - 20 * mm, 10 * mm, f"Page {doc.page} of 3")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(output_path), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=20 * mm,
        title=f"Digital Forensic Investigation Report — {report['evidence_id']}",
        author="Digital Forensic Examination Service",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return str(output_path)


def export_professional_docx(bundle: Dict[str, Any], output_path: Path) -> str:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Inches, Pt

    report = build_professional_report(bundle)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.65)
    section.bottom_margin = Inches(0.65)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)
    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(9.5)

    def heading(text: str, level: int = 1):
        paragraph = doc.add_heading(text, level)
        paragraph.style.font.name = "Arial"
        return paragraph

    title = doc.add_heading(report["title"], 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    table = doc.add_table(rows=0, cols=2)
    table.style = "Table Grid"
    for label, value in [
        ("Investigation ID", report["investigation_id"]),
        ("Document", report["evidence_name"]),
        ("Investigation Timestamp", f"{report['investigation_date']} {report['investigation_time']}"),
        ("Overall Verdict", report["verdict"]), ("Risk Level", report["risk_level"]),
        ("Evidence Count", report["evidence_count"]),
        ("AI Jury Decision", report["jury_decision"]),
    ]:
        cells = table.add_row().cells
        cells[0].text, cells[1].text = label, str(value)
    heading("Executive Summary")
    doc.add_paragraph(report["executive_summary"])
    doc.add_page_break()

    title = doc.add_heading("INVESTIGATION FINDINGS", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if report["findings"]:
        finding_grid = doc.add_table(rows=0, cols=2)
        finding_grid.style = "Table Grid"
        for offset in range(0, len(report["findings"]), 2):
            cells = finding_grid.add_row().cells
            for column, finding in enumerate(report["findings"][offset:offset + 2]):
                paragraph = cells[column].paragraphs[0]
                values = [
                    (f"Finding {finding['number']} — {finding['manipulation_type']}", True),
                    (f"\nID: {finding.get('finding_id', 'Not recorded')}", False),
                    (f"\nPage / location: {finding['page']} / {finding['location']}", False),
                    (f"\nConfidence / risk: {finding['confidence']} / {finding['risk']}", False),
                    (f"\nEvidence: {'; '.join(finding.get('evidence') or [])}", False),
                    (f"\nComparison: {finding.get('comparison', 'Not available')}", False),
                    (f"\nExplanation: {finding['observation']}", False),
                    (f"\nRecommendation: {finding['recommendation']}", False),
                    (f"\nProvenance: {finding.get('provenance', 'Not recorded')}", False),
                ]
                for value, bold in values:
                    run = paragraph.add_run(value)
                    run.bold = bold
                    run.font.size = Pt(7.5)
    else:
        doc.add_paragraph(
            "The forensic examination did not identify any confirmed evidence of digital manipulation. "
            "The analysed document appears internally consistent based on the available evidence. "
            "No suspicious modifications requiring further investigation were identified."
        )
    doc.add_page_break()

    title = doc.add_heading("TECHNICAL APPENDIX", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    heading("Investigation Conclusion")
    doc.add_paragraph(report["conclusion"])
    heading("Recommendations")
    for item in report["recommendations"]:
        doc.add_paragraph(item, style="List Bullet")
    appendix = report["appendix"]
    appendix_table = doc.add_table(rows=0, cols=2)
    appendix_table.style = "Table Grid"
    for label, value in [
        ("Models / Methods Used", appendix["models_used"]),
        ("Metadata Summary", appendix["metadata_summary"]), ("Evidence Count", appendix["evidence_count"]),
        ("Evidence Hash", appendix["hash"]), ("Timestamp", appendix["timestamp"]),
        ("Chain of Custody", appendix["chain_of_custody"]),
        ("Finding Traceability", appendix["finding_traceability"]),
        ("Consensus Summary", appendix["consensus_summary"]),
    ]:
        cells = appendix_table.add_row().cells
        cells[0].text, cells[1].text = label, str(value)

    for section in doc.sections:
        footer = section.footer.paragraphs[0]
        footer.text = f"Investigation ID: {report['investigation_id']} — Confidential · Page "
        run = footer.add_run()
        field_begin = OxmlElement("w:fldChar")
        field_begin.set(qn("w:fldCharType"), "begin")
        instruction = OxmlElement("w:instrText")
        instruction.set(qn("xml:space"), "preserve")
        instruction.text = "PAGE"
        field_end = OxmlElement("w:fldChar")
        field_end.set(qn("w:fldCharType"), "end")
        run._r.extend([field_begin, instruction, field_end])
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.save(str(output_path))
    return str(output_path)


def export_professional_html(bundle: Dict[str, Any], output_path: Path) -> str:
    report = build_professional_report(bundle)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    esc = lambda value: html.escape(_text(value, limit=5000))

    def rows(items):
        return "".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in items)

    if report["findings"]:
        findings_html = "".join(
            f"""<article class="finding">
              <h3>Finding {f['number']} — {esc(f['manipulation_type'])}</h3>
              <table>{rows([
                  ('Finding ID', f.get('finding_id', 'Not recorded')),
                  ('Location', f['location']), ('Page', f['page']),
                  ('Confidence', f['confidence']), ('Risk', f['risk']),
                  ('Observed Evidence', '; '.join(f.get('evidence') or [])),
                  ('Comparison', f.get('comparison', 'Not available')),
                  ('Explanation', f['observation']), ('Recommendation', f['recommendation']),
                  ('Provenance', f.get('provenance', 'Not recorded')),
              ])}</table>
            </article>"""
            for f in report["findings"]
        )
    else:
        findings_html = (
            "<p>The forensic examination did not identify any confirmed evidence of digital manipulation. "
            "The analysed document appears internally consistent based on the available evidence. "
            "No suspicious modifications requiring further investigation were identified.</p>"
        )

    appendix = report["appendix"]
    content = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Digital Forensic Investigation Report — {esc(report['evidence_id'])}</title>
<style>
@page {{ size: A4; margin: 18mm 20mm 20mm; }}
* {{ box-sizing: border-box; }} body {{ margin: 0; color: #202020; font: 10pt/1.45 Arial, sans-serif; }}
.page {{ min-height: 257mm; page-break-after: always; padding: 18mm 20mm 20mm; }}
.page:last-child {{ page-break-after: auto; }} h1 {{ text-align: center; font-size: 17pt; letter-spacing: .02em; margin: 0 0 14pt; }}
h2 {{ font-size: 13pt; margin: 16pt 0 7pt; border-bottom: 1px solid #999; padding-bottom: 4pt; }}
h3 {{ font-size: 10.5pt; margin: 8pt 0 4pt; }} p {{ text-align: justify; }}
table {{ border-collapse: collapse; width: 100%; table-layout: fixed; }} th, td {{ border: 1px solid #bbb; padding: 5pt 7pt; vertical-align: top; }}
th {{ width: 26%; background: #f2f2f2; text-align: left; }} .finding {{ break-inside: avoid; margin-bottom: 9pt; }}
.findings-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 7pt; }} .findings-grid .finding {{ margin: 0; font-size: 7.5pt; }}
.findings-grid th, .findings-grid td {{ padding: 2.5pt 4pt; }} .findings-grid h3 {{ margin-top: 0; font-size: 8.5pt; }}
footer {{ color: #555; border-top: 1px solid #aaa; margin-top: 14pt; padding-top: 5pt; font-size: 8pt; text-align: center; }}
ul {{ padding-left: 20pt; }}
@media screen {{ body {{ background: #e8e8e8; }} .page {{ width: 210mm; margin: 10mm auto; background: white; box-shadow: 0 1mm 4mm #aaa; }} }}
</style></head><body>
<section class="page"><h1>{esc(report['title'])}</h1>
<table>{rows([
    ('Investigation ID', report['investigation_id']), ('Document', report['evidence_name']),
    ('Investigation Timestamp', report['investigation_date'] + ' ' + report['investigation_time']),
    ('Overall Verdict', report['verdict']), ('Risk Level', report['risk_level']),
    ('Evidence Count', report['evidence_count']), ('AI Jury Decision', report['jury_decision']),
])}</table><h2>Executive Summary</h2><p>{esc(report['executive_summary'])}</p>
<footer>Investigation ID: {esc(report['investigation_id'])} — Confidential — Page 1 of 3</footer></section>
<section class="page"><h1>INVESTIGATION FINDINGS</h1><div class="findings-grid">{findings_html}</div>
<footer>Investigation ID: {esc(report['investigation_id'])} — Confidential — Page 2 of 3</footer></section>
<section class="page"><h1>TECHNICAL APPENDIX</h1><h2>Investigation Conclusion</h2><p>{esc(report['conclusion'])}</p>
<h2>Recommendations</h2><ul>{''.join(f'<li>{esc(r)}</li>' for r in report['recommendations'])}</ul>
<table>{rows([
    ('Models / Methods Used', appendix['models_used']),
    ('Metadata Summary', appendix['metadata_summary']), ('Evidence Count', appendix['evidence_count']),
    ('Evidence Hash', appendix['hash']), ('Timestamp', appendix['timestamp']),
    ('Chain of Custody', appendix['chain_of_custody']),
    ('Finding Traceability', appendix['finding_traceability']),
    ('Consensus Summary', appendix['consensus_summary']),
])}</table><footer>Investigation ID: {esc(report['investigation_id'])} — Confidential — Page 3 of 3</footer></section>
</body></html>"""
    output_path.write_text(content, encoding="utf-8")
    return str(output_path)


# ---------------------------------------------------------------------------
# Court-ready report presentation
# ---------------------------------------------------------------------------
# The original helpers above remain available for older callers. These
# definitions are the current report contract used by the exporters below.

import os
import tempfile
from threading import Lock

_REPORT_DOSSIER_LOCK = Lock()
_CR_VOTE_LABELS = {
    "AUTHENTIC": "Clean",
    "CLEAN": "Clean",
    "SUSPICIOUS": "Suspicious",
    "MANIPULATED": "Manipulated",
    "INCONCLUSIVE": "Inconclusive",
}


def _cr_text(value: Any, default: str = "", limit: int = 1200) -> str:
    if value is None:
        return default
    if isinstance(value, (list, tuple)):
        value = "; ".join(str(item) for item in value if item not in (None, ""))
    elif isinstance(value, dict):
        value = "; ".join(f"{key}: {item}" for key, item in value.items())
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text[:limit] if text else default


def _cr_clean(value: Any, default: str = "", limit: int = 1200) -> str:
    text = _cr_text(value, default=default, limit=limit)
    replacements = (
        (r"\bAI[- ]assisted\b", "automated"),
        (r"\bAI jury\b", "independent forensic expert review"),
        (r"\bneural networks?\b", "automated image analysis"),
        (r"\btransformers?\b", "automated text analysis"),
        (r"\bmachine learning\b", "automated analysis"),
        (r"\bprediction\b", "assessment"),
        (r"\bconfidence score\b", "evidence strength"),
        (r"\bdetector confidence\b", "evidence strength"),
        (r"\bdetectors?\b", "forensic methods"),
        (r"\bmodel(?:s)?\b", "analysis method"),
        (r"\bensemble\b", "combined examination"),
    )
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return re.sub(r"\s+([,.;:])", r"\1", text).strip()


def _cr_severity(value: Any) -> str:
    text = _cr_text(value, default="").upper()
    for label in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        if label in text:
            return label.title()
    return "Not recorded"


def _cr_strength(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = -1
    if number < 0:
        return "Not recorded"
    if number <= 1:
        number *= 100
    if number >= 80:
        return "Strong"
    if number >= 50:
        return "Moderate"
    return "Limited"


def _cr_bbox(value: Any) -> Optional[List[float]]:
    if isinstance(value, dict):
        try:
            x = value.get("x", value.get("left", value.get("x1")))
            y = value.get("y", value.get("top", value.get("y1")))
            width = value.get("width", value.get("w"))
            height = value.get("height", value.get("h"))
            if width is None and value.get("x2") is not None and x is not None:
                width = float(value["x2"]) - float(x)
            if height is None and value.get("y2") is not None and y is not None:
                height = float(value["y2"]) - float(y)
            if None not in (x, y, width, height):
                return [float(x), float(y), float(width), float(height)]
        except (TypeError, ValueError):
            return None
    if isinstance(value, (list, tuple)) and len(value) >= 4:
        try:
            return [float(value[index]) for index in range(4)]
        except (TypeError, ValueError):
            return None
    return None


def _cr_location(raw: Mapping[str, Any], page: str, bbox: Optional[List[float]]) -> str:
    location = raw.get("location") or raw.get("where") or raw.get("region")
    if isinstance(location, dict):
        location = location.get("description") or location.get("label")
    location = _cr_clean(location, default="")
    if location:
        return f"Page {page} · {location}" if page != "Not recorded" and "page" not in location.lower() else location
    if bbox:
        coords = ", ".join(str(round(item, 1)) for item in bbox)
        return f"Page {page} · Coordinates [{coords}]"
    return f"Page {page}" if page != "Not recorded" else "Document-wide"


def _cr_evidence_values(raw: Mapping[str, Any]) -> List[str]:
    values: List[Any] = []
    for key in ("observed_evidence", "evidence", "supporting_methods", "detectors", "signals"):
        value = raw.get(key)
        if isinstance(value, (list, tuple)):
            values.extend(value)
        elif value not in (None, ""):
            values.append(value)
    output: List[str] = []
    for value in values:
        text = _cr_clean(value, limit=260)
        if text and text not in output:
            output.append(text)
    return output[:6]


def _cr_finding_rows(bundle: Dict[str, Any]) -> List[Dict[str, Any]]:
    dossier = bundle.get("forensic_dossier") or {}
    sources: List[tuple[str, Any]] = [
        ("canonical findings", bundle.get("canonical_findings")),
        ("human findings", dossier.get("human_findings") if isinstance(dossier, dict) else None),
        ("localized regions", dossier.get("localized_regions") if isinstance(dossier, dict) else None),
        ("localization", (bundle.get("localization") or {}).get("regions")),
        ("document tampering", (dossier.get("document_tampering") or {}).get("findings") if isinstance(dossier, dict) else None),
        ("signature analysis", (dossier.get("signature_analysis") or {}).get("findings") if isinstance(dossier, dict) else None),
        ("signature verification", (dossier.get("signature_verification") or {}).get("findings") if isinstance(dossier, dict) else None),
        ("report regions", bundle.get("region_findings")),
    ]
    findings: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for source, collection in sources:
        if not isinstance(collection, list):
            continue
        for raw in collection:
            if not isinstance(raw, Mapping):
                continue
            raw_id = raw.get("finding_id") or raw.get("id") or raw.get("region_id")
            key = str(raw_id) if raw_id else (
                f"{source}:{raw.get('type') or raw.get('category')}:"
                f"{raw.get('page') or raw.get('page_number')}:{raw.get('location') or raw.get('where')}"
            )
            if key in seen:
                continue
            seen.add(key)
            page = _cr_text(raw.get("page") or raw.get("page_number"), default="Not recorded", limit=30)
            title = _cr_clean(
                raw.get("title") or raw.get("label") or raw.get("edit_type")
                or raw.get("type") or raw.get("category"),
                default="Forensic finding",
                limit=180,
            )
            bbox = _cr_bbox(raw.get("bbox") or raw.get("bounding_box") or raw.get("coordinates"))
            reason = _cr_clean(
                raw.get("technical_reason") or raw.get("technical_explanation")
                or raw.get("reason") or raw.get("why") or raw.get("explanation")
                or raw.get("detailed_explanation") or raw.get("description"),
                default=f"The examination recorded a {title.lower()} finding.",
            )
            impact = _cr_clean(
                raw.get("potential_impact") or raw.get("impact"),
                default="Significance requires verification against the original source.",
            )
            recommendation = _cr_clean(
                raw.get("recommended_action") or raw.get("recommendation")
                or raw.get("recommended_review"),
                default="Verify this finding against an authenticated source.",
            )
            confidence = raw.get("confidence")
            if confidence is None:
                confidence = raw.get("confidence_pct") or raw.get("score")
            findings.append({
                "finding_id": str(raw_id) if raw_id else f"F-{len(findings) + 1:03d}",
                "title": title,
                "location": _cr_location(raw, page, bbox),
                "page": page,
                "severity": _cr_severity(raw.get("severity") or raw.get("risk") or raw.get("risk_level")),
                "evidence": _cr_evidence_values(raw),
                "explanation": _cr_clean(
                    raw.get("human_summary") or raw.get("plain_english_explanation")
                    or raw.get("description") or raw.get("observation") or reason,
                    default=reason,
                ),
                "technical_reason": reason,
                "impact": impact,
                "recommendation": recommendation,
                "evidence_strength": _cr_strength(confidence),
                "confidence": confidence,
                "bbox": bbox,
                "polygon": raw.get("polygon") or [],
                "mask": raw.get("mask") or raw.get("mask_path"),
                "source": source,
                "reference_comparison": _cr_clean(
                    raw.get("reference_comparison") or raw.get("comparison"),
                    default="",
                ),
            })
    return findings


def _cr_localization_images(bundle: Dict[str, Any]) -> List[Dict[str, str]]:
    candidates: List[tuple[str, Any]] = []
    artifacts = bundle.get("artifacts") or {}
    localization = bundle.get("localization") or {}
    for label, keys in (
        ("Original Evidence", ("evidence_original",)),
        ("Localized Evidence", ("combined_overlay", "localization_overlay", "localization_annotated")),
        ("Heatmap", ("forensic_heatmap", "localization_heatmap", "heatmap")),
        ("Bounding Box Evidence", ("localization_regions", "bounding_boxes", "forgery_mask")),
    ):
        for key in keys:
            candidates.append((label, artifacts.get(key)))
            candidates.append((label, (localization.get("files") or {}).get(key)))
            candidates.append((label, (localization.get("views") or {}).get(key)))
    output: List[Dict[str, str]] = []
    seen: set[str] = set()
    for label, value in candidates:
        if not value:
            continue
        path = Path(str(value).replace("file://", ""))
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            if str(path.resolve()) not in seen:
                seen.add(str(path.resolve()))
                output.append({"label": label, "path": str(path)})
    return output


def _cr_jury(bundle: Dict[str, Any]) -> Dict[str, Any]:
    dossier = bundle.get("forensic_dossier") or {}
    ai_jury = dossier.get("ai_jury") if isinstance(dossier, dict) else None
    source = ai_jury if isinstance(ai_jury, dict) else bundle.get("dossier_jury") or {}
    consensus = source.get("consensus") if isinstance(source, dict) else {}
    if not isinstance(consensus, dict) or not consensus:
        consensus = (
            dossier.get("jury_consensus")
            if isinstance(dossier, dict) and isinstance(dossier.get("jury_consensus"), dict)
            else {}
        )
    experts = source.get("experts") if isinstance(source, dict) else []
    if not isinstance(experts, list):
        experts = []
    if not experts and isinstance(dossier, dict):
        experts = dossier.get("jury_experts") or []
    if not experts and isinstance(bundle.get("jury"), dict):
        agents = bundle["jury"].get("agents") or {}
        experts = list(agents.values()) if isinstance(agents, dict) else []
    normalized: List[Dict[str, Any]] = []
    for expert in experts:
        if not isinstance(expert, Mapping):
            continue
        vote = str(expert.get("vote") or expert.get("verdict") or "INCONCLUSIVE").upper()
        normalized.append({
            "id": expert.get("id") or expert.get("expert_id") or f"expert_{len(normalized) + 1:02d}",
            "name": _cr_clean(expert.get("name") or expert.get("expert_name"), default="Forensic reviewer"),
            "vote": _CR_VOTE_LABELS.get(vote, "Inconclusive"),
            "evidence": list(expert.get("supporting_evidence") or expert.get("supporting_findings") or []),
            "summary": _cr_clean(expert.get("summary") or expert.get("reasoning_text") or expert.get("reasoning"), default="Reasoning not recorded."),
        })
    verdict = _cr_clean(
        consensus.get("overall_verdict") or consensus.get("final_verdict")
        or dossier.get("final_verdict") if isinstance(dossier, dict) else "",
        default="Not recorded",
    )
    if verdict.upper() in _CR_VOTE_LABELS:
        verdict = _CR_VOTE_LABELS[verdict.upper()]
    manipulation_count = sum(1 for expert in normalized if expert["vote"] == "Manipulated")
    return {
        "experts": normalized,
        "verdict": verdict,
        "risk_level": _cr_clean(consensus.get("risk_level") or dossier.get("risk_level") if isinstance(dossier, dict) else "", default="Not recorded"),
        "agreement": _cr_clean(consensus.get("jury_agreement") or consensus.get("consensus_level"), default="Not recorded"),
        "overall_confidence": consensus.get("overall_confidence"),
        "reason": _cr_clean(consensus.get("primary_reason") or consensus.get("final_reasoning"), default="Independent expert reasoning was not recorded."),
        "manipulation_count": manipulation_count,
        "expert_count": len(normalized),
    }


def _cr_timeline(bundle: Dict[str, Any]) -> List[Dict[str, str]]:
    timeline: List[Dict[str, str]] = []
    for event in bundle.get("timeline") or []:
        if not isinstance(event, Mapping):
            continue
        timestamp = _cr_text(event.get("timestamp"), default="")
        description = _cr_clean(event.get("description") or event.get("type"), default="")
        if timestamp or description:
            timeline.append({
                "timestamp": timestamp or "Time not recorded",
                "event": description or "Forensic event",
                "actor": _cr_clean(event.get("actor"), default="Not recorded"),
            })
    return timeline


def build_professional_report(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Build a concise four-page examiner-facing report from recorded data."""
    meta = bundle.get("meta") or {}
    evidence = bundle.get("evidence_summary") or {}
    findings = _cr_finding_rows(bundle)
    jury = _cr_jury(bundle)
    timeline = _cr_timeline(bundle)
    date, time = _date_time(meta.get("generated_at") or evidence.get("intake_timestamp"))
    case_id = _cr_text((bundle.get("case_context") or {}).get("case_id"), default="Not recorded")
    evidence_id = _cr_text(meta.get("evidence_id") or evidence.get("evidence_id"), default="Not recorded")
    filename = _cr_text(evidence.get("original_filename"), default="Not recorded")
    evidence_type = _cr_text(evidence.get("media_type"), default="Not recorded").title()
    titles = [finding["title"] for finding in findings[:3]]
    title_sentence = ", ".join(titles[:-1]) + (" and " if len(titles) > 1 else "") + titles[-1] if titles else ""

    if findings:
        executive_summary = (
            f"The submitted {evidence_type.lower()} was subjected to a digital forensic examination "
            "using the evidence and analysis outputs recorded for this item. "
            f"{len(findings)} finding"
            f"{'s were' if len(findings) != 1 else ' was'} recorded"
            f"{f', including {title_sentence.lower()}' if title_sentence else ''}. "
            "These observations identify content requiring verification against the original source "
            "before the evidence is relied upon."
        )
        opinion = (
            f"The forensic examination identified {len(findings)} recorded indicator"
            f"{'s' if len(findings) != 1 else ''} requiring review. "
            f"The principal observations concern {title_sentence.lower() if title_sentence else 'the localized evidence'}. "
            "The submitted material should not be treated as an authentic representation of the "
            "original source without independent verification."
        )
    else:
        executive_summary = (
            f"The submitted {evidence_type.lower()} was subjected to a digital forensic examination. "
            "No adverse finding rows were recorded in the available dossier. This result is limited "
            "to the evidence and methods documented for this examination."
        )
        opinion = (
            "No adverse finding rows were recorded in the available dossier. The material may be "
            "internally consistent within the documented scope, but source verification remains "
            "necessary where authenticity has legal, financial, or regulatory significance."
        )

    if jury["expert_count"]:
        jury_sentence = (
            f"{jury['manipulation_count']} of {jury['expert_count']} independent forensic reviewers "
            "recorded a Manipulated assessment."
        )
    else:
        jury_sentence = "Independent forensic expert review was not recorded for this examination."
    report_summary = {
        "evidence_id": evidence_id,
        "case_id": case_id,
        "finding_count": len(findings),
        "localized_count": sum(1 for finding in findings if finding.get("bbox")),
        "verdict": jury["verdict"],
        "risk_level": jury["risk_level"],
        "summary": executive_summary,
    }
    return {
        "title": "DIGITAL FORENSIC EXAMINATION REPORT",
        "subtitle": "Court-ready evidence review",
        "case_information": {
            "Evidence ID": evidence_id,
            "Case ID": case_id,
            "Investigation Date": date,
            "Investigator": _cr_text(evidence.get("intake_user"), default="Not recorded"),
            "Evidence Type": evidence_type,
            "Filename": filename,
            "SHA-256": _cr_text(evidence.get("sha256"), default="Not recorded", limit=128),
        },
        "evidence_id": evidence_id,
        "case_id": case_id,
        "evidence_name": filename,
        "investigation_date": date,
        "investigation_time": time,
        "verdict": jury["verdict"],
        "risk_level": jury["risk_level"],
        "executive_summary": executive_summary,
        "findings": findings,
        "finding_count": len(findings),
        "localized_regions": [finding for finding in findings if finding.get("bbox")],
        "localization_images": _cr_localization_images(bundle),
        "jury_review": jury,
        "jury_summary": {
            "statement": jury_sentence,
            "verdict": jury["verdict"],
            "agreement": jury["agreement"],
            "experts": jury["experts"],
        },
        "timeline": timeline,
        "expert_opinion": opinion,
        "opinion": opinion,
        "recommendations": list(dict.fromkeys(
            finding["recommendation"] for finding in findings if finding.get("recommendation")
        ))[:6],
        "report_summary": report_summary,
        "investigation_timeline": timeline,
        "appendix": {
            "hash": _cr_text(evidence.get("sha256"), default="Not recorded", limit=128),
            "chain_of_custody": (
                f"{evidence.get('custody_events', 0) or 0} recorded event(s); "
                f"integrity status: {'Verified' if evidence.get('chain_verified') else 'Not independently verified'}."
            ),
            "finding_traceability": ", ".join(finding["finding_id"] for finding in findings) or "No finding references recorded.",
        },
    }


def persist_report_sections(bundle: Dict[str, Any], report: Dict[str, Any]) -> None:
    """Append report-facing sections to the existing dossier atomically."""
    evidence_id = _cr_text((bundle.get("meta") or {}).get("evidence_id"), default="")
    if not evidence_id:
        return
    dossier_path = Path("data/temp/uploads/analysis") / evidence_id / "forensic_dossier.json"
    if not dossier_path.is_file():
        return
    with _REPORT_DOSSIER_LOCK:
        try:
            dossier = json.loads(dossier_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(dossier, dict):
            return
        dossier["report_summary"] = report["report_summary"]
        dossier["executive_summary"] = {
            "text": report["executive_summary"],
            "verdict": report["verdict"],
            "risk_level": report["risk_level"],
            "finding_count": report["finding_count"],
        }
        dossier["expert_opinion"] = report["expert_opinion"]
        if not dossier.get("jury_summary"):
            dossier["jury_summary"] = report["jury_summary"]
        else:
            dossier["report_jury_summary"] = report["jury_summary"]
        dossier["investigation_timeline"] = report["investigation_timeline"]
        fd, temporary_name = tempfile.mkstemp(
            prefix="forensic_dossier.",
            suffix=".tmp",
            dir=str(dossier_path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(dossier, handle, indent=2, ensure_ascii=False)
            os.replace(temporary_name, dossier_path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)


def _cr_pdf_styles():
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib import colors

    styles = getSampleStyleSheet()
    ink = colors.HexColor("#20252b")
    muted = colors.HexColor("#56616b")
    styles.add(ParagraphStyle("CRTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=17, leading=21, textColor=ink, alignment=TA_CENTER, spaceAfter=4))
    styles.add(ParagraphStyle("CRSubtitle", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=11, textColor=muted, alignment=TA_CENTER, spaceAfter=12))
    styles.add(ParagraphStyle("CRHeading", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11.5, leading=14, textColor=ink, spaceBefore=5, spaceAfter=6))
    styles.add(ParagraphStyle("CRBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=9, leading=12, textColor=ink, alignment=TA_LEFT, spaceAfter=5))
    styles.add(ParagraphStyle("CRSmall", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.2, leading=9, textColor=ink, alignment=TA_LEFT))
    styles.add(ParagraphStyle("CRSmallMuted", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.2, leading=9, textColor=muted, alignment=TA_LEFT))
    return styles


def export_professional_pdf(bundle: Dict[str, Any], output_path: Path) -> str:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import Image as ReportImage
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    report = build_professional_report(bundle)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    styles = _cr_pdf_styles()
    story: List[Any] = []

    def para(value: Any, style: str = "CRBody"):
        return Paragraph(escape(_cr_text(value, default="Not recorded", limit=5000)), styles[style])

    def table(rows: List[List[Any]], widths: List[float], header: bool = False) -> Table:
        result = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
        commands = [
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#aab2b8")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
        if header:
            commands.extend([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8edf0")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ])
        result.setStyle(TableStyle(commands))
        return result

    story.extend([para(report["title"], "CRTitle"), para(report["subtitle"], "CRSubtitle")])
    story.append(para("Case Information", "CRHeading"))
    story.append(table(
        [[para(label, "CRSmallMuted"), para(value, "CRSmall")] for label, value in report["case_information"].items()],
        [43 * mm, 125 * mm],
    ))
    story.append(para("Executive Summary", "CRHeading"))
    story.append(para(report["executive_summary"]))
    story.append(para("Scope", "CRHeading"))
    story.append(para(
        "This report presents only observations and evidence records contained in the AI-FORGE "
        "forensic dossier. It does not assume the provenance or authenticity of any supplied reference."
    ))
    story.append(PageBreak())

    story.append(para("FORENSIC FINDINGS", "CRTitle"))
    rows = [[para("ID", "CRSmall"), para("Finding", "CRSmall"), para("Location", "CRSmall"), para("Severity", "CRSmall"), para("Evidence and explanation", "CRSmall")]]
    displayed_findings = report["findings"][:12]
    for finding in displayed_findings:
        evidence_text = "; ".join(finding["evidence"]) or "No supporting evidence text recorded."
        rows.append([
            para(finding["finding_id"], "CRSmall"),
            para(finding["title"], "CRSmall"),
            para(finding["location"], "CRSmall"),
            para(finding["severity"], "CRSmall"),
            para(f"{evidence_text}<br/><b>Explanation:</b> {finding['explanation']}", "CRSmall"),
        ])
    if len(report["findings"]) > len(displayed_findings):
        rows.append([para("—", "CRSmall"), para("Additional finding records remain in the dossier.", "CRSmall"), para("—", "CRSmall"), para("—", "CRSmall"), para(f"{len(report['findings']) - len(displayed_findings)} additional record(s) retained for traceability.", "CRSmall")])
    if len(rows) == 1:
        rows.append([para("—", "CRSmall"), para("No adverse finding rows were recorded.", "CRSmall"), para("—", "CRSmall"), para("—", "CRSmall"), para("The available dossier contains no finding-level evidence for this report.", "CRSmall")])
    story.append(table(rows, [18 * mm, 31 * mm, 34 * mm, 19 * mm, 66 * mm], header=True))
    story.append(Spacer(1, 4 * mm))
    story.append(para("Each finding is traceable to a recorded dossier row. Numeric evidence values are retained in the technical source records rather than repeated as a confidence display in this report.", "CRSmallMuted"))
    story.append(PageBreak())

    story.append(para("LOCALIZED EVIDENCE", "CRTitle"))
    image_cells: List[List[Any]] = []
    for item in report["localization_images"][:4]:
        try:
            image = ReportImage(item["path"], width=78 * mm, height=48 * mm)
            image_cells.append([para(item["label"], "CRSmall"), image])
        except (OSError, ValueError):
            continue
    if image_cells:
        image_table = Table(image_cells, colWidths=[28 * mm, 78 * mm])
        image_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#aab2b8"))]))
        story.append(image_table)
    else:
        story.append(para("No localization image artifact was recorded for this examination."))
    story.append(para("Localized Regions", "CRHeading"))
    region_rows = [[para("Region", "CRSmall"), para("Finding", "CRSmall"), para("Location", "CRSmall"), para("Reason and evidence", "CRSmall")]]
    for index, finding in enumerate(report["localized_regions"][:8]):
        reason = finding["technical_reason"]
        evidence = "; ".join(finding["evidence"])
        region_rows.append([
            para(f"Region {chr(65 + index)}", "CRSmall"),
            para(finding["title"], "CRSmall"),
            para(finding["location"], "CRSmall"),
            para(f"{reason}<br/>Evidence strength: {finding['evidence_strength']}{f'<br/>{evidence}' if evidence else ''}", "CRSmall"),
        ])
    if len(region_rows) == 1:
        region_rows.append([para("—", "CRSmall"), para("No localized regions recorded.", "CRSmall"), para("—", "CRSmall"), para("No finding with a recorded bounding box was available.", "CRSmall")])
    story.append(table(region_rows, [20 * mm, 36 * mm, 45 * mm, 59 * mm], header=True))
    story.append(PageBreak())

    story.append(para("FORENSIC OPINION", "CRTitle"))
    story.append(para(report["expert_opinion"]))
    story.append(para("Independent Forensic Expert Review", "CRHeading"))
    jury = report["jury_review"]
    jury_rows = [[para("Reviewer", "CRSmall"), para("Assessment", "CRSmall"), para("Recorded evidence", "CRSmall")]]
    for expert in jury["experts"]:
        jury_rows.append([para(expert["name"], "CRSmall"), para(expert["vote"], "CRSmall"), para(", ".join(expert["evidence"]) or "No finding reference recorded.", "CRSmall")])
    if len(jury_rows) == 1:
        jury_rows.append([para("—", "CRSmall"), para("Not recorded", "CRSmall"), para("Independent review was not recorded.", "CRSmall")])
    story.append(table(jury_rows, [60 * mm, 29 * mm, 71 * mm], header=True))
    story.append(para(report["jury_summary"]["statement"], "CRSmallMuted"))
    story.append(para("Investigation Timeline", "CRHeading"))
    timeline_rows = [[para("Time", "CRSmall"), para("Event", "CRSmall"), para("Actor", "CRSmall")]]
    for event in report["timeline"][:8]:
        timeline_rows.append([para(event["timestamp"], "CRSmall"), para(event["event"], "CRSmall"), para(event["actor"], "CRSmall")])
    if len(timeline_rows) == 1:
        timeline_rows.append([para("—", "CRSmall"), para("No timestamped investigation events recorded.", "CRSmall"), para("—", "CRSmall")])
    story.append(table(timeline_rows, [40 * mm, 95 * mm, 25 * mm], header=True))
    if report["recommendations"]:
        story.append(para("Recommendations", "CRHeading"))
        for recommendation in report["recommendations"][:5]:
            story.append(para(f"• {recommendation}", "CRSmall"))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#aab2b8"))
        canvas.line(20 * mm, 15 * mm, A4[0] - 20 * mm, 15 * mm)
        canvas.setFillColor(colors.HexColor("#56616b"))
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(20 * mm, 10 * mm, f"Evidence ID: {report['evidence_id']} · Confidential")
        canvas.drawRightString(A4[0] - 20 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(str(output_path), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=16 * mm, bottomMargin=20 * mm, title=f"Digital Forensic Examination Report — {report['evidence_id']}", author="Digital Forensic Examination Service")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return str(output_path)


def export_professional_docx(bundle: Dict[str, Any], output_path: Path) -> str:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Inches, Pt

    report = build_professional_report(bundle)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.6)
    section.bottom_margin = Inches(0.6)
    section.left_margin = Inches(0.7)
    section.right_margin = Inches(0.7)
    document.styles["Normal"].font.name = "Arial"
    document.styles["Normal"].font.size = Pt(9)

    def heading(text: str, level: int = 1):
        paragraph = document.add_heading(text, level)
        paragraph.style.font.name = "Arial"
        return paragraph

    def add_table(rows: List[List[str]]):
        result = document.add_table(rows=0, cols=len(rows[0]))
        result.style = "Table Grid"
        for values in rows:
            cells = result.add_row().cells
            for index, value in enumerate(values):
                cells[index].text = str(value)
        return result

    title = document.add_heading(report["title"], 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle = document.add_paragraph(report["subtitle"])
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_table([[label, value] for label, value in report["case_information"].items()])
    heading("Executive Summary")
    document.add_paragraph(report["executive_summary"])
    document.add_paragraph("This report presents only observations and evidence records contained in the forensic dossier.")
    document.add_page_break()

    title = document.add_heading("FORENSIC FINDINGS", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    finding_rows = [["ID", "Finding", "Location", "Severity", "Evidence and explanation"]]
    for finding in report["findings"][:12]:
        finding_rows.append([
            finding["finding_id"],
            finding["title"],
            finding["location"],
            finding["severity"],
            f"{'; '.join(finding['evidence']) or 'No supporting evidence text recorded.'}\nExplanation: {finding['explanation']}",
        ])
    if len(finding_rows) == 1:
        finding_rows.append(["—", "No adverse finding rows were recorded.", "—", "—", "No finding-level evidence was available."])
    add_table(finding_rows)
    document.add_page_break()

    title = document.add_heading("LOCALIZED EVIDENCE", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for item in report["localization_images"][:4]:
        document.add_paragraph(item["label"])
        try:
            document.add_picture(item["path"], width=Inches(3.0))
        except (OSError, ValueError):
            pass
    region_rows = [["Region", "Finding", "Location", "Reason and evidence"]]
    for index, finding in enumerate(report["localized_regions"][:8]):
        region_rows.append([
            f"Region {chr(65 + index)}",
            finding["title"],
            finding["location"],
            f"{finding['technical_reason']}\nEvidence strength: {finding['evidence_strength']}",
        ])
    if len(region_rows) == 1:
        region_rows.append(["—", "No localized regions recorded.", "—", "No finding with a bounding box was available."])
    add_table(region_rows)
    document.add_page_break()

    title = document.add_heading("FORENSIC OPINION", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.add_paragraph(report["expert_opinion"])
    heading("Independent Forensic Expert Review")
    jury_rows = [["Reviewer", "Assessment", "Recorded evidence"]]
    for expert in report["jury_review"]["experts"]:
        jury_rows.append([expert["name"], expert["vote"], ", ".join(expert["evidence"]) or "No finding reference recorded."])
    if len(jury_rows) == 1:
        jury_rows.append(["—", "Not recorded", "Independent review was not recorded."])
    add_table(jury_rows)
    document.add_paragraph(report["jury_summary"]["statement"])
    heading("Investigation Timeline")
    timeline_rows = [["Time", "Event", "Actor"]]
    for event in report["timeline"][:8]:
        timeline_rows.append([event["timestamp"], event["event"], event["actor"]])
    if len(timeline_rows) == 1:
        timeline_rows.append(["—", "No timestamped investigation events recorded.", "—"])
    add_table(timeline_rows)
    if report["recommendations"]:
        heading("Recommendations")
        for recommendation in report["recommendations"][:5]:
            document.add_paragraph(recommendation, style="List Bullet")

    for current_section in document.sections:
        footer = current_section.footer.paragraphs[0]
        footer.text = f"Evidence ID: {report['evidence_id']} · Confidential · "
        run = footer.add_run()
        begin = OxmlElement("w:fldChar")
        begin.set(qn("w:fldCharType"), "begin")
        instruction = OxmlElement("w:instrText")
        instruction.set(qn("xml:space"), "preserve")
        instruction.text = "PAGE"
        end = OxmlElement("w:fldChar")
        end.set(qn("w:fldCharType"), "end")
        run._r.extend([begin, instruction, end])
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.save(str(output_path))
    return str(output_path)


def export_professional_html(bundle: Dict[str, Any], output_path: Path) -> str:
    report = build_professional_report(bundle)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    esc = lambda value: html.escape(_cr_text(value, default="Not recorded", limit=5000))
    case_rows = "".join(f"<tr><th>{esc(label)}</th><td>{esc(value)}</td></tr>" for label, value in report["case_information"].items())
    finding_rows = "".join(
        f"<tr><td>{esc(f['finding_id'])}</td><td>{esc(f['title'])}</td><td>{esc(f['location'])}</td><td>{esc(f['severity'])}</td><td>{esc('; '.join(f['evidence']) or 'No supporting evidence text recorded.')}<br><b>Explanation:</b> {esc(f['explanation'])}</td></tr>"
        for f in report["findings"][:12]
    ) or "<tr><td colspan='5'>No adverse finding rows were recorded.</td></tr>"
    regions = "".join(
        f"<tr><td>Region {chr(65 + i)}</td><td>{esc(f['title'])}</td><td>{esc(f['location'])}</td><td>{esc(f['technical_reason'])}<br>Evidence strength: {esc(f['evidence_strength'])}</td></tr>"
        for i, f in enumerate(report["localized_regions"][:8])
    ) or "<tr><td colspan='4'>No localized regions recorded.</td></tr>"
    experts = "".join(
        f"<tr><td>{esc(e['name'])}</td><td>{esc(e['vote'])}</td><td>{esc(', '.join(e['evidence']) or 'No finding reference recorded.')}</td></tr>"
        for e in report["jury_review"]["experts"]
    ) or "<tr><td colspan='3'>Independent review was not recorded.</td></tr>"
    timeline = "".join(
        f"<tr><td>{esc(e['timestamp'])}</td><td>{esc(e['event'])}</td><td>{esc(e['actor'])}</td></tr>"
        for e in report["timeline"][:8]
    ) or "<tr><td colspan='3'>No timestamped investigation events recorded.</td></tr>"
    images = "".join(
        f"<figure><figcaption>{esc(item['label'])}</figcaption><img src='{esc(Path(item['path']).as_uri())}' alt='{esc(item['label'])}'></figure>"
        for item in report["localization_images"][:4]
    ) or "<p>No localization image artifact was recorded.</p>"
    html_content = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{esc(report['title'])}</title>
<style>
@page{{size:A4;margin:16mm 18mm}}*{{box-sizing:border-box}}body{{font:10pt/1.4 Arial,sans-serif;color:#20252b;margin:0}}.page{{min-height:257mm;padding:4mm 0 12mm;page-break-after:always}}.page:last-child{{page-break-after:auto}}h1{{font-size:17pt;text-align:center;margin:0 0 5pt}}h2{{font-size:12pt;border-bottom:1px solid #aab2b8;padding-bottom:4pt;margin:16pt 0 7pt}}p{{margin:0 0 7pt}}table{{border-collapse:collapse;width:100%;table-layout:fixed}}th,td{{border:1px solid #aab2b8;padding:5pt;vertical-align:top;word-wrap:break-word}}th{{background:#e8edf0;text-align:left}}.muted{{color:#56616b;font-size:8.5pt}}figure{{display:inline-block;width:48%;margin:1% 1% 4%;vertical-align:top}}figure img{{max-width:100%;max-height:55mm}}figcaption{{font-weight:bold;margin-bottom:4pt}}footer{{border-top:1px solid #aab2b8;margin-top:14pt;padding-top:5pt;color:#56616b;font-size:8pt;text-align:center}}
</style></head><body>
<section class="page"><h1>{esc(report['title'])}</h1><p class="muted" style="text-align:center">{esc(report['subtitle'])}</p>
<h2>Case Information</h2><table>{case_rows}</table><h2>Executive Summary</h2><p>{esc(report['executive_summary'])}</p><h2>Scope</h2><p>This report presents only observations and evidence records contained in the forensic dossier.</p><footer>Evidence ID: {esc(report['evidence_id'])} · Page 1</footer></section>
<section class="page"><h1>FORENSIC FINDINGS</h1><table><tr><th>ID</th><th>Finding</th><th>Location</th><th>Severity</th><th>Evidence and explanation</th></tr>{finding_rows}</table><footer>Evidence ID: {esc(report['evidence_id'])} · Page 2</footer></section>
<section class="page"><h1>LOCALIZED EVIDENCE</h1>{images}<h2>Localized Regions</h2><table><tr><th>Region</th><th>Finding</th><th>Location</th><th>Reason and evidence</th></tr>{regions}</table><footer>Evidence ID: {esc(report['evidence_id'])} · Page 3</footer></section>
<section class="page"><h1>FORENSIC OPINION</h1><p>{esc(report['expert_opinion'])}</p><h2>Independent Forensic Expert Review</h2><table><tr><th>Reviewer</th><th>Assessment</th><th>Recorded evidence</th></tr>{experts}</table><p>{esc(report['jury_summary']['statement'])}</p><h2>Investigation Timeline</h2><table><tr><th>Time</th><th>Event</th><th>Actor</th></tr>{timeline}</table><h2>Recommendations</h2><ul>{''.join(f'<li>{esc(item)}</li>' for item in report['recommendations'][:5])}</ul><footer>Evidence ID: {esc(report['evidence_id'])} · Page 4</footer></section>
</body></html>"""
    output_path.write_text(html_content, encoding="utf-8")
    return str(output_path)
