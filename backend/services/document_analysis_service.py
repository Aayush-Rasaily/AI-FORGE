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
            if progress:
                progress.emit("cache", "completed", extra={"source": "redis"})
                progress.complete({"cached": True})
            return (
                redis_cached["document_analysis"],
                redis_cached.get("timing", {}),
                True,
            )

    if use_cache:
        db_cached = get_analysis_by_hash(file_hash, "document")
        if db_cached:
            if progress:
                progress.emit("cache", "completed", extra={"source": "database"})
                progress.complete({"cached": True})
            return (
                db_cached["analysis"],
                db_cached.get("execution_times", {}),
                True,
            )

    cache = AnalysisCache(evidence_id, analysis_dir)
    if use_cache:
        cached = cache.load()
        if cached and cached.get("document_analysis"):
            if progress:
                progress.emit("cache", "completed")
                progress.complete({"cached": True})
            return cached["document_analysis"], cached.get("timing", {}), True

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
