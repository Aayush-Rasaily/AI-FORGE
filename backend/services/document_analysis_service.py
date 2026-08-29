"""
Production document analysis — hash cache, DB persistence, progress streaming.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from backend.database.repository import get_analysis_by_hash, save_analysis_record
from backend.services.document_service import analyze_document
from backend.utils.cache import AnalysisCache
from backend.utils.file_hash import compute_file_hash
from backend.utils.image_utils import validate_path
from backend.utils.progress import ProgressBus, ProgressTracker
from backend.forensics.integration import on_analysis_complete
from backend.utils.redis_cache import cache_key, get_redis_cache
from backend.utils.sla_guard import sla_timer
from backend.utils.timing import ModuleTimer

logger = logging.getLogger("ai_forge.document_service")


def _ensure_document_tampering(
    result: Dict[str, Any],
    analysis_dir: Path,
    evidence_id: str,
) -> Dict[str, Any]:
    tampering = result.get("document_tampering")
    if not isinstance(tampering, dict):
        from backend.services.document_tampering_service import build_document_tampering

        tampering = build_document_tampering(
            result,
            analysis_dir=analysis_dir,
            evidence_id=evidence_id,
        )
        result["document_tampering"] = tampering
    return tampering


def _ensure_document_localization(
    result: Dict[str, Any],
    analysis_dir: Path,
    evidence_id: str,
) -> Dict[str, Any]:
    localization = result.get("evidence_localization")
    if isinstance(localization, dict) and localization.get("regions") is not None:
        return localization
    page_images = {
        int(page.get("page_number") or index): page["image"]
        for index, page in enumerate(result.get("pages") or [], start=1)
        if isinstance(page, dict) and page.get("image")
    }
    if not page_images:
        return {}
    from backend.services.professional_localization_service import (
        build_professional_localization,
    )

    localization = build_professional_localization(
        evidence_id,
        analysis_dir,
        image_paths=page_images,
        analysis=result,
    )
    result["evidence_localization"] = localization
    return localization


def _ensure_document_narrative(
    result: Dict[str, Any],
    analysis_dir: Path,
    evidence_id: str,
) -> Dict[str, Any]:
    from backend.services.explainable_narrative_service import (
        build_explainable_narrative,
    )

    narrative = build_explainable_narrative(
        evidence_id,
        analysis_dir,
        analysis=result,
    )
    result["explainable_ai"] = narrative
    return narrative


def _ensure_document_jury(
    analysis_dir: Path,
    evidence_id: str,
) -> Dict[str, Any]:
    from backend.services.dossier_jury_service import run_dossier_jury

    return run_dossier_jury(evidence_id, analysis_dir)


def run_document_analysis(
    document_path: Path,
    analysis_dir: Path,
    evidence_id: str,
    use_cache: bool = True,
    progress: Optional[ProgressTracker] = None,
) -> Tuple[Dict[str, Any], Dict[str, float], bool]:
    """
    Analyze PDF/DOCX with layered caching and profiling.

    Returns (analysis_result, timing_summary, from_cache).
    """
    document_path = validate_path(document_path)
    if progress is None:
        progress = ProgressBus.get(evidence_id)

    file_hash = compute_file_hash(document_path)

    redis = get_redis_cache()
    rkey = cache_key("document", file_hash)
    if use_cache:
        redis_cached = redis.get(rkey)
        if redis_cached and redis_cached.get("document_analysis"):
            result = redis_cached["document_analysis"]
            _ensure_document_tampering(result, analysis_dir, evidence_id)
            _ensure_document_localization(result, analysis_dir, evidence_id)
            _ensure_document_narrative(result, analysis_dir, evidence_id)
            _ensure_document_jury(analysis_dir, evidence_id)
            if progress:
                progress.emit("cache", "completed", extra={"source": "redis"})
                progress.complete({"cached": True})
            return (
                result,
                redis_cached.get("timing", {}),
                True,
            )

    if use_cache:
        db_cached = get_analysis_by_hash(file_hash, "document")
        if db_cached:
            result = db_cached["analysis"]
            _ensure_document_tampering(result, analysis_dir, evidence_id)
            _ensure_document_localization(result, analysis_dir, evidence_id)
            _ensure_document_narrative(result, analysis_dir, evidence_id)
            _ensure_document_jury(analysis_dir, evidence_id)
            if progress:
                progress.emit("cache", "completed", extra={"source": "database"})
                progress.complete({"cached": True})
            return (
                result,
                db_cached.get("execution_times", {}),
                True,
            )

    cache = AnalysisCache(evidence_id, analysis_dir)
    if use_cache:
        cached = cache.load()
        if cached and cached.get("document_analysis"):
            result = cached["document_analysis"]
            _ensure_document_tampering(result, analysis_dir, evidence_id)
            _ensure_document_localization(result, analysis_dir, evidence_id)
            _ensure_document_narrative(result, analysis_dir, evidence_id)
            _ensure_document_jury(analysis_dir, evidence_id)
            if progress:
                progress.emit("cache", "completed")
                progress.complete({"cached": True})
            return result, cached.get("timing", {}), True

    timer = ModuleTimer("Document Analysis")
    if progress:
        progress.emit("pipeline", "running")

    with sla_timer("document", evidence_id):
        with timer.track("document_analysis"):
            result = analyze_document(
                str(document_path),
                evidence_id,
                progress=progress,
            )

    timing = {**timer.log_summary(), **(result.pop("timing", {}) or {})}
    result["file_hash"] = file_hash
    result["timing"] = timing
    _ensure_document_tampering(result, analysis_dir, evidence_id)
    _ensure_document_localization(result, analysis_dir, evidence_id)
    _ensure_document_narrative(result, analysis_dir, evidence_id)
    _ensure_document_jury(analysis_dir, evidence_id)

    cache.save({"document_analysis": result, "timing": timing})
    redis.set(rkey, {"document_analysis": result, "timing": timing})
    _persist(evidence_id, file_hash, document_path, result, timing)

    on_analysis_complete(evidence_id, result, media_type="document", execution_times=timing)

    if progress:
        progress.complete({"cached": False})

    return result, timing, False


def _persist(
    evidence_id: str,
    file_hash: str,
    document_path: Path,
    result: Dict[str, Any],
    timing: Dict[str, float],
) -> None:
    try:
        save_analysis_record(
            record_id=str(uuid.uuid4()),
            file_hash=file_hash,
            media_type="document",
            analysis=result,
            evidence_id=evidence_id,
            filename=document_path.name,
            execution_times=timing,
            deep_scan=True,
        )
    except Exception as exc:
        logger.warning("DB persist failed: %s", exc)
