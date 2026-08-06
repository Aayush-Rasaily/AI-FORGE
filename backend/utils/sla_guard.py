"""SLA timing guard — logs warnings when pipelines exceed targets."""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Generator

from backend.utils.performance_config import SLA_IMAGE_SEC, SLA_PDF_SEC, SLA_VIDEO_SEC

logger = logging.getLogger("ai_forge.sla")

_SLA_MAP = {
    "image": SLA_IMAGE_SEC,
    "document": SLA_PDF_SEC,
    "pdf": SLA_PDF_SEC,
    "video": SLA_VIDEO_SEC,
}


@contextmanager
def sla_timer(pipeline: str, evidence_id: str = "") -> Generator[None, None, None]:
    target = _SLA_MAP.get(pipeline, 30.0)
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        tag = f"[{evidence_id}] " if evidence_id else ""
        if elapsed > target:
            logger.warning(
                "%sSLA exceeded for %s: %.2fs > %.1fs target",
                tag, pipeline, elapsed, target,
            )
        else:
            logger.info("%s%s pipeline completed in %.2fs (SLA %.1fs)", tag, pipeline, elapsed, target)
