"""
Evidence Router — dispatch by media type to existing production pipelines.

Does not reimplement detectors; routes to image / document / video services.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from backend.utils.module_registry import get_file_category

logger = logging.getLogger("ai_forge.engines.router")


def route_evidence(
    path: Path,
    *,
    evidence_id: str,
    analysis_dir: Path,
    progress=None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Route evidence to the correct pipeline. Returns a normalized envelope:
      { media_type, evidence_id, analysis, ... }
    """
    category = get_file_category(Path(path))
    logger.info("route_evidence | id=%s | category=%s", evidence_id, category)

    if category == "image":
        from backend.services.image_analysis_service import run_image_analysis

        analysis, tampering, timing, cached, completion = run_image_analysis(
            Path(path),
            Path(analysis_dir),
            evidence_id,
            progress=progress,
            **{k: v for k, v in kwargs.items() if k in ("use_cache", "force_deep", "defer_artifacts")},
        )
        return {
            "media_type": "image",
            "evidence_id": evidence_id,
            "analysis": analysis,
            "tampering": tampering,
            "timing": timing,
            "cached": cached,
            "completion": completion,
        }

    if category == "document":
        from backend.services.document_analysis_service import run_document_analysis

        analysis, timing, cached = run_document_analysis(
            Path(path),
            Path(analysis_dir),
            evidence_id,
            progress=progress,
            **{k: v for k, v in kwargs.items() if k in ("use_cache",)},
        )
        return {
            "media_type": "document",
            "evidence_id": evidence_id,
            "analysis": analysis if isinstance(analysis, dict) else {"raw": analysis},
            "timing": timing,
            "cached": cached,
        }

    if category == "video":
        from backend.services.video_service import analyze_video_parallel

        result = analyze_video_parallel(
            str(path),
            str(analysis_dir),
            progress=progress,
            video_id=evidence_id,
            **{k: v for k, v in kwargs.items() if k in ("use_cache", "max_frames")},
        )
        return {
            "media_type": "video",
            "evidence_id": evidence_id,
            "analysis": result if isinstance(result, dict) else {"raw": result},
        }

    raise ValueError(f"Unsupported evidence category for {path}: {category}")
