"""
Video analysis API — uses parallel frame batch pipeline.
"""

from pathlib import Path
import shutil
import uuid
import asyncio
import logging

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Request

from backend.services.video_service import analyze_video_parallel
from backend.forensics.integration import on_evidence_uploaded
from backend.forensics.user_context import get_investigator
from backend.utils.progress import ProgressBus

logger = logging.getLogger("ai_forge.video_api")

router = APIRouter(
    prefix="/api/video",
    tags=["Video Analysis"]
)

UPLOAD_DIR = Path("data/temp/videos")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/analyze")
async def analyze_video_endpoint(
    request: Request,
    file: UploadFile = File(...),
    job_id: str | None = Query(None, description="Client job ID for SSE progress"),
):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No video uploaded"
        )

    extension = Path(file.filename).suffix
    video_id = job_id or str(uuid.uuid4())

    video_path = UPLOAD_DIR / f"{video_id}{extension}"

    with open(video_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    investigator = get_investigator(request)
    forensic = on_evidence_uploaded(
        video_id,
        video_path,
        original_filename=file.filename,
        media_type="video",
        investigator=investigator,
    )

    analysis_dir = UPLOAD_DIR / "analysis" / video_id
    progress = ProgressBus.create(video_id)

    try:
        result = await asyncio.to_thread(
            analyze_video_parallel,
            str(video_path),
            str(analysis_dir),
            12,
            progress,
            True,
            video_id,
        )
        progress.complete({"video_id": video_id})

        try:
            from backend.pipeline.report_manager import persist_analysis_payload, generate_reports
            from backend.evidence.paths import get_analysis_dir
            import json as _json
            import shutil as _shutil

            # Mirror analysis into canonical analysis dir for report pipeline
            canonical = get_analysis_dir(video_id, create=True)
            persist_analysis_payload(video_id, result if isinstance(result, dict) else {"result": result}, kind="video")
            if analysis_dir.exists() and analysis_dir.resolve() != canonical.resolve():
                for src in analysis_dir.glob("*"):
                    if src.is_file():
                        dest = canonical / src.name
                        if not dest.exists():
                            _shutil.copy2(src, dest)
            generate_reports(video_id, background=True)
            logger.info("video_report_queued | evidence_id=%s", video_id)
        except Exception as report_exc:
            logger.warning("video_report_queue_failed | evidence_id=%s | error=%s", video_id, report_exc)

        return {
            "success": True,
            "video_id": video_id,
            "evidence_id": video_id,
            "job_id": video_id,
            "hashes": forensic.get("hashes"),
            "analysis": result,
            "reports_pending": True,
            "report_status": "queued",
        }
    except Exception as exc:
        progress.fail(str(exc))
        logger.exception("Video analysis failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
