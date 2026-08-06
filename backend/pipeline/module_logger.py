"""
Per-module pipeline logging — writes to logs/{evidence_id}.log
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

_logger = logging.getLogger("ai_forge.pipeline")


def log_module(
    evidence_id: str,
    module: str,
    status: str,
    *,
    duration_ms: Optional[float] = None,
    error: Optional[str] = None,
    extra: Optional[dict] = None,
) -> None:
    """Log module start/finish to file and Python logger."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "evidence_id": evidence_id,
        "module": module,
        "status": status,
        "duration_ms": round(duration_ms, 2) if duration_ms is not None else None,
        "success": status == "completed",
        "failure": status == "failed",
        "error": error,
        **(extra or {}),
    }

    level = logging.ERROR if status == "failed" else logging.INFO
    msg = f"[{evidence_id}] {module} {status}"
    if duration_ms is not None:
        msg += f" ({duration_ms:.0f}ms)"
    if error:
        msg += f" — {error}"
    _logger.log(level, msg)

    log_file = LOG_DIR / f"{evidence_id}.log"
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except OSError as exc:
        _logger.warning("Could not write pipeline log: %s", exc)
