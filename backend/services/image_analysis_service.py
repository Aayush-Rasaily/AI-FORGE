"""
Production image analysis pipeline — two-stage scan, hash cache, DB persistence.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from backend.analysis.unified_image_analysis import analyze_image_unified
from backend.database.repository import get_analysis_by_hash, save_analysis_record
from backend.services.artifact_service import generate_all_forensic_artifacts
from backend.services.quick_scan import build_quick_verdict, run_quick_scan
from backend.utils.artifact_paths import artifact_api_urls
from backend.utils.cache import AnalysisCache
from backend.utils.analysis_persistence import load_analysis_bundle, save_analysis_bundle
from backend.utils.file_hash import compute_file_hash
from backend.utils.image_utils import is_image_file, prepare_working_image, validate_path
from backend.pipeline.completion import ensure_pipeline_complete, build_standard_response
from backend.forensics.integration import on_analysis_complete
from backend.utils.performance_config import DEFER_EXPLAINABILITY
from backend.utils.progress import ProgressBus, ProgressTracker
from backend.utils.redis_cache import cache_key, get_redis_cache
from backend.utils.sla_guard import sla_timer
from backend.utils.timing import ModuleTimer, format_timing_dashboard

logger = logging.getLogger("ai_forge.image_service")


def _attach_artifacts(result: Dict[str, Any], evidence_id: str) -> Dict[str, Any]:
    """Always include API artifact URLs in the response."""
    result["artifacts"] = artifact_api_urls(evidence_id)
    result["artifacts_pending"] = True
    return result


def run_image_analysis(
    image_path: Path,
    analysis_dir: Path,
    evidence_id: str,
    use_cache: bool = True,
    progress: Optional[ProgressTracker] = None,
    force_deep: bool = False,
    defer_artifacts: bool = False,
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, float], bool, Dict[str, Any]]:
    image_path = validate_path(image_path)
    original_path = image_path

    if not is_image_file(image_path):
        raise ValueError(f"Not an image file: {image_path.suffix}")

    if progress is None:
        progress = ProgressBus.get(evidence_id)

    file_hash = compute_file_hash(image_path)

    redis = get_redis_cache()
    rkey = cache_key("image", file_hash)
    if use_cache:
        redis_cached = redis.get(rkey)
        if redis_cached and redis_cached.get("analysis"):
            analysis = redis_cached["analysis"]
            tampering = redis_cached.get("tampering", {})
            timing = redis_cached.get("timing", {})
            completion = ensure_pipeline_complete(
                evidence_id, image_path, analysis_dir, analysis, tampering, timing, progress=progress
            )
            if progress:
                progress.emit("cache", "completed", extra={"source": "redis"})
                progress.complete({"cached": True})
            return analysis, tampering, timing, True, completion

    if use_cache:
        db_cached = get_analysis_by_hash(file_hash, "image")
        if db_cached:
            analysis = db_cached["analysis"]
            tampering = db_cached["tampering"]
            timing = db_cached.get("execution_times", {})
            completion = ensure_pipeline_complete(
                evidence_id, image_path, analysis_dir, analysis, tampering, timing, progress=progress
            )
            if progress:
                progress.emit("cache", "completed", extra={"source": "database"})
                progress.complete({"cached": True})
            return analysis, tampering, timing, True, completion

    cache = AnalysisCache(evidence_id, analysis_dir)
    if use_cache:
        bundle = load_analysis_bundle(analysis_dir)
        if bundle and bundle.get("analysis"):
            analysis = bundle["analysis"]
            tampering = bundle.get("tampering") or _extract_tampering(analysis)
            timing = bundle.get("timing", {})
            completion = ensure_pipeline_complete(
                evidence_id, image_path, analysis_dir, analysis, tampering, timing, progress=progress
            )
            if progress:
                progress.emit("cache", "completed")
                progress.complete({"cached": True})
            return analysis, tampering, timing, True, completion

        cached = cache.load()
        if cached and cached.get("analysis"):
            analysis = cached["analysis"]
            tampering = cached.get("tampering") or _extract_tampering(analysis)
            timing = cached.get("timing", {})
            completion = ensure_pipeline_complete(
                evidence_id, image_path, analysis_dir, analysis, tampering, timing, progress=progress
            )
            if progress:
                progress.emit("cache", "completed")
                progress.complete({"cached": True})
            return analysis, tampering, timing, True, completion

    timer = ModuleTimer("Image Analysis")
    all_timing: Dict[str, float] = {}

    with sla_timer("image", evidence_id):
        with timer.track("prepare_image"):
            if progress:
                progress.emit("prepare_image", "running")
            working_path, _ = prepare_working_image(image_path, analysis_dir)
            if progress:
                progress.emit("prepare_image", "completed")

        with timer.track("quick_scan"):
            if progress:
                progress.emit("quick_scan", "running")
            quick = run_quick_scan(working_path)
            all_timing.update(quick.get("timing", {}))
            if progress:
                progress.emit("quick_scan", "completed")

        run_deep = force_deep or quick.get("needs_deep_scan", True)

        if not run_deep and quick.get("authentic_likely"):
            result = build_quick_verdict(quick)
            result["file_hash"] = file_hash
            result["evidence_id"] = evidence_id
            tampering = _minimal_tampering(quick)
            timing = {**timer.log_summary(), **all_timing}
            _persist(evidence_id, file_hash, original_path, analysis_dir, result, tampering, timing, deep_scan=False, redis_key=rkey)
            completion = ensure_pipeline_complete(
                evidence_id, original_path, analysis_dir, result, tampering, timing, progress=progress
            )
            on_analysis_complete(evidence_id, result, media_type="image", execution_times=timing)
            if progress:
                progress.emit("pipeline", "completed", extra={"scan_mode": "quick"})
                progress.complete({"scan_mode": "quick"})
            return result, tampering, timing, False, completion

        with timer.track("deep_scan"):
            if progress:
                progress.emit("deep_scan", "running")
            result = analyze_image_unified(
                working_path, analysis_dir, progress=progress, evidence_id=evidence_id,
            )
            result["scan_mode"] = "deep"
            result["file_hash"] = file_hash
            result["evidence_id"] = evidence_id
            result["quick_scan"] = {"risk_score": quick["risk_score"], "signals": quick["signals"]}
            if progress:
                progress.emit("deep_scan", "completed")

        tampering = _extract_tampering(result)
        timing = {**timer.log_summary(), **all_timing}
        result["timing"] = timing
        result["timing_dashboard"] = format_timing_dashboard(timing)

        _persist(evidence_id, file_hash, original_path, analysis_dir, result, tampering, timing, deep_scan=True, redis_key=rkey)
        completion = ensure_pipeline_complete(
            evidence_id, original_path, analysis_dir, result, tampering, timing, progress=progress
        )
        on_analysis_complete(evidence_id, result, media_type="image", execution_times=timing)

        if progress:
            progress.complete({"scan_mode": "deep"})

        return result, tampering, timing, False, completion


def schedule_background_explainability(
    evidence_id: str,
    image_path: Path,
    analysis_dir: Path,
    result: Dict[str, Any],
    tampering: Dict[str, Any],
    redis_key: str,
) -> None:
    from backend.utils.worker_pool import get_worker_pool

    def _run():
        try:
            from backend.analysis.explainability.engine import run_explainability
            signals = result.get("signals") or {}
            evidence_list = result.get("evidence") or []
            explain = run_explainability(
                str(image_path),
                str(analysis_dir),
                context={
                    "verdict": result.get("verdict"),
                    "risk_score": result.get("risk_score", 0),
                    "confidence": result.get("confidence", 75),
                    "signals": signals,
                    "evidence": evidence_list,
                },
                tampering_result=tampering,
            )
            result["explainability"] = explain
            result["explainability_pending"] = False
            from backend.utils.analysis_persistence import save_analysis_bundle
            cached = AnalysisCache(evidence_id, analysis_dir).load() or {}
            save_analysis_bundle(
                analysis_dir,
                analysis=result,
                tampering=cached.get("tampering", tampering),
                timing=cached.get("timing", result.get("timing", {})),
                risk=result.get("risk_fusion"),
            )
            cache = AnalysisCache(evidence_id, analysis_dir)
            cache.save({
                "analysis": result,
                "tampering": cached.get("tampering", tampering),
                "timing": cached.get("timing", result.get("timing", {})),
            })
            get_redis_cache().set(redis_key, {
                "analysis": result,
                "tampering": tampering,
                "timing": result.get("timing", {}),
            })
            logger.info("[%s] Background explainability complete", evidence_id)
        except Exception as exc:
            logger.warning("[%s] Background explainability failed: %s", evidence_id, exc)

    get_worker_pool().submit(_run)


def schedule_background_artifacts(
    evidence_id: str,
    image_path: Path,
    analysis_dir: Path,
    tampering: Dict[str, Any],
) -> None:
    from backend.utils.worker_pool import get_worker_pool
    logger.info("[%s] Scheduling background artifact generation", evidence_id)
    get_worker_pool().submit(
        generate_all_forensic_artifacts,
        evidence_id,
        image_path,
        analysis_dir,
        tampering,
    )


def _persist(
    evidence_id: str,
    file_hash: str,
    image_path: Path,
    analysis_dir: Path,
    result: Dict[str, Any],
    tampering: Dict[str, Any],
    timing: Dict[str, float],
    deep_scan: bool,
    redis_key: Optional[str] = None,
) -> None:
    metadata = result.get("metadata_forensics") or {}
    risk = result.get("risk_fusion") or result.get("ensemble")

    save_analysis_bundle(
        analysis_dir,
        analysis=result,
        tampering=tampering,
        timing=timing,
        metadata=metadata if metadata else None,
        risk=risk,
    )

    cache = AnalysisCache(evidence_id, analysis_dir)
    payload = {"analysis": result, "tampering": tampering, "timing": timing}
    cache.save(payload)
    if redis_key:
        get_redis_cache().set(redis_key, payload)
    try:
        save_analysis_record(
            record_id=str(uuid.uuid4()),
            file_hash=file_hash,
            media_type="image",
            analysis=result,
            evidence_id=evidence_id,
            filename=image_path.name,
            tampering=tampering,
            execution_times=timing,
            deep_scan=deep_scan,
        )
    except Exception as exc:
        logger.warning("DB persist failed: %s", exc)


def _minimal_tampering(quick: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "success": True,
        "verdict": "NO_STRONG_TAMPERING_SIGNAL",
        "severity": "LOW",
        "tampering_score": quick["risk_score"],
        "confidence": quick["confidence"],
        "signals": ["Quick scan — deep tampering module skipped."],
        "analysis": {},
    }


def _extract_tampering(analysis: Dict[str, Any]) -> Dict[str, Any]:
    td = analysis.get("tampering_detection") or {}
    signals = analysis.get("signals") or {}
    return {
        "success": td.get("success", True),
        "verdict": td.get("verdict", signals.get("tampering_verdict", "UNKNOWN")),
        "severity": td.get("severity", signals.get("tampering_severity", "LOW")),
        "tampering_score": td.get("tampering_score", signals.get("tampering_score", 0)),
        "tampering_percentage": td.get("tampering_percentage", signals.get("tampering_percentage", 0)),
        "confidence": td.get("confidence", signals.get("tampering_confidence", 0)),
        "signals": td.get("signals", signals.get("tampering_signals", [])),
        "analysis": td.get("analysis", {}),
    }
