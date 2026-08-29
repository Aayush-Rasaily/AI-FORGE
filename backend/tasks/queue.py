"""
Redis job queue for long-running forensic analysis.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from backend.security.config import QUEUE_ENABLED

logger = logging.getLogger("ai_forge.tasks.queue")

JOB_QUEUE = "aiforge:jobs"
JOB_STATUS_PREFIX = "aiforge:job:"
JOB_TTL_SEC = 86400


def _redis():
    from backend.utils.redis_cache import _get_redis
    return _get_redis()


def enqueue_job(job_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Push job to Redis queue. Falls back to sync marker when Redis unavailable."""
    job_id = f"JOB-{uuid.uuid4().hex[:12]}"
    job = {
        "job_id": job_id,
        "type": job_type,
        "payload": payload,
        "status": "queued",
        "created_at": time.time(),
    }

    client = _redis()
    if client and QUEUE_ENABLED:
        try:
            client.lpush(JOB_QUEUE, json.dumps(job, default=str))
            client.setex(f"{JOB_STATUS_PREFIX}{job_id}", JOB_TTL_SEC, json.dumps(job, default=str))
            logger.info("Enqueued job %s type=%s", job_id, job_type)
            return job
        except Exception as exc:
            logger.warning("Queue enqueue failed: %s", exc)

    job["status"] = "inline"
    return job


def dequeue_job(timeout: int = 5) -> Optional[Dict[str, Any]]:
    client = _redis()
    if not client:
        return None
    try:
        result = client.brpop(JOB_QUEUE, timeout=timeout)
        if not result:
            return None
        _, raw = result
        job = json.loads(raw)
        job["status"] = "processing"
        job["started_at"] = time.time()
        client.setex(
            f"{JOB_STATUS_PREFIX}{job['job_id']}",
            JOB_TTL_SEC,
            json.dumps(job, default=str),
        )
        return job
    except Exception as exc:
        logger.warning("Queue dequeue failed: %s", exc)
        return None


def update_job_status(job_id: str, status: str, result: Optional[Dict[str, Any]] = None) -> None:
    client = _redis()
    if not client:
        return
    key = f"{JOB_STATUS_PREFIX}{job_id}"
    try:
        raw = client.get(key)
        job = json.loads(raw) if raw else {"job_id": job_id}
        job["status"] = status
        job["updated_at"] = time.time()
        if result is not None:
            job["result"] = result
        client.setex(key, JOB_TTL_SEC, json.dumps(job, default=str))
    except Exception as exc:
        logger.warning("Job status update failed: %s", exc)


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    client = _redis()
    if not client:
        return None
    try:
        raw = client.get(f"{JOB_STATUS_PREFIX}{job_id}")
        return json.loads(raw) if raw else None
    except Exception:
        return None


def queue_depth() -> int:
    client = _redis()
    if not client:
        return 0
    try:
        return int(client.llen(JOB_QUEUE))
    except Exception:
        return 0
