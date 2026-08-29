"""
Reasoning + Judge + Report Writer agents.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.agents.investigation.base import AgentResult
from backend.agents.investigation.confidence import calibrate_confidence
from backend.agents.investigation.correlation import correlate_evidence

logger = logging.getLogger("ai_forge.agents.reasoning")


def run_reasoning_agent(
    agent_outputs: Dict[str, AgentResult],
    correlation: Dict[str, Any],
) -> AgentResult:
    t0 = time.perf_counter()
    findings: List[str] = []
    conflicts: List[str] = []

    for aid, res in agent_outputs.items():
        if res.status == "failed":
            conflicts.append(f"{res.agent_name} failed: {res.error}")
        elif res.status == "skipped":
            findings.append(f"{res.agent_name} skipped — {res.reason or 'not applicable'}")
        elif res.status == "completed":
            findings.append(
                f"{res.agent_name}: verdict={res.verdict}, "
                f"confidence={round(res.confidence * 100, 1)}%, "
                f"risk={round(res.risk_score * 100, 1)}%"
            )

    for inc in correlation.get("inconsistencies") or []:
        conflicts.append(inc.get("explanation") or str(inc))
        findings.append(f"CONFLICT: {inc.get('explanation')}")

    for corr in correlation.get("correlations") or []:
        findings.append(f"ALIGNED: {corr.get('explanation')}")

    explanation = (
        "Reasoning Agent synthesized specialist outputs. "
        + (f"Detected {len(conflicts)} conflict(s). " if conflicts else "No major conflicts. ")
        + correlation.get("cross_modal_summary", "")
    )

    # Reasoning confidence: high when many completed agents agree directionally
    completed = [r for r in agent_outputs.values() if r.status == "completed"]
    if completed:
        risks = [r.risk_score for r in completed]
        spread = max(risks) - min(risks) if risks else 0
        conf = max(0.55, min(0.95, 0.9 - spread * 0.35))
        risk = sum(risks) / len(risks)
    else:
        conf, risk = 0.4, 0.5

    risk = min(1.0, risk + float(correlation.get("risk_boost") or 0))

    return AgentResult(
        agent_id="reasoning",
        agent_name="Reasoning Agent",
        status="completed",
        confidence=conf,
        risk_score=risk,
        verdict="CONFLICTS" if conflicts else "CONSISTENT",
        findings=findings[:24],
        executed_modules=["cross_validation", "conflict_detection"],
        data={
            "explanation": explanation,
            "conflicts": conflicts,
            "correlation": correlation,
        },
        duration_ms=(time.perf_counter() - t0) * 1000,
        reason=explanation,
    )


def run_judge_agent(
    agent_outputs: Dict[str, AgentResult],
    *,
    analysis: Optional[Dict] = None,
    tampering: Optional[Dict] = None,
    document_analysis: Optional[Dict] = None,
    video_analysis: Optional[Dict] = None,
    signature_result: Optional[Dict] = None,
    evidence_id: Optional[str] = None,
) -> AgentResult:
    t0 = time.perf_counter()
    try:
        from backend.agents.jury.orchestrator import run_jury_analysis

        jury = run_jury_analysis(
            analysis=analysis,
            tampering=tampering,
            document_analysis=document_analysis,
            video_analysis=video_analysis,
            signature_result=signature_result,
            evidence_id=evidence_id,
        )
    except Exception as exc:
        logger.warning("Jury orchestrator fallback: %s", exc)
        jury = {"fusion": {}, "agents": {}, "error": str(exc)}

    components = {
        aid: res.confidence
        for aid, res in agent_outputs.items()
        if res.status == "completed" and res.confidence > 0
    }
    # Prefer risk-oriented confidence for fraud calibration
    risk_components = {
        aid: res.risk_score if res.risk_score > 0 else (1.0 - res.confidence)
        for aid, res in agent_outputs.items()
        if res.status == "completed"
    }
    calibration = calibrate_confidence(components)
    risk_cal = calibrate_confidence(risk_components)

    fusion = jury.get("fusion") or {}
    majority = fusion.get("majority_vote") or jury.get("majority_vote") or {}
    risk_score = float(
        fusion.get("fused_risk_score")
        or fusion.get("risk_score")
        or risk_cal.get("final_fraud_confidence")
        or 0
    )
    if risk_score > 1:
        risk_score /= 100.0

    if risk_score >= 0.70:
        verdict = "Fraudulent"
    elif risk_score >= 0.40:
        verdict = "Suspicious"
    else:
        verdict = "Authentic"

    explanation = fusion.get("reasoning") or (
        f"Judge Agent calibrated multi-agent confidence. "
        f"Final fraud confidence {calibration.get('final_percent')}%. "
        f"Verdict: {verdict}."
    )

    return AgentResult(
        agent_id="judge",
        agent_name="Judge Agent",
        status="completed",
        confidence=float(calibration.get("final_fraud_confidence") or 0.7),
        risk_score=risk_score,
        verdict=verdict,
        findings=[
            f"Verdict: {verdict}",
            f"Calibrated confidence: {calibration.get('final_percent')}%",
            f"Component scores: {calibration.get('components')}",
        ],
        executed_modules=["weighted_voting", "confidence_calibration"],
        data={
            "jury": jury,
            "calibration": calibration,
            "risk_calibration": risk_cal,
            "majority_vote": majority,
            "explanation": explanation,
            "human_readable": explanation,
            "supporting_modules": [
                aid for aid, r in agent_outputs.items() if r.status == "completed"
            ],
        },
        duration_ms=(time.perf_counter() - t0) * 1000,
        reason=explanation,
    )


def run_report_writer_agent(
    evidence_id: str,
    analysis_dir: Path,
    judge: AgentResult,
    timeline: List[Dict[str, Any]],
) -> AgentResult:
    t0 = time.perf_counter()
    try:
        from backend.pipeline.report_manager import generate_reports

        meta = generate_reports(evidence_id, background=True)
        status = "completed"
        reason = "Report Writer queued executive/technical/court/JSON/PDF/HTML generation."
        data = {"report_manager": meta, "download_urls": {
            "pdf": f"/api/report/{evidence_id}/download?format=pdf",
            "executive": f"/api/report/{evidence_id}/download?format=pdf&template=executive",
            "court": f"/api/report/{evidence_id}/download?format=pdf&template=court",
            "json": f"/api/report/{evidence_id}/download?format=json",
            "html": f"/api/report/{evidence_id}/download?format=html",
        }}
    except Exception as exc:
        logger.exception("Report writer failed: %s", exc)
        status = "failed"
        reason = str(exc)[:500]
        data = {}

    return AgentResult(
        agent_id="report",
        agent_name="Report Writer Agent",
        status=status,
        confidence=0.9 if status == "completed" else 0.0,
        risk_score=judge.risk_score,
        verdict=judge.verdict,
        findings=[
            "Executive / Technical / Court / JSON / HTML reports requested.",
            f"Judge verdict carried into reports: {judge.verdict}",
        ],
        executed_modules=["pdf", "html", "json", "docx"],
        data={**data, "timeline": timeline},
        duration_ms=(time.perf_counter() - t0) * 1000,
        reason=reason,
        error=reason if status == "failed" else None,
    )
