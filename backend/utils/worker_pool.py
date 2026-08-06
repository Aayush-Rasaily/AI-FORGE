"""
Shared thread pool for CPU-bound forensic work.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor

_CPU_COUNT = os.cpu_count() or 4
_MAX_WORKERS = min(12, max(4, _CPU_COUNT))

_POOL: ThreadPoolExecutor | None = None


def get_worker_pool() -> ThreadPoolExecutor:
    global _POOL
    if _POOL is None:
        _POOL = ThreadPoolExecutor(
            max_workers=_MAX_WORKERS,
            thread_name_prefix="ai_forge_worker",
        )
    return _POOL


def shutdown_pool() -> None:
    global _POOL
    if _POOL is not None:
        _POOL.shutdown(wait=False, cancel_futures=True)
        _POOL = None
