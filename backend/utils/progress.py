"""
Thread-safe progress tracking for streaming analysis updates to the frontend.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("ai_forge.progress")


class ProgressTracker:
    """Emit module-by-module progress events for a single analysis job."""

    def __init__(self, job_id: str):
        self.job_id = job_id
        self._lock = threading.Lock()
        self._events: List[Dict[str, Any]] = []
        self._subscribers: List[Callable[[Dict[str, Any]], None]] = []
        self._started = time.perf_counter()
        self._completed_modules: List[str] = []
        self._status = "running"

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        with self._lock:
            self._subscribers.append(callback)
            for event in self._events:
                callback(event)

    def emit(
        self,
        module: str,
        status: str,
        elapsed: Optional[float] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        event: Dict[str, Any] = {
            "job_id": self.job_id,
            "module": module,
            "status": status,
            "elapsed": round(elapsed or 0, 3),
            "timestamp": round(time.perf_counter() - self._started, 3),
        }
        if extra:
            event.update(extra)

        with self._lock:
            self._events.append(event)
            if status == "completed":
                if module not in self._completed_modules:
                    self._completed_modules.append(module)
            subscribers = list(self._subscribers)

        for cb in subscribers:
            try:
                cb(event)
            except Exception as exc:
                logger.warning("Progress subscriber error: %s", exc)

    def complete(self, payload: Optional[Dict[str, Any]] = None) -> None:
        self._status = "completed"
        self.emit("pipeline", "completed", extra=payload or {})

    def fail(self, error: str) -> None:
        self._status = "failed"
        self.emit("pipeline", "failed", extra={"error": error})

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "job_id": self.job_id,
                "status": self._status,
                "completed_modules": list(self._completed_modules),
                "events": list(self._events),
                "elapsed": round(time.perf_counter() - self._started, 3),
            }


class ProgressBus:
    """Global registry of active analysis jobs."""

    _trackers: Dict[str, ProgressTracker] = {}
    _lock = threading.Lock()

    @classmethod
    def create(cls, job_id: str) -> ProgressTracker:
        tracker = ProgressTracker(job_id)
        with cls._lock:
            cls._trackers[job_id] = tracker
        return tracker

    @classmethod
    def get(cls, job_id: str) -> Optional[ProgressTracker]:
        with cls._lock:
            return cls._trackers.get(job_id)

    @classmethod
    def remove(cls, job_id: str) -> None:
        with cls._lock:
            cls._trackers.pop(job_id, None)


async def stream_progress_events(job_id: str, timeout: float = 300.0):
    """Async generator yielding SSE-formatted progress events."""
    tracker = ProgressBus.get(job_id)
    if not tracker:
        yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
        return

    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def on_event(event: Dict[str, Any]):
        loop.call_soon_threadsafe(queue.put_nowait, event)

    tracker.subscribe(on_event)
    deadline = time.perf_counter() + timeout

    while time.perf_counter() < deadline:
        try:
            event = await asyncio.wait_for(queue.get(), timeout=2.0)
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("status") in ("completed", "failed") and event.get("module") == "pipeline":
                break
        except asyncio.TimeoutError:
            snap = tracker.snapshot()
            if snap["status"] in ("completed", "failed"):
                break
            yield f"data: {json.dumps({'module': 'heartbeat', 'status': 'running', 'elapsed': snap['elapsed']})}\n\n"
