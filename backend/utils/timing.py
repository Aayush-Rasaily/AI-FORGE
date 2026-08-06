"""
Execution timing utilities for forensic modules.
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Dict, List, Optional

logger = logging.getLogger("ai_forge.timing")


class ModuleTimer:
    """Track and log per-module execution times."""

    def __init__(self, pipeline_name: str = "pipeline"):
        self.pipeline_name = pipeline_name
        self._start = time.perf_counter()
        self.records: List[Dict[str, float]] = []

    def record(self, module: str, elapsed: float) -> None:
        self.records.append({"module": module, "elapsed": elapsed})

    @contextmanager
    def track(self, module: str):
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            self.record(module, elapsed)

    def total(self) -> float:
        return time.perf_counter() - self._start

    def log_summary(self, highlight_threshold: float = 0.5) -> Dict[str, float]:
        """Print and return timing summary."""
        summary: Dict[str, float] = {}
        lines = [f"\n--- {self.pipeline_name} Timing ---"]

        for rec in self.records:
            name = rec["module"]
            elapsed = rec["elapsed"]
            summary[name] = round(elapsed, 3)
            flag = " ⚠ SLOW" if elapsed >= highlight_threshold else ""
            lines.append(f"{name:.<20} {elapsed:.2f}s{flag}")

        total = self.total()
        summary["total"] = round(total, 3)
        lines.append(f"{'Total':.<20} {total:.2f}s")
        lines.append("---")

        message = "\n".join(lines)
        logger.info(message)
        print(message)
        return summary


def format_timing_dashboard(timing: Dict[str, float]) -> str:
    """Human-readable timing dashboard for API responses."""
    if not timing:
        return "No timing data."
    lines = []
    total = timing.get("total", 0.0)
    for key, val in sorted(timing.items()):
        if key == "total":
            continue
        lines.append(f"{key:.<20} {val:.2f} sec")
    lines.append(f"{'Total':.<20} {total:.2f} sec")
    return "\n".join(lines)
