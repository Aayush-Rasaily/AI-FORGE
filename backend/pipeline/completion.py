"""
Pipeline completion — fast analysis return + background report generation.
"""

from __future__ import annotations

import json
import logging
import shutil
import time
from pathlib import Path
from typing import Any, Dict, Optional

from backend.agents.jury import run_jury_analysis
from backend.pipeline.dashboard_builder import build_dashboard, save_dashboard
from backend.pipeline.module_logger import log_module
from backend.pipeline.report_manager import generate_reports, write_status, read_status
from backend.pipeline.report_pipeline import generate_all_reports, get_report_status
from backend.pipeline.validator import validate_analysis_outputs, PipelineValidationError
from backend.services.artifact_service import generate_all_forensic_artifacts
from backend.utils.analysis_persistence import save_analysis_bundle
from backend.utils.artifact_paths import artifact_api_urls, ARTIFACT_FILES

logger = logging.getLogger("ai_forge.pipeline.completion")

REPORT_STATUS_FILE = "report_status.json"


def _save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    if path.exists():
        path.unlink(missing_ok=True)
    tmp.replace(path)


def _save_timeline_and_recommendation(
    analysis_dir: Path,
    timing: Dict[str, float],
    analysis: Dict[str, Any],
    dashboard: Dict[str, Any],
) -> None:
    timeline = dashboard.get("timeline") or []
    _save_json(analysis_dir / "timeline.json", {
        "events": timeline,
        "modules": timing,
        "generated_at": dashboard.get("generated_at"),
    })
    _save_json(analysis_dir / "recommendation.json", {
        "recommendation": analysis.get("recommendation", ""),
        "explanation": analysis.get("explanation", ""),
        "verdict": analysis.get("verdict"),
        "risk_score": analysis.get("risk_score"),
        "confidence": analysis.get("confidence"),
        "explainability": (analysis.get("risk_fusion") or {}).get("explainability", []),
    })


def _copy_heatmap(analysis_dir: Path) -> None:
    """Alias ELA artifact as heatmap.png for downstream consumers."""
    ela = analysis_dir / ARTIFACT_FILES["ela"]
    heatmap = analysis_dir / "heatmap.png"
    if ela.exists() and ela.stat().st_size > 0:
        try:
            shutil.copy2(ela, heatmap)
        except OSError as exc:
            logger.debug("Heatmap copy skipped: %s", exc)


def finalize_analysis_sync(
    evidence_id: str,
    image_path: Path,
    analysis_dir: Path,
    result: Dict[str, Any],
    tampering: Dict[str, Any],
    timing: Dict[str, float],
    *,
    progress=None,
) -> Dict[str, Any]:
    """
    Synchronous stage: artifacts → jury → dashboard → persist.
    Reports run in background afterward.
    """
    analysis_dir = Path(analysis_dir)
    image_path = Path(image_path)
    pipeline_start = time.perf_counter()
    warnings: list[str] = []

    # ── Artifacts (resilient — never abort pipeline) ─────────────────────
    log_module(evidence_id, "artifacts", "started")
    t0 = time.perf_counter()
    if progress:
        progress.emit("artifacts", "running")
    try:
        generate_all_forensic_artifacts(evidence_id, image_path, analysis_dir, tampering)
        log_module(evidence_id, "artifacts", "completed", duration_ms=(time.perf_counter() - t0) * 1000)
    except Exception as exc:
        warnings.append(f"artifacts: {exc}")
        log_module(evidence_id, "artifacts", "failed", duration_ms=(time.perf_counter() - t0) * 1000, error=str(exc))
    if progress:
        progress.emit("artifacts", "completed")

    result["artifacts"] = artifact_api_urls(evidence_id)
    result["artifacts_pending"] = False
    _copy_heatmap(analysis_dir)

    # ── AI Jury ──────────────────────────────────────────────────────────
    log_module(evidence_id, "jury", "started")
    t0 = time.perf_counter()
    if progress:
        progress.emit("jury", "running")
    jury_result: Dict[str, Any] = {}
    try:
        jury_result = run_jury_analysis(
            analysis=result,
            tampering=tampering,
            evidence_id=evidence_id,
            filename=image_path.name,
        )
        log_module(evidence_id, "jury", "completed", duration_ms=(time.perf_counter() - t0) * 1000)
    except Exception as exc:
        warnings.append(f"jury: {exc}")
        jury_result = {"success": False, "error": str(exc), "fusion": {}}
        log_module(evidence_id, "jury", "failed", duration_ms=(time.perf_counter() - t0) * 1000, error=str(exc))
    _save_json(analysis_dir / "jury.json", jury_result)
    if progress:
        progress.emit("jury", "completed")

    # ── Dashboard ──────────────────────────────────────────────────────
    log_module(evidence_id, "dashboard", "started")
    t0 = time.perf_counter()
    if progress:
        progress.emit("dashboard", "running")
    dashboard = build_dashboard(
        evidence_id, result, tampering, jury=jury_result, timing=timing, artifacts=result["artifacts"]
    )
    save_dashboard(analysis_dir, dashboard)
    _save_timeline_and_recommendation(analysis_dir, timing, result, dashboard)
    log_module(evidence_id, "dashboard", "completed", duration_ms=(time.perf_counter() - t0) * 1000)
    if progress:
        progress.emit("dashboard", "completed")

    # ── Persist analysis bundle ──────────────────────────────────────────
    risk = result.get("risk_fusion") or result.get("ensemble")
    save_analysis_bundle(
        analysis_dir,
        analysis=result,
        tampering=tampering,
        timing=timing,
        jury=jury_result,
        metadata=result.get("metadata_forensics"),
        risk=risk,
    )

    # Mark reports as pending (status.json + legacy report_status.json)
    write_status(analysis_dir, status="queued", progress=5, report_ready=False)
    _save_json(analysis_dir / REPORT_STATUS_FILE, {
        "status": "queued",
        "evidence_id": evidence_id,
        "files": {},
        "errors": {},
    })

    # Validate analysis outputs (not reports — those are async)
    try:
        validation = validate_analysis_outputs(analysis_dir, evidence_id)
    except PipelineValidationError as exc:
        log_module(evidence_id, "validation", "failed", error=str(exc))
        raise

    total_ms = (time.perf_counter() - pipeline_start) * 1000
    log_module(evidence_id, "analysis_sync", "completed", duration_ms=total_ms)

    return {
        "dashboard": dashboard,
        "artifacts": result["artifacts"],
        "report": {
            "status": "queued",
            "download_url": f"/api/report/{evidence_id}/download?format=pdf",
            "status_url": f"/api/report/{evidence_id}/status",
        },
        "jury": jury_result,
        "risk": result.get("risk_score", dashboard.get("risk_score", 0)),
        "confidence": result.get("confidence", dashboard.get("confidence", 0)),
        "processing_time_ms": round(total_ms, 2),
        "validation": validation,
        "warnings": warnings,
        "reports_pending": True,
    }


