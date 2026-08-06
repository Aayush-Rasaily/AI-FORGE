"""
SSE progress streaming and job status endpoints.
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.utils.progress import ProgressBus, stream_progress_events

logger = logging.getLogger("ai_forge.progress_api")

router = APIRouter(prefix="/api/progress", tags=["progress"])


@router.get("/stream/{job_id}")
async def stream_analysis_progress(job_id: str):
    """Server-Sent Events stream for module-by-module analysis progress."""
    # Wait for analysis job to be registered (client may connect before POST)
    for _ in range(60):
        if ProgressBus.get(job_id):
            break
        await asyncio.sleep(0.1)
    else:
        raise HTTPException(
            status_code=404,
            detail="Analysis job not found. Start analysis first.",
        )

    return StreamingResponse(
        stream_progress_events(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/status/{job_id}")
async def get_analysis_progress(job_id: str):
    """Polling fallback — current progress snapshot."""
    tracker = ProgressBus.get(job_id)
    if not tracker:
        raise HTTPException(status_code=404, detail="Job not found.")
    return {"success": True, **tracker.snapshot()}
