"""
WebSocket real-time progress — complements existing SSE without breaking it.
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.utils.progress import ProgressBus

logger = logging.getLogger("ai_forge.ws")

router = APIRouter(tags=["WebSocket"])


@router.websocket("/api/ws/progress/{job_id}")
async def websocket_progress(websocket: WebSocket, job_id: str):
    await websocket.accept()

    for _ in range(60):
        if ProgressBus.get(job_id):
            break
        await asyncio.sleep(0.1)
    else:
        await websocket.send_json({"error": "Job not found", "job_id": job_id})
        await websocket.close()
        return

    tracker = ProgressBus.get(job_id)
    last_count = 0

    try:
        while True:
            if not tracker:
                break

            snap = tracker.snapshot()
            events = snap.get("events", [])
            if len(events) > last_count:
                for ev in events[last_count:]:
                    await websocket.send_json({"type": "progress", **ev})
                last_count = len(events)

            status = snap.get("status", "running")
            await websocket.send_json({
                "type": "heartbeat",
                "status": status,
                "completed_modules": snap.get("completed_modules", 0),
                "total_modules": snap.get("total_modules", 0),
            })

            if status in ("completed", "failed"):
                await websocket.send_json({"type": "done", "status": status, "result": snap.get("result")})
                break

            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        logger.debug("WebSocket disconnected: %s", job_id)
    except Exception as exc:
        logger.warning("WebSocket error: %s", exc)
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
