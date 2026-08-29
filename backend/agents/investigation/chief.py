"""
Chief Investigator Agent — autonomous investigation orchestration.

Evidence → Plan → Specialists → Correlation → Reasoning → Judge → Report
"""

from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.agents.investigation.base import AgentResult, TimelineEvent, utc_now
from backend.agents.investigation.correlation import correlate_evidence
from backend.agents.investigation.planner import run_planner_agent
from backend.agents.investigation.reasoning import (
    run_judge_agent,
    run_reasoning_agent,
    run_report_writer_agent,
)
from backend.agents.investigation.specialists import (
    run_document_agent,
    run_image_forensics_agent,
    run_metadata_cross_agent,
    run_signature_forensics_agent,
    run_video_agent,
)
from backend.evidence.paths import find_evidence_file, get_analysis_dir

logger = logging.getLogger("ai_forge.agents.chief")


def _emit(timeline: List[Dict], stage: str, agent: Optional[str], status: str, message: str, duration_ms=None):
    ev = TimelineEvent(stage=stage, agent=agent, status=status, message=message, duration_ms=duration_ms)
    timeline.append(ev.to_dict())
    logger.info("Investigation | %s | %s | %s", stage, agent or "-", message)


def _save_investigation(analysis_dir: Path, payload: Dict[str, Any]) -> None:
    analysis_dir.mkdir(parents=True, exist_ok=True)
    path = analysis_dir / "investigation.json"
    tmp = path.with_suffix(".tmp")
    from backend.document_analysis.evidence_fusion import make_json_serializable
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(make_json_serializable(payload), f, indent=2, default=str)
    if path.exists():
        path.unlink(missing_ok=True)
    tmp.replace(path)


