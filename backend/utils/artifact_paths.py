"""
Canonical forensic artifact paths and API URLs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

# Standard artifact filenames inside analysis/{evidence_id}/
ARTIFACT_FILES: Dict[str, str] = {
    "ela": "ela.png",
    "edges": "edges.png",
    "wavelet": "wavelet.png",
    "copy_move": "copymove.png",
}

# Legacy jpg names (backward compatibility for old analyses)
LEGACY_SUFFIXES: Dict[str, str] = {
    "ela": "_ela.jpg",
    "edges": "_edges.jpg",
    "wavelet": "_wavelet.jpg",
    "copy_move": "_copy_move.jpg",
}


def artifact_path(analysis_dir: Path, artifact_type: str) -> Path:
    """Canonical on-disk path for an artifact."""
    filename = ARTIFACT_FILES.get(artifact_type)
    if not filename:
        raise ValueError(f"Unknown artifact type: {artifact_type}")
    return Path(analysis_dir) / filename


def resolve_artifact_path(
    analysis_dir: Path,
    artifact_type: str,
    upload_stem: str | None = None,
) -> Path:
    """Resolve artifact path — canonical first, then legacy."""
    canonical = artifact_path(analysis_dir, artifact_type)
    if canonical.exists():
        return canonical

    if upload_stem:
        legacy = analysis_dir / f"{upload_stem}{LEGACY_SUFFIXES.get(artifact_type, '')}"
        if legacy.exists():
            return legacy

    return canonical


def artifact_api_urls(evidence_id: str) -> Dict[str, str]:
    """Always-return API URLs for all forensic artifacts."""
    base = f"/api/evidence/artifacts/{evidence_id}"
    return {
        "ela": f"{base}/ela",
        "edges": f"{base}/edges",
        "wavelet": f"{base}/wavelet",
        "copy_move": f"{base}/copy_move",
    }
