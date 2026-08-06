"""
Analysis result caching per evidence_id.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("ai_forge.cache")

CACHE_FILENAME = "analysis.json"


class AnalysisCache:
    """Load/save cached analysis results for an evidence item."""

    def __init__(self, evidence_id: str, analysis_dir: Path):
        self.evidence_id = evidence_id
        self.analysis_dir = Path(analysis_dir)
        self.cache_path = self.analysis_dir / CACHE_FILENAME

    def exists(self) -> bool:
        return self.cache_path.is_file()

    def load(self) -> Optional[Dict[str, Any]]:
        if not self.exists():
            return None
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info("Cache hit for evidence %s", self.evidence_id)
            return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Cache read failed for %s: %s", self.evidence_id, exc)
            return None

    def save(self, data: Dict[str, Any]) -> None:
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "evidence_id": self.evidence_id,
            "cached": True,
            **data,
        }
        try:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, default=str)
            logger.info("Cache saved for evidence %s", self.evidence_id)
        except OSError as exc:
            logger.warning("Cache write failed for %s: %s", self.evidence_id, exc)