def run_chief_investigation(
    evidence_id: str,
    *,
    evidence_path: Optional[Path] = None,
    force_deep: bool = False,
    progress=None,
    reference_signature: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Autonomous investigation entrypoint.
    Reuses existing forensic services — does not replace them.
    """
    started = time.perf_counter()
    timeline: List[Dict[str, Any]] = []
    agents: Dict[str, AgentResult] = {}

    path = Path(evidence_path) if evidence_path else find_evidence_file(evidence_id)
    if path is None or not Path(path).is_file():
        raise FileNotFoundError(f"Evidence not found: {evidence_id}")
    path = Path(path)
    analysis_dir = get_analysis_dir(evidence_id, create=True)

    _emit(timeline, "intake", "chief", "started", f"Chief Investigator started for {evidence_id}")

    # 1. Planner
    planner = run_planner_agent(evidence_id, path, force_deep=force_deep)
    agents["planner"] = planner
    plan_dict = (planner.data or {}).get("plan") or {}
    from backend.agents.investigation.base import InvestigationPlan

    plan = InvestigationPlan(
        evidence_id=evidence_id,
        evidence_type=plan_dict.get("evidence_type", "unknown"),
        profile=plan_dict.get("profile", "unknown"),
        modules=list(plan_dict.get("modules") or []),
        agents=list(plan_dict.get("agents") or []),
        skip_reasons=dict(plan_dict.get("skip_reasons") or {}),
        priorities=list(plan_dict.get("priorities") or []),
        estimated_seconds=float(plan_dict.get("estimated_seconds") or 10),
    )
    _emit(
        timeline,
        "planning",
        "planner",
        "completed",
        f"Plan ready — type={plan.evidence_type}, modules={len(plan.modules)}",
        planner.duration_ms,
    )

    # 2. Specialist agents (parallel where independent)
    specialist_jobs = {}
    if "image" in plan.agents:
        specialist_jobs["image"] = lambda: run_image_forensics_agent(
            evidence_id, path, analysis_dir, plan, progress=progress, force_deep=force_deep
        )
    if "document" in plan.agents:
        specialist_jobs["document"] = lambda: run_document_agent(
            evidence_id, path, analysis_dir, plan, progress=progress
        )
    if "video" in plan.agents:
        specialist_jobs["video"] = lambda: run_video_agent(evidence_id, path, analysis_dir, plan)
    if "signature" in plan.agents:
        specialist_jobs["signature"] = lambda: run_signature_forensics_agent(
            evidence_id, path, plan, reference_path=reference_signature
        )

    _emit(timeline, "agents", "chief", "running", f"Dispatching {len(specialist_jobs)} specialist agent(s)")

    with ThreadPoolExecutor(max_workers=max(1, len(specialist_jobs))) as pool:
        futures = {pool.submit(fn): name for name, fn in specialist_jobs.items()}
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                res = fut.result()
            except Exception as exc:
                res = AgentResult(
                    agent_id=name,
                    agent_name=f"{name.title()} Agent",
                    status="failed",
                    error=str(exc)[:500],
                )
            agents[name] = res
            _emit(
                timeline,
                "agent",
                name,
                res.status,
                res.reason or res.error or f"{res.agent_name} {res.status}",
                res.duration_ms,
            )

    import gc
    gc.collect()

    image_data = (agents.get("image").data if agents.get("image") else None) or {}
    document_data = ((agents.get("document").data or {}).get("document_analysis") if agents.get("document") else None)
    video_data = ((agents.get("video").data or {}).get("video_analysis") if agents.get("video") else None)
    signature_data = ((agents.get("signature").data or {}).get("signature_result") if agents.get("signature") else None)
    analysis = image_data.get("analysis") if isinstance(image_data, dict) else None
    tampering = image_data.get("tampering") if isinstance(image_data, dict) else None

    # 3. Metadata cross-agent
    meta = run_metadata_cross_agent(
        image_data=analysis,
        document_data=document_data if isinstance(document_data, dict) else None,
        video_data=video_data if isinstance(video_data, dict) else None,
        analysis=analysis if isinstance(analysis, dict) else None,
        tampering=tampering if isinstance(tampering, dict) else None,
    )
    agents["metadata"] = meta
    _emit(timeline, "agent", "metadata", meta.status, meta.reason or "Metadata cross-validation", meta.duration_ms)

    # 4. Correlation engine
    try:
        correlation = correlate_evidence(
            image_data=analysis if isinstance(analysis, dict) else None,
            document_data=document_data if isinstance(document_data, dict) else None,
            metadata_data=(meta.data or {}).get("metadata_agent"),
            video_data=video_data if isinstance(video_data, dict) else None,
            signature_data=signature_data if isinstance(signature_data, dict) else None,
        )
    except Exception as corr_exc:
        logger.exception("Correlation failed: %s", corr_exc)
        correlation = {
            "inconsistencies": [],
            "correlations": [],
            "cross_modal_summary": f"Correlation unavailable: {corr_exc}",
            "error": str(corr_exc)[:400],
        }
    _emit(
        timeline,
        "correlation",
        "correlation_engine",
        "completed",
        correlation.get("cross_modal_summary", "Correlation complete"),
    )

    # 5. Reasoning
    reasoning = run_reasoning_agent(agents, correlation)
    agents["reasoning"] = reasoning
    _emit(timeline, "reasoning", "reasoning", reasoning.status, reasoning.reason or "", reasoning.duration_ms)

    # 6. Judge
    judge = run_judge_agent(
        agents,
        analysis=analysis if isinstance(analysis, dict) else None,
        tampering=tampering if isinstance(tampering, dict) else None,
        document_analysis=document_data if isinstance(document_data, dict) else None,
        video_analysis=video_data if isinstance(video_data, dict) else None,
        signature_result=signature_data if isinstance(signature_data, dict) else None,
        evidence_id=evidence_id,
    )
    agents["judge"] = judge
    _emit(timeline, "judge", "judge", judge.status, f"Verdict: {judge.verdict}", judge.duration_ms)

    # 7. Report writer
    report = run_report_writer_agent(evidence_id, analysis_dir, judge, timeline)
    agents["report"] = report
    _emit(timeline, "report", "report", report.status, report.reason or "Reports queued", report.duration_ms)

    duration_ms = (time.perf_counter() - started) * 1000
    _emit(timeline, "complete", "chief", "completed", "Investigation complete", duration_ms)

    # Persist case memory + graph + knowledge (best-effort)
    try:
        from backend.memory.case_memory import remember_investigation
        from backend.graph.fraud_graph import upsert_investigation_graph
        from backend.knowledge.rag_store import index_investigation

        remember_investigation(evidence_id, judge, agents, correlation)
        upsert_investigation_graph(evidence_id, judge, agents, correlation)
        index_investigation(evidence_id, judge, reasoning, correlation)

        try:
            from backend.graph.case_correlation import build_case_correlation
            from backend.cases.case_service import _refresh_case_verdict
            from backend.database.repository import get_session, init_db
            from backend.forensics.models import EvidenceRegistry

            init_db()
            session = get_session()
            try:
                rec = session.query(EvidenceRegistry).filter_by(evidence_id=evidence_id).first()
                if rec and rec.investigation_id:
                    build_case_correlation(rec.investigation_id)
                    _refresh_case_verdict(rec.investigation_id)
            finally:
                session.close()
        except Exception as case_exc:
            logger.debug("Case graph update skipped: %s", case_exc)
    except Exception as mem_exc:
        logger.warning("Memory/graph/knowledge update skipped: %s", mem_exc)

    calibration = (judge.data or {}).get("calibration") or {}
    payload = {
        "success": True,
        "evidence_id": evidence_id,
        "status": "completed",
        "mode": "autonomous_investigation",
        "plan": plan.to_dict(),
        "verdict": judge.verdict,
        "risk_score": judge.risk_score,
        "confidence": judge.confidence,
        "confidence_calibration": calibration,
        "explanation": (judge.data or {}).get("human_readable") or judge.reason,
        "correlation": correlation,
        "agents": {k: v.to_dict() for k, v in agents.items()},
        "timeline": timeline,
        "jury": (judge.data or {}).get("jury"),
        "analysis": analysis,
        "tampering": tampering,
        "document_analysis": document_data,
        "video_analysis": video_data,
        "signature_result": signature_data,
        "download_urls": (report.data or {}).get("download_urls"),
        "reports_pending": True,
        "duration_ms": round(duration_ms, 1),
        "generated_at": utc_now(),
    }

    # Attach dashboard/completion if image path produced them
    completion = image_data.get("completion") if isinstance(image_data, dict) else None
    if isinstance(completion, dict):
        payload["dashboard"] = completion.get("dashboard")
        payload["artifacts"] = completion.get("artifacts")
        payload["risk"] = completion.get("risk") or {
            "score": judge.risk_score,
            "level": judge.verdict,
        }

    _save_investigation(analysis_dir, payload)
    logger.info(
        "Chief Investigator complete | evidence=%s verdict=%s duration_ms=%.0f",
        evidence_id,
        judge.verdict,
        duration_ms,
    )
    return payload
