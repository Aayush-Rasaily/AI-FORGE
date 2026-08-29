"""
Validate pipeline outputs — analysis vs reports.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from backend.utils.artifact_paths import ARTIFACT_FILES, resolve_artifact_path


class PipelineValidationError(Exception):
    def __init__(self, evidence_id: str, missing: List[str]):
        self.evidence_id = evidence_id
        self.missing = missing
        super().__init__(f"Pipeline incomplete for {evidence_id}: missing {', '.join(missing)}")


REQUIRED_ANALYSIS = ("analysis.json", "dashboard.json", "risk.json", "jury.json")
REQUIRED_ARTIFACT_TYPES = (
    "ela",
    "edges",
    "wavelet",
    "copy_move",
    "noise",
    "heatmap",
    "forgery_mask",
    "bounding_boxes",
    "difference",
)
REQUIRED_ARTIFACTS = tuple(ARTIFACT_FILES[name] for name in REQUIRED_ARTIFACT_TYPES)
REQUIRED_REPORTS = (
    "report.pdf",
    "report_executive.pdf",
    "report_court.pdf",
    "report_technical.pdf",
    "report.json",
    "report.html",
    "report.docx",
)


def validate_analysis_outputs(analysis_dir: Path, evidence_id: str) -> Dict[str, Any]:
    """Validate analysis + dashboard + artifacts (sync stage)."""
    analysis_dir = Path(analysis_dir)
    missing: List[str] = []

    for name in REQUIRED_ANALYSIS:
        if not (analysis_dir / name).is_file():
            missing.append(name)

    for artifact_type, name in zip(REQUIRED_ARTIFACT_TYPES, REQUIRED_ARTIFACTS):
        p = resolve_artifact_path(
            evidence_id,
            artifact_type,
            analysis_dir=analysis_dir,
        )
        if p is None or not p.is_file() or p.stat().st_size == 0:
            missing.append(name)

    if missing:
        raise PipelineValidationError(evidence_id, missing)

    return {"valid": True, "stage": "analysis", "missing": []}


def validate_reports(analysis_dir: Path, evidence_id: str) -> Dict[str, Any]:
    """Validate report files (async stage)."""
    analysis_dir = Path(analysis_dir)
    missing = [n for n in REQUIRED_REPORTS if not (analysis_dir / n).is_file()]
    return {
        "valid": len(missing) == 0,
        "stage": "reports",
        "missing": missing,
        "ready": len(missing) == 0,
    }


# Backward compat
def validate_pipeline(analysis_dir: Path, evidence_id: str) -> Dict[str, Any]:
    analysis = validate_analysis_outputs(analysis_dir, evidence_id)
    reports = validate_reports(analysis_dir, evidence_id)
    missing = reports.get("missing", [])
    if missing:
        raise PipelineValidationError(evidence_id, missing)
    return {**analysis, **reports}