def schedule_background_reports(
    evidence_id: str,
    analysis_dir: Path,
    jury_data: Optional[Dict[str, Any]] = None,
) -> None:
    """Generate all report formats in background worker pool."""
    generate_reports(evidence_id, jury_data=jury_data, background=True)


def ensure_pipeline_complete(
    evidence_id: str,
    image_path: Path,
    analysis_dir: Path,
    result: Dict[str, Any],
    tampering: Dict[str, Any],
    timing: Dict[str, float],
    *,
    progress=None,
) -> Dict[str, Any]:
    """Ensure analysis outputs exist; schedule reports if missing."""
    analysis_dir = Path(analysis_dir)
    analysis_ready = (
        (analysis_dir / "analysis.json").is_file()
        and (analysis_dir / "dashboard.json").is_file()
        and (analysis_dir / "ela.png").is_file()
    )
    report_status = read_status(analysis_dir)
    legacy_status = get_report_status(analysis_dir)
    reports_ready = report_status.get("report_ready") or legacy_status.get("ready", False)

    if analysis_ready:
        dashboard = {}
        jury = {}
        dash_path = analysis_dir / "dashboard.json"
        jury_path = analysis_dir / "jury.json"
        if dash_path.exists():
            with open(dash_path, encoding="utf-8") as f:
                dashboard = json.load(f)
        if jury_path.exists():
            with open(jury_path, encoding="utf-8") as f:
                jury = json.load(f)
        result["artifacts"] = artifact_api_urls(evidence_id)
        result["artifacts_pending"] = False

        if not reports_ready:
            schedule_background_reports(evidence_id, analysis_dir, jury_data=jury)

        return {
            "dashboard": dashboard,
            "artifacts": result["artifacts"],
            "report": {
                "status": report_status.get("status", legacy_status.get("status", "generating")),
                "download_url": f"/api/report/{evidence_id}/download?format=pdf",
                "status_url": f"/api/report/{evidence_id}/status",
                "files": report_status.get("files", legacy_status.get("files", {})),
            },
            "jury": jury,
            "risk": result.get("risk_score", dashboard.get("risk_score", 0)),
            "confidence": result.get("confidence", dashboard.get("confidence", 0)),
            "processing_time_ms": 0,
            "cached": True,
            "reports_pending": not reports_ready,
        }

    completion = finalize_analysis_sync(
        evidence_id, image_path, analysis_dir, result, tampering, timing, progress=progress
    )
    schedule_background_reports(evidence_id, analysis_dir, jury_data=completion.get("jury"))
    return completion


# Backward-compatible alias
finalize_pipeline = finalize_analysis_sync


def build_standard_response(
    evidence_id: str,
    analysis: Dict[str, Any],
    tampering: Dict[str, Any],
    completion: Dict[str, Any],
    *,
    timing: Optional[Dict] = None,
    cached: bool = False,
    scan_mode: str = "deep",
) -> Dict[str, Any]:
    """Standard API envelope — backward compatible."""
    reports_pending = completion.get("reports_pending", True)
    report_info = completion.get("report", {})
    return {
        "success": True,
        "evidence_id": evidence_id,
        "job_id": evidence_id,
        "dashboard": completion.get("dashboard", {}),
        "artifacts": completion.get("artifacts", {}),
        "report": report_info,
        "jury": completion.get("jury", {}),
        "risk": completion.get("risk", analysis.get("risk_score", 0)),
        "confidence": completion.get("confidence", analysis.get("confidence", 0)),
        "processing_time": completion.get("processing_time_ms", 0),
        "analysis": analysis,
        "tampering": tampering,
        "timing": timing or analysis.get("timing", {}),
        "cached": cached,
        "artifacts_pending": False,
        "reports_pending": reports_pending,
        "report_status": report_info.get("status", "queued" if reports_pending else "completed"),
        "warnings": completion.get("warnings", []),
        "scan_mode": scan_mode,
        "pipeline_complete": not reports_pending,
    }
