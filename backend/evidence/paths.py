"""
Unified evidence path resolution — original, working, analysis (backward compatible).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

# Legacy paths (preserved for existing APIs)
LEGACY_UPLOAD_DIR = Path("data/temp/uploads")
LEGACY_ANALYSIS_ROOT = LEGACY_UPLOAD_DIR / "analysis"

# Production evidence vault
EVIDENCE_ROOT = Path("data/evidence")
ORIGINAL_DIR = EVIDENCE_ROOT / "original"
WORKING_DIR = EVIDENCE_ROOT / "working"
ANALYSIS_DIR = EVIDENCE_ROOT / "analysis"

for d in (LEGACY_UPLOAD_DIR, LEGACY_ANALYSIS_ROOT, ORIGINAL_DIR, WORKING_DIR, ANALYSIS_DIR):
    d.mkdir(parents=True, exist_ok=True)


def get_analysis_dir(evidence_id: str, *, create: bool = True) -> Path:
    """Primary analysis output directory (legacy path — used by all existing APIs)."""
    path = LEGACY_ANALYSIS_ROOT / evidence_id
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def get_metadata_path(evidence_id: str) -> Path:
    return get_analysis_dir(evidence_id) / "metadata.json"


def find_original_evidence(evidence_id: str) -> Optional[Path]:
    """Locate immutable original — vault first, then legacy upload."""
    for base in (ORIGINAL_DIR, LEGACY_UPLOAD_DIR):
        matches = [f for f in base.glob(f"{evidence_id}.*") if f.is_file()]
        if matches:
            return matches[0]
    return None


def find_working_evidence(evidence_id: str) -> Optional[Path]:
    """Locate working copy for forensic modules."""
    matches = [f for f in WORKING_DIR.glob(f"{evidence_id}.*") if f.is_file()]
    if matches:
        return matches[0]
    return find_original_evidence(evidence_id)


def find_evidence_file(evidence_id: str) -> Optional[Path]:
    """Backward-compatible evidence lookup."""
    return find_working_evidence(evidence_id) or find_original_evidence(evidence_id)
