"""
Per-analysis deduplication context — avoids duplicate work within one pipeline run.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Callable, Dict, Optional

_ctx: ContextVar[Optional[Dict[str, Any]]] = ContextVar("analysis_dedup", default=None)
_lock = threading.Lock()


class AnalysisDedup:
    """Thread-safe memoization for expensive intermediate results."""

    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def get_or_compute(self, key: str, factory: Callable[[], Any]) -> Any:
        with self._lock:
            if key in self._store:
                return self._store[key]
        result = factory()
        with self._lock:
            self._store[key] = result
        return result

    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = value


def get_dedup() -> AnalysisDedup:
    dedup = _ctx.get()
    if dedup is None:
        dedup = AnalysisDedup()
        _ctx.set(dedup)
    return dedup


@contextmanager
def dedup_context():
    """Context manager for scoped deduplication."""
    token = _ctx.set(AnalysisDedup())
    try:
        yield get_dedup()
    finally:
        _ctx.reset(token)
