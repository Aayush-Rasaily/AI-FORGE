"""
Job queue status API.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.security.dependencies import AuthUser, get_current_user
from backend.tasks.queue import get_job_status, queue_depth

router = APIRouter(prefix="/api/jobs", tags=["Job Queue"])


@router.get("/{job_id}")
async def job_status(job_id: str, user: AuthUser = Depends(get_current_user)):
    status = get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"success": True, **status}


@router.get("")
async def queue_stats(user: AuthUser = Depends(get_current_user)):
    return {"success": True, "queue_depth": queue_depth()}
