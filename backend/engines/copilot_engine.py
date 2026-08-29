"""
AI Investigator Copilot — evidence-grounded natural language Q&A.

Answers ONLY from structured forensic payloads:
  detector outputs, fusion, localization, reasoning, jury, metadata, OCR, reports.

Never hallucinates detectors, scores, or regions not present in context.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.evidence.paths import get_analysis_dir, find_evidence_file
from backend.forensics.repository import get_evidence_record

logger = logging.getLogger("ai_forge.copilot")

UPLOAD_DIR = Path("data/temp/uploads")


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def load_investigation_context(evidence_id: str) -> Dict[str, Any]:
    """Aggregate all grounded sources for one evidence item."""
    analysis_dir = get_analysis_dir(evidence_id, create=False)
    legacy_dir = UPLOAD_DIR / "analysis" / evidence_id

    def _pick(name: str) -> Path:
        p = analysis_dir / name
        return p if p.is_file() else legacy_dir / name

    analysis = _load_json(_pick("analysis.json")) or _load_json(_pick("document_analysis.json"))
    jury = _load_json(_pick("jury.json"))
    localization = _load_json(_pick("localization.json"))
    reasoning = _load_json(_pick("forensic_reasoning.json"))
    explainable = _load_json(_pick("explainable_ai.json"))
    dashboard = _load_json(_pick("dashboard.json"))
    recommendation = _load_json(_pick("recommendation.json"))

    if not localization.get("regions"):
        try:
            from backend.analysis.forgery_localization import load_localization

            localization = load_localization(evidence_id) or localization
        except Exception:
            pass

    if not reasoning and analysis.get("forensic_reasoning"):
        reasoning = analysis["forensic_reasoning"]
    if not explainable and analysis.get("explainable_ai"):
        explainable = analysis["explainable_ai"]

    evidence_record = {}
    try:
        evidence_record = get_evidence_record(evidence_id) or {}
    except Exception:
        pass

    fusion = analysis.get("evidence_fusion") or analysis.get("risk_fusion") or {}
    detectors = analysis.get("detector_outputs") or []
    ocr = analysis.get("ocr") or analysis.get("text_layout") or {}
    metadata = analysis.get("metadata") or analysis.get("metadata_forensics") or {}

    return {
        "evidence_id": evidence_id,
        "analysis": analysis,
        "fusion": fusion,
        "detectors": detectors if isinstance(detectors, list) else [],
        "localization": localization,
        "regions": localization.get("regions") or [],
        "forensic_reasoning": reasoning,
        "explainable_ai": explainable,
        "jury": jury,
        "dashboard": dashboard,
        "recommendation": recommendation,
        "metadata": metadata,
        "ocr": ocr,
        "evidence_record": evidence_record,
        "has_file": bool(find_evidence_file(evidence_id)),
    }


# ── Intent patterns ──────────────────────────────────────────────────────────

_INTENTS: List[Tuple[str, re.Pattern]] = [
    ("why_suspicious", re.compile(
        r"why.*(suspicious|flagged|risk|manipulat|forgery|fake|tamper)|what.*wrong",
        re.I,
    )),
    ("amount_changed", re.compile(
        r"where.*(amount|invoice|total|number).*(chang|edit)|amount.*(chang|edit|where)",
        re.I,
    )),
    ("which_region", re.compile(
        r"which region|where.*(edit|modif|chang)|what.*(edit|modif)|show.*region|locat",
        re.I,
    )),
    ("show_edited", re.compile(
        r"show.*(edit|suspicious|anomal|forgery|mask)|only.*(edit|suspicious)|highlight",
        re.I,
    )),
    ("detector_disagreement", re.compile(
        r"disagree|conflict|contradict|minority|split|diverg",
        re.I,
    )),
    ("summarize", re.compile(
        r"summar|overview|brief|case status|what happened",
        re.I,
    )),
    ("evidence_verdict", re.compile(
        r"evidence.*(verdict|finding|support)|what supports|why.*verdict|proof",
        re.I,
    )),
    ("court_explanation", re.compile(
        r"court|legal|testimony|affidavit|expert witness",
        re.I,
    )),
    ("highest_confidence", re.compile(
        r"highest confidence|most confident|strongest detector|best detector|top detector",
        re.I,
    )),
    ("ocr_failure", re.compile(
        r"ocr.*(fail|error|low|miss)|why.*ocr|text extraction",
        re.I,
    )),
    ("compare_regions", re.compile(
        r"compare.*(original|region|suspicious)|original vs|difference between",
        re.I,
    )),
]


def classify_intent(question: str, history: Optional[List[Dict]] = None) -> str:
    q = (question or "").strip()
    for name, pat in _INTENTS:
        if pat.search(q):
            return name
    # Follow-up context from history
    if history:
        last_intent = next(
            (h.get("intent") for h in reversed(history) if h.get("intent")),
            None,
        )
        if last_intent in ("which_region", "amount_changed") and re.search(
            r"that|this|it|more|detail|explain", q, re.I
        ):
            return last_intent
    return "general"


def _region_by_keywords(regions: List[Dict], *keywords: str) -> Optional[Dict]:
    for reg in regions:
        blob = " ".join(
            str(reg.get(k, "")) for k in ("label", "type", "manipulation", "finding", "reason")
        ).lower()
        if any(kw in blob for kw in keywords):
            return reg
    return regions[0] if regions else None


def _highest_confidence_detector(ctx: Dict) -> Tuple[str, float]:
    best_name, best_score = "", 0.0
    for d in ctx.get("detectors") or []:
        if d.get("status") not in (None, "ok"):
            continue
        score = float(d.get("score") or 0) * float(d.get("confidence") or 0)
        if score > best_score:
            best_score = score
            best_name = str(d.get("detector_name", ""))
    if not best_name:
        for c in (ctx.get("fusion") or {}).get("detector_contributions") or []:
            score = float(c.get("contribution") or c.get("score") or 0)
            if score > best_score:
                best_score = score
                best_name = str(c.get("detector") or c.get("name") or "")
    return best_name.replace("_", " ").title(), best_score


def _format_detector_list(detectors: List[Dict], limit: int = 8) -> List[str]:
    lines = []
    for d in sorted(detectors, key=lambda x: float(x.get("score") or 0), reverse=True)[:limit]:
        if d.get("status") not in (None, "ok"):
            continue
        name = str(d.get("detector_name", "")).replace("_", " ").upper()
        score = float(d.get("score") or 0)
        conf = float(d.get("confidence") or 0)
        reason = (d.get("technical_reason") or "")[:160]
        lines.append(f"{name}: score {score:.2f}, confidence {conf:.2f}" + (f" — {reason}" if reason else ""))
    return lines


def _actions_for_region(reg: Optional[Dict], *, view_mode: str = "bounding_boxes") -> Dict[str, Any]:
    if not reg:
        return {}
    return {
        "highlight_region_id": reg.get("id"),
        "highlight_region_ids": [reg.get("id")] if reg.get("id") else [],
        "zoom_region_id": reg.get("id"),
        "view_mode": view_mode,
    }


def answer_copilot_question(
    question: str,
    ctx: Dict[str, Any],
    *,
    history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Generate grounded copilot response from investigation context."""
    history = history or []
    intent = classify_intent(question, history)
    regions = ctx.get("regions") or []
    reasoning = ctx.get("forensic_reasoning") or {}
    xai = ctx.get("explainable_ai") or {}
    fusion = ctx.get("fusion") or {}
    jury = ctx.get("jury") or {}
    findings = reasoning.get("findings") or []
    primary = findings[0] if findings else {}
    sources: List[Dict[str, str]] = []
    evidence: List[str] = []
    actions: Dict[str, Any] = {}

    def src(stype: str, field: str) -> None:
        sources.append({"type": stype, "field": field})

    verdict = (
        fusion.get("verdict")
        or ctx.get("analysis", {}).get("verdict")
        or jury.get("fusion", {}).get("verdict")
        or jury.get("verdict")
        or "Not recorded"
    )
    risk = float(fusion.get("overall_score") or fusion.get("overall_fraud_risk") or ctx.get("analysis", {}).get("risk_score") or 0)
    conf = float(
        reasoning.get("primary_confidence")
        or primary.get("confidence")
        or fusion.get("confidence")
        or 0
    )

    # ── Intent handlers ──────────────────────────────────────────────────

    if intent == "why_suspicious":
        src("explainable_ai", "investigation_summary")
        inv = xai.get("investigation_summary") or xai.get("executive_summary")
        if inv:
            answer = inv
        elif primary:
            src("forensic_reasoning", "findings")
            bullets = [
                f"• {s.get('detector', '').upper()}: {s.get('observation', '')}"
                for s in primary.get("supporting_evidence") or []
            ]
            answer = (
                f"This evidence is flagged as suspicious: {primary.get('finding')} "
                f"(confidence {primary.get('confidence')}%).\n\n"
                f"Verdict: {verdict} | Risk score: {risk:.1f}\n\n"
                f"Supporting Evidence\n" + "\n".join(bullets)
            )
            evidence = bullets
        else:
            src("fusion", "verdict")
            det_lines = _format_detector_list(ctx.get("detectors") or [])
            answer = (
                f"Verdict: {verdict} (risk {risk:.1f}/100).\n\n"
                + ("\n".join(det_lines) if det_lines else "No elevated detector outputs in the analysis record.")
            )
            evidence = det_lines

    elif intent == "amount_changed":
        reg = _region_by_keywords(regions, "amount", "invoice", "number", "total")
        if not reg and regions:
            reg = _region_by_keywords(regions, "invoice") or regions[0]
        src("localization", "regions")
        actions = _actions_for_region(reg, view_mode="polygons")
        if reg:
            plain = reg.get("plain_english_explanation") or reg.get("finding") or ""
            answer = (
                f"The amount-related anomaly is localized to **{reg.get('label') or reg.get('id')}** "
                f"in the {reg.get('manipulation') or 'edited field'}.\n\n"
                f"{plain}\n\n"
                f"Coordinates: x={reg.get('coordinates', {}).get('x', reg.get('bbox', {}).get('x'))}, "
                f"y={reg.get('coordinates', {}).get('y', reg.get('bbox', {}).get('y'))} | "
                f"Confidence: {reg.get('confidence', '—')}%.\n\n"
                "The viewer has zoomed to this region."
            )
            evidence = list(reg.get("evidence") or [])
        else:
            answer = (
                "No localized amount region is recorded in the localization engine output. "
                f"Case-level finding: {primary.get('finding') or verdict}."
            )

    elif intent == "which_region":
        src("localization", "regions")
        if not regions:
            answer = "No suspicious regions were localized for this evidence item."
        else:
            lines = []
            ids = []
            for i, reg in enumerate(regions[:10], 1):
                lines.append(
                    f"{i}. {reg.get('label') or reg.get('id')} — "
                    f"{reg.get('finding') or reg.get('manipulation') or reg.get('reason', 'anomaly')} "
                    f"(confidence {reg.get('confidence', '—')}%)"
                )
                if reg.get("id"):
                    ids.append(reg["id"])
            reg = regions[0]
            actions = {
                "highlight_region_ids": ids,
                "highlight_region_id": reg.get("id"),
                "zoom_region_id": reg.get("id"),
                "view_mode": "bounding_boxes",
            }
            answer = (
                f"{len(regions)} suspicious region(s) identified:\n\n"
                + "\n".join(lines)
                + "\n\nSelecting the highest-priority region in the viewer."
            )
            evidence = [r.get("plain_english_explanation") or r.get("technical_explanation", "") for r in regions[:5]]

    elif intent == "show_edited":
        src("localization", "regions")
        actions = {
            "view_mode": "forgery_mask",
            "highlight_region_ids": [r.get("id") for r in regions if r.get("id")],
        }
        if regions:
            answer = (
                f"Displaying forgery mask overlay with {len(regions)} localized edited area(s). "
                "Switch to Mask view to see pixel-level modifications."
            )
        else:
            coverage = ctx.get("localization", {}).get("coverage")
            answer = (
                f"Mask overlay activated. Localization coverage: {coverage or '—'}. "
                "No discrete region polygons were extracted."
            )

    elif intent == "detector_disagreement":
        src("jury", "fusion")
        src("forensic_reasoning", "contradictory_evidence")
        jury_fusion = jury.get("fusion") or jury
        disagreements = jury_fusion.get("disagreements") or jury.get("disagreements") or []
        minority = jury_fusion.get("minority_opinion") or jury.get("minority_opinion") or ""
        contra = []
        for f in findings:
            contra.extend(f.get("contradictory_evidence") or [])
        lines = []
        for d in disagreements[:5]:
            lines.append(f"• Jury: {d.get('agent', d.get('module', 'agent'))} — {d.get('finding', d.get('reason', ''))}")
        for c in contra[:5]:
            lines.append(f"• Contradiction: {c.get('detector', '')} — {c.get('observation', '')}")
        if lines:
            answer = "Detector disagreement analysis:\n\n" + "\n".join(lines)
            if minority:
                answer += f"\n\nMinority opinion: {minority}"
        else:
            elevated = fusion.get("elevated_detectors") or fusion.get("elevated_modules") or []
            answer = (
                "No explicit jury disagreements or contradictory evidence nodes recorded. "
                f"Elevated detectors: {', '.join(elevated) if elevated else 'none above threshold'}."
            )
        evidence = lines

    elif intent == "summarize":
        src("explainable_ai", "executive_summary")
        exec_sum = xai.get("executive_summary") or xai.get("investigation_summary")
        if exec_sum:
            answer = exec_sum
        else:
            src("forensic_reasoning", "primary_finding")
            answer = (
                f"Case {ctx.get('evidence_id')}: {primary.get('finding') or verdict} "
                f"(confidence {conf:.1f}%, risk {risk:.1f}). "
                f"{len(regions)} localized region(s). "
                f"Recommendation: {primary.get('recommendation') or 'See full report.'}"
            )
        evidence = xai.get("key_evidence") or []

    elif intent == "evidence_verdict":
        src("forensic_reasoning", "findings")
        bullets = []
        for f in findings[:3]:
            bullets.append(f"**{f.get('finding')}** ({f.get('confidence')}%)")
            for s in f.get("supporting_evidence") or []:
                bullets.append(f"  • {s.get('detector', '').upper()}: {s.get('observation', '')}")
        jury_reason = (jury.get("fusion") or jury).get("reasoning") or jury.get("reasoning") or ""
        answer = (
            f"Verdict: {verdict}\n\nEvidence supporting this conclusion:\n"
            + ("\n".join(bullets) if bullets else "No reasoning findings indexed.")
        )
        if jury_reason:
            answer += f"\n\nJury synthesis: {jury_reason[:400]}"
        evidence = bullets

    elif intent == "court_explanation":
        src("explainable_ai", "court_explanation")
        court = xai.get("court_explanation")
        if court:
            answer = court
        else:
            answer = (
                "Court-ready explanation not yet generated. "
                "Re-run analysis to produce explainable_ai.json, or export a Court template report."
            )

    elif intent == "highest_confidence":
        src("detector_outputs", "detectors")
        name, score = _highest_confidence_detector(ctx)
        if name:
            answer = (
                f"The detector with the highest weighted confidence is **{name}** "
                f"(score × confidence = {score:.3f}).\n\n"
                + "\n".join(_format_detector_list(ctx.get("detectors") or [], 5))
            )
        else:
            answer = "No detector outputs are available in the analysis record for this evidence."
        evidence = _format_detector_list(ctx.get("detectors") or [], 3)

    elif intent == "ocr_failure":
        src("ocr", "ocr")
        ocr = ctx.get("ocr") or {}
        ocr_det = next(
            (d for d in (ctx.get("detectors") or []) if str(d.get("detector_name", "")).lower() == "ocr"),
            None,
        )
        lines = []
        if ocr.get("error"):
            lines.append(f"OCR error: {ocr['error']}")
        if ocr.get("skipped") or (ocr_det and ocr_det.get("status") == "skipped"):
            lines.append(f"OCR skipped: {ocr_det.get('technical_reason') if ocr_det else ocr.get('reason', 'module not run')}")
        mismatches = ocr.get("mismatch_regions") or ocr.get("suspicious_words") or []
        if mismatches:
            lines.append(f"{len(mismatches)} OCR mismatch region(s) recorded.")
        consensus = ocr.get("consensus") or {}
        if consensus.get("reasoning"):
            lines.append(f"Consensus: {consensus['reasoning']}")
        if ocr_det and ocr_det.get("technical_reason"):
            lines.append(f"Detector: {ocr_det['technical_reason']}")
        answer = (
            "\n".join(lines) if lines else
            "OCR completed without recorded failures. Check font_consistency and text_layout modules for typography flags."
        )
        evidence = lines

    elif intent == "compare_regions":
        src("localization", "regions")
        actions = {"view_mode": "difference"}
        if len(regions) >= 1:
            reg = regions[0]
            actions.update(_actions_for_region(reg, view_mode="difference"))
            answer = (
                f"Comparison mode: Difference overlay vs original.\n\n"
                f"Primary suspicious region: {reg.get('label') or reg.get('id')} — "
                f"{reg.get('plain_english_explanation') or reg.get('technical_explanation', '')[:300]}"
            )
        else:
            answer = "No localized regions available for side-by-side comparison. Showing difference overlay for full image."

    else:
        # General — use reasoning/explainable only
        src("explainable_ai", "investigation_summary")
        inv = xai.get("investigation_summary") or reasoning.get("narrative")
        if inv:
            answer = inv
        elif primary:
            answer = (
                f"{primary.get('finding')} (confidence {primary.get('confidence')}%). "
                f"{primary.get('recommendation') or ''}"
            )
        else:
            answer = (
                f"Forensic record for {ctx.get('evidence_id')}: {verdict}, risk {risk:.1f}/100. "
                "Ask about specific regions, detectors, jury disagreement, or court explanation."
            )

    return {
        "answer": answer.strip(),
        "intent": intent,
        "sources": sources,
        "evidence": [e for e in evidence if e],
        "actions": actions,
        "confidence": conf,
        "evidence_id": ctx.get("evidence_id"),
        "grounded": True,
    }


def answer_with_context(
    question: str,
    evidence_id: str,
    *,
    history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    if not evidence_id:
        return {
            "answer": "Evidence ID is required. Select an analyzed evidence item first.",
            "intent": "error",
            "sources": [],
            "evidence": [],
            "actions": {},
            "grounded": True,
        }
    ctx = load_investigation_context(evidence_id)
    if not ctx.get("has_file") and not ctx.get("analysis"):
        return {
            "answer": f"No forensic analysis record found for {evidence_id}. Run analysis first.",
            "intent": "error",
            "sources": [],
            "evidence": [],
            "actions": {},
            "grounded": True,
            "evidence_id": evidence_id,
        }
    return answer_copilot_question(question, ctx, history=history)
