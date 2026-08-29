"""
Investigation pipeline facade — stable entry for API layer.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from backend.agents.investigation.chief import run_chief_investigation
from backend.evidence.paths import find_evidence_file, get_analysis_dir
from backend.utils.progress import ProgressBus

logger = logging.getLogger("ai_forge.pipelines.investigation")


def investigate_evidence(
    evidence_id: str,
    *,
    force_deep: bool = False,
    reference_signature: Optional[str] = None,
) -> Dict[str, Any]:
    progress = ProgressBus.create(evidence_id)
    progress.emit("chief_investigator", "running")
    try:
        result = run_chief_investigation(
            evidence_id,
            force_deep=force_deep,
            progress=progress,
            reference_signature=Path(reference_signature) if reference_signature else None,
        )
        try:
            from backend.services.forensic_findings_service import get_or_build_forensic_findings
            canonical = get_or_build_forensic_findings(
                evidence_id, get_analysis_dir(evidence_id)
            )
            result["canonical_findings"] = canonical.get("findings") or []
            result["findings_summary"] = canonical.get("summary") or {}
        except Exception as exc:
            logger.warning("Investigation finding projection failed for %s: %s", evidence_id, exc)
        progress.complete({"verdict": result.get("verdict")})
        return result
    except Exception as exc:
        progress.fail(str(exc))
        raise


def load_investigation(evidence_id: str) -> Optional[Dict[str, Any]]:
    import json

    path = get_analysis_dir(evidence_id, create=False) / "investigation.json"
    if not path.is_file():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            result = json.load(f)
        try:
            from backend.services.forensic_findings_service import get_or_build_forensic_findings
            canonical = get_or_build_forensic_findings(evidence_id, path.parent)
            result["canonical_findings"] = canonical.get("findings") or []
            result["findings_summary"] = canonical.get("summary") or {}
        except Exception:
            pass
        return result
    except (json.JSONDecodeError, OSError):
        return None
