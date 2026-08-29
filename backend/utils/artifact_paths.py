"""
Canonical forensic artifact paths and API URLs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.evidence.paths import (
    get_analysis_artifacts_dir,
    get_analysis_dir,
    get_evidence_artifacts_dir,
)

# Standard artifact filenames (canonical keys → on-disk name)
ARTIFACT_FILES: Dict[str, str] = {
    "ela": "ela.png",
    "edges": "edges.png",
    "wavelet": "wavelet.png",
    "copy_move": "copymove.png",
    "noise": "noise.png",
    "heatmap": "heatmap.png",
    "localization": "localization.png",
    "forgery_mask": "forgery_mask.png",
    "bounding_boxes": "bounding_boxes.png",
    "difference": "difference.png",
    "metadata": "metadata_overlay.png",
    "ocr": "ocr_regions.png",
    "gradcam": "gradcam.png",
    "attention": "attention.png",
    "shap": "shap.png",
    "lime": "lime.png",
    "segmentation_mask": "segmentation_mask.png",
    "segmentation_heatmap": "segmentation_heatmap.png",
    "segmentation_overlay": "segmentation_overlay.png",
    "copymove_localization": "copymove_localization.png",
    "signature_localization": "signature_localization.png",
    "text_modification_report": "text_modification_report.json",
    "phase6_bundle": "phase6_localization.json",
    "fused_heatmap": "fused_heatmap.png",
    "evidence_localization": "evidence_localization.json",
    "localization_overlay": "localization_overlay.png",
    "localization_mask": "localization_mask.png",
    "forensic_heatmap": "forensic_heatmap.png",
    "combined_overlay": "combined_overlay.png",
    "localization_summary": "localization_summary.json",
    "investigation_summary": "investigation_summary.json",
    "explainable_ai": "explainable_ai.json",
    "forensic_narrative": "forensic_narrative.json",
    "ocr_difference_report": "ocr_difference_report.json",
}

# API-served artifact types (includes aliases)
SERVED_ARTIFACT_TYPES: List[str] = list(ARTIFACT_FILES.keys())

# Legacy jpg names (backward compatibility for old analyses)
LEGACY_SUFFIXES: Dict[str, str] = {
    "ela": "_ela.jpg",
    "edges": "_edges.jpg",
    "wavelet": "_wavelet.jpg",
    "copy_move": "_copy_move.jpg",
    "noise": "_noise.jpg",
    "heatmap": "_heatmap.jpg",
}

ARTIFACT_REGISTRY_FILE = "artifact_registry.json"
ARTIFACT_STATUS_FILE = "artifact_status.json"

_MIN_BYTES = 500
_MIN_BYTES_JSON = 32


def _min_bytes_for(path: Path) -> int:
    if path.suffix.lower() == ".json":
        return _MIN_BYTES_JSON
    return _MIN_BYTES


def artifacts_dirs(evidence_id: str, *, create: bool = True) -> tuple[Path, Path]:
    """Return (vault_artifacts_dir, analysis_artifacts_dir)."""
    return (
        get_evidence_artifacts_dir(evidence_id, create=create),
        get_analysis_artifacts_dir(evidence_id, create=create),
    )


def artifact_filename(artifact_type: str) -> str:
    return ARTIFACT_FILES.get(artifact_type) or f"{artifact_type}.png"


def artifact_path(analysis_dir: Path, artifact_type: str) -> Path:
    """Canonical on-disk path inside analysis artifacts subfolder."""
    return Path(analysis_dir) / "artifacts" / artifact_filename(artifact_type)


def vault_artifact_path(evidence_id: str, artifact_type: str) -> Path:
    """Production vault path: data/evidence/<id>/artifacts/<file>."""
    return get_evidence_artifacts_dir(evidence_id, create=False) / artifact_filename(artifact_type)


def legacy_root_artifact_path(analysis_dir: Path, artifact_type: str) -> Path:
    """Legacy flat layout at analysis root (pre-artifacts/ subfolder)."""
    return Path(analysis_dir) / artifact_filename(artifact_type)


def resolve_artifact_path(
    evidence_id: str | Path,
    artifact_type: str,
    analysis_dir: Optional[Path] = None,
    upload_stem: str | None = None,
) -> Optional[Path]:
    """
    Resolve artifact path — vault first, then analysis artifacts/, then legacy root.
    Returns None when no valid file exists. Robust to parameter ordering.
    """
    if isinstance(evidence_id, Path) or (
        isinstance(evidence_id, str) and ("/" in evidence_id or "\\" in evidence_id or evidence_id.startswith("data"))
    ):
        if analysis_dir is None:
            analysis_dir = Path(evidence_id)
        elif upload_stem is None and isinstance(analysis_dir, str):
            upload_stem = str(analysis_dir)
            analysis_dir = Path(evidence_id)
        evidence_id = analysis_dir.name

    evidence_id_str = str(evidence_id)
    analysis_dir = Path(analysis_dir) if analysis_dir else get_analysis_dir(evidence_id_str, create=False)

    candidates: List[Path] = [
        vault_artifact_path(evidence_id_str, artifact_type),
        artifact_path(analysis_dir, artifact_type),
        legacy_root_artifact_path(analysis_dir, artifact_type),
    ]

    if upload_stem:
        legacy = analysis_dir / f"{upload_stem}{LEGACY_SUFFIXES.get(artifact_type, '')}"
        candidates.append(legacy)

    # Localization / explainability fallbacks at analysis root
    root_aliases = {
        "localization": analysis_dir / "localization_heatmap.png",
        "forgery_mask": analysis_dir / "forgery_mask.png",
        "mask": analysis_dir / "forgery_mask.png",
        "heatmap": analysis_dir / "heatmap.png",
        "bounding_boxes": analysis_dir / "localization_annotated.png",
        "annotated": analysis_dir / "localization_annotated.png",
        "difference": analysis_dir / "localization_diff.png",
        "difference_image": analysis_dir / "localization_diff.png",
        "highlight": analysis_dir / "localization_highlight.png",
        "polygons": analysis_dir / "localization_polygons.png",
        "attention": analysis_dir / "localization_attention.png",
        "noise": analysis_dir / "noise.png",
        "gradcam": analysis_dir / "explainability" / "gradcam_overlay.jpg",
        "attention_overlay": analysis_dir / "explainability" / "attention_overlay.jpg",
        "shap": analysis_dir / "explainability" / "shap_overlay.jpg",
        "lime": analysis_dir / "explainability" / "lime_overlay.jpg",
        "fused_heatmap": analysis_dir / "explainability" / "fused_suspicious_overlay.jpg",
        "localization_overlay": analysis_dir / "localization_overlay.png",
        "localization_mask": analysis_dir / "localization_mask.png",
        "forensic_heatmap": analysis_dir / "forensic_heatmap.png",
        "combined_overlay": analysis_dir / "combined_overlay.png",
        "localization_summary": analysis_dir / "localization_summary.json",
        "investigation_summary": analysis_dir / "investigation_summary.json",
        "explainable_ai": analysis_dir / "explainable_ai.json",
        "forensic_narrative": analysis_dir / "forensic_narrative.json",
    }
    if artifact_type in root_aliases:
        candidates.append(root_aliases[artifact_type])

    for path in candidates:
        if path.is_file() and path.stat().st_size >= _min_bytes_for(path):
            return path
    return None


def artifact_is_available(path: Optional[Path]) -> bool:
    if path is None or not path.is_file():
        return False
    return path.stat().st_size >= _min_bytes_for(path)


def artifact_api_url(evidence_id: str, artifact_type: str) -> str:
    return f"/api/evidence/artifacts/{evidence_id}/{artifact_type}"


def artifact_api_urls(evidence_id: str) -> Dict[str, str]:
    """Always-return API URLs for all forensic artifacts."""
    return {key: artifact_api_url(evidence_id, key) for key in ARTIFACT_FILES}


def build_registry_entry(
    evidence_id: str,
    artifact_type: str,
    path: Optional[Path],
    *,
    score: Any = None,
    confidence: Any = None,
    explanation: str = "",
) -> Dict[str, Any]:
    available = artifact_is_available(path)
    return {
        "score": score,
        "confidence": confidence,
        "explanation": explanation or "",
        "artifact_path": artifact_api_url(evidence_id, artifact_type) if available else None,
        "disk_path": str(path.resolve()) if available and path else None,
        "available": available,
    }
