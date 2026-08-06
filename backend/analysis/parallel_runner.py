"""
Parallel execution of independent forensic modules.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, Optional, Set

from backend.utils.timing import ModuleTimer

logger = logging.getLogger("ai_forge.parallel")

ProgressCallback = Optional[Callable[[str, str, float], None]]


def run_parallel_modules(
    tasks: Dict[str, Callable[[], Any]],
    max_workers: int = 8,
    timer: ModuleTimer | None = None,
    progress: ProgressCallback = None,
    enabled_modules: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """
    Execute independent forensic modules concurrently.

    Parameters
    ----------
    tasks : dict
        Mapping of module name -> callable returning result.
    max_workers : int
        Thread pool size.
    timer : ModuleTimer, optional
        Records per-module timing.

    Returns
    -------
    dict
        Module name -> result (empty dict on failure).
    """
    results: Dict[str, Any] = {}
    workers = min(max_workers, max(1, len(tasks)))

    filtered = {
        name: fn for name, fn in tasks.items()
        if enabled_modules is None or name in enabled_modules
    }

    for name in tasks:
        if name not in filtered:
            results[name] = {}
            if progress:
                progress(name, "skipped", 0.0)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        def _wrap(name: str, fn: Callable[[], Any]):
            def _run():
                if progress:
                    progress(name, "running", 0.0)
                start = __import__("time").perf_counter()
                try:
                    if timer:
                        with timer.track(name):
                            out = fn()
                    else:
                        out = fn()
                    elapsed = __import__("time").perf_counter() - start
                    if progress:
                        progress(name, "completed", elapsed)
                    return out
                except Exception as exc:
                    elapsed = __import__("time").perf_counter() - start
                    if progress:
                        progress(name, "failed", elapsed)
                    logger.error("Module %s failed: %s", name, exc)
                    return {}
            return _run

        future_map = {
            executor.submit(_wrap(name, fn)): name
            for name, fn in filtered.items()
        }

        for future in as_completed(future_map):
            name = future_map[future]
            try:
                results[name] = future.result()
            except Exception as exc:
                logger.error("Module %s failed: %s", name, exc)
                results[name] = {}

    return results
