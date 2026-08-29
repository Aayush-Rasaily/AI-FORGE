"""
Forensic artifact pipeline — always produces output images with placeholders on failure.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Optional

from backend.utils.artifact_paths import (
    ARTIFACT_FILES,
    artifact_api_url,
    artifact_api_urls,
    artifact_path,
    resolve_artifact_path,
)
from backend.utils.artifact_visualization import create_placeholder

logger = logging.getLogger("ai_forge.artifacts")

ARTIFACT_STATUS_FILE = "artifact_status.json"
ARTIFACT_TYPES = (
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


def _write_status(analysis_dir: Path, status: str, artifacts: Optional[Dict] = None) -> None:
    path = analysis_dir / ARTIFACT_STATUS_FILE
    payload = {"status": status, "artifacts": artifacts or artifact_api_urls("")}
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except OSError as exc:
        logger.warning("Could not write artifact status: %s", exc)


def get_artifact_status(analysis_dir: Path) -> Dict:
    path = analysis_dir / ARTIFACT_STATUS_FILE
    if not path.exists():
        return {"status": "pending", "artifacts": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"status": "unknown", "artifacts": {}}


def get_artifact_registry(analysis_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Return normalized availability metadata for canonical artifacts.

    The status file stores API URLs while the pipeline route needs both
    availability and metadata. Resolve each artifact against the canonical,
    legacy, and vault locations so callers never depend on one disk layout.
    """
    analysis_dir = Path(analysis_dir)
    status = get_artifact_status(analysis_dir)
    stored = status.get("artifacts") if isinstance(status, dict) else {}
    stored = stored if isinstance(stored, dict) else {}
    registry: Dict[str, Dict[str, Any]] = {}

    for artifact_type in ARTIFACT_FILES:
        path = resolve_artifact_path(
            analysis_dir.name,
            artifact_type,
            analysis_dir=analysis_dir,
        )
        previous = stored.get(artifact_type)
        previous = previous if isinstance(previous, dict) else {}
        available = bool(path and path.is_file() and path.stat().st_size > 0)
        registry[artifact_type] = {
            "available": available,
            "artifact_path": artifact_api_url(analysis_dir.name, artifact_type)
            if available
            else None,
            "disk_path": str(path.resolve()) if available and path else None,
            "score": previous.get("score"),
            "confidence": previous.get("confidence"),
            "explanation": previous.get("explanation", ""),
        }
    return registry


def _generate_ela(image_path: str, out_path: Path) -> str:
    from backend.utils.artifact_visualization import load_bgr, render_ela_heatmap
    from backend.analysis.ela import generate_ela, calculate_ela_score
    import numpy as np
    from PIL import Image

    ela_pil = generate_ela(image_path, str(out_path.with_suffix(".tmp.jpg")))
    original = load_bgr(image_path)
    ela_arr = np.asarray(ela_pil.convert("L"))
    if original is not None:
        viz = render_ela_heatmap(original, ela_arr)
        import cv2
        cv2.imwrite(str(out_path), viz)
    else:
        ela_pil.save(str(out_path))
    return str(out_path.resolve())


def _generate_edges(image_path: str, out_path: Path) -> str:
    from backend.utils.artifact_visualization import load_bgr, render_edge_overlay
    from backend.analysis.edge_detection import analyze_edges
    import cv2
    import tempfile

    tmp = out_path.with_suffix(".tmp.jpg")
    analyze_edges(image_path, str(tmp))
    original = load_bgr(image_path)
    edges = cv2.imread(str(tmp), cv2.IMREAD_GRAYSCALE)
    if original is not None and edges is not None:
        viz = render_edge_overlay(original, edges)
        cv2.imwrite(str(out_path), viz)
    elif edges is not None:
        cv2.imwrite(str(out_path), edges)
    tmp.unlink(missing_ok=True)
    return str(out_path.resolve())


def _generate_wavelet(image_path: str, out_path: Path) -> str:
    from backend.utils.artifact_visualization import load_bgr, render_wavelet_heatmap
    from backend.analysis.wavelet_analysis import analyze_wavelet
    import cv2

    tmp = out_path.with_suffix(".tmp.jpg")
    analyze_wavelet(image_path, str(tmp))
    original = load_bgr(image_path)
    wmap = cv2.imread(str(tmp), cv2.IMREAD_GRAYSCALE)
    if original is not None and wmap is not None:
        viz = render_wavelet_heatmap(original, wmap)
        cv2.imwrite(str(out_path), viz)
    elif wmap is not None:
        cv2.imwrite(str(out_path), wmap)
    tmp.unlink(missing_ok=True)
    return str(out_path.resolve())


def _generate_copy_move(image_path: str, out_path: Path, analysis_dir: Path) -> str:
    # Skip re-detection if artifact already exists
    if out_path.exists() and out_path.stat().st_size > 0:
        return str(out_path.resolve())

    canonical = analysis_dir / "copymove.png"
    if canonical.exists() and canonical.stat().st_size > 0:
        import shutil
        shutil.copy2(canonical, out_path)
        return str(out_path.resolve())

    from backend.analysis.copy_move import detect_copy_move
    result = detect_copy_move(image_path, output_dir=analysis_dir)
    artifact = result.get("artifact")
    if artifact and Path(artifact).exists():
        if Path(artifact).resolve() != out_path.resolve():
            import shutil
            shutil.copy2(artifact, out_path)
        return str(out_path.resolve())
    raise FileNotFoundError("Copy-move artifact not produced")


def _generate_noise(image_path: str, out_path: Path) -> str:
    from backend.utils.artifact_visualization import load_bgr, render_noise_heatmap
    import cv2
    import numpy as np

    original = load_bgr(image_path)
    if original is not None:
        gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
        denoised = cv2.medianBlur(gray, 3)
        noise = cv2.absdiff(gray, denoised)
        viz = render_noise_heatmap(original, noise)
        cv2.imwrite(str(out_path), viz)
        return str(out_path.resolve())
    raise FileNotFoundError("Image load failed for noise map")


def _generate_localization_artifact(artifact_type: str, image_path: str, out_path: Path, analysis_dir: Path) -> str:
    from backend.analysis.forgery_localization import build_forgery_localization
    import shutil

    evidence_id = analysis_dir.name
    res = build_forgery_localization(evidence_id, image_path=Path(image_path), analysis_dir=analysis_dir)
    target_files = {
        "heatmap": analysis_dir / "localization_heatmap.png",
        "forgery_mask": analysis_dir / "forgery_mask.png",
        "mask": analysis_dir / "forgery_mask.png",
        "bounding_boxes": analysis_dir / "localization_annotated.png",
        "difference": analysis_dir / "localization_diff.png",
        "difference_image": analysis_dir / "localization_diff.png",
    }
    src = target_files.get(artifact_type)
    if src and src.exists() and src.stat().st_size > 0:
        if src.resolve() != out_path.resolve():
            shutil.copy2(src, out_path)
        return str(out_path.resolve())
    raise FileNotFoundError(f"Localization artifact {artifact_type} not produced")


def _safe_generate(
    artifact_type: str,
    image_path: str,
    analysis_dir: Path,
) -> str:
    out_path = artifact_path(analysis_dir, artifact_type)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        if artifact_type == "ela":
            return _generate_ela(image_path, out_path)
        if artifact_type == "edges":
            return _generate_edges(image_path, out_path)
        if artifact_type == "wavelet":
            return _generate_wavelet(image_path, out_path)
        if artifact_type == "copy_move":
            return _generate_copy_move(image_path, out_path, analysis_dir)
        if artifact_type == "noise":
            return _generate_noise(image_path, out_path)
        if artifact_type in ("heatmap", "forgery_mask", "mask", "bounding_boxes", "difference", "difference_image"):
            return _generate_localization_artifact(artifact_type, image_path, out_path, analysis_dir)
    except Exception as exc:
        logger.warning("Artifact %s failed: %s — creating placeholder", artifact_type, exc)
        labels = {
            "ela": ("ELA Analysis", f"Module error: {exc}"),
            "edges": ("Edge Detection", f"Module error: {exc}"),
            "wavelet": ("Wavelet Analysis", f"Module error: {exc}"),
            "copy_move": ("Copy-Move Detection", f"Module error: {exc}"),
            "noise": ("Noise Analysis", f"Module error: {exc}"),
            "heatmap": ("Heatmap Overlay", f"Module error: {exc}"),
            "forgery_mask": ("Localization Mask", f"Module error: {exc}"),
            "bounding_boxes": ("Bounding Boxes", f"Module error: {exc}"),
            "difference": ("Difference Image", f"Module error: {exc}"),
        }
        title, msg = labels.get(artifact_type, ("Forensic Module", str(exc)))
        return create_placeholder(out_path, title, msg)

    return create_placeholder(out_path, artifact_type.upper(), "Artifact visualization ready.")


def generate_all_forensic_artifacts(
    evidence_id: str,
    image_path: Path,
    analysis_dir: Path,
    tampering: dict | None = None,
) -> Dict[str, str]:
    """Generate all four forensic artifacts in parallel. Never fails entirely."""
    analysis_dir = Path(analysis_dir)
    analysis_dir.mkdir(parents=True, exist_ok=True)
    img_str = str(image_path)
    api_urls = artifact_api_urls(evidence_id)
    disk_paths: Dict[str, str] = {}

    _write_status(analysis_dir, "generating", api_urls)

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(_safe_generate, atype, img_str, analysis_dir): atype
            for atype in ARTIFACT_TYPES
        }
        for future in as_completed(futures):
            atype = futures[future]
            try:
                disk_paths[atype] = future.result()
            except Exception as exc:
                logger.error("[%s] Artifact %s failed completely: %s", evidence_id, atype, exc)
                disk_paths[atype] = _safe_generate(atype, img_str, analysis_dir)

    _write_status(analysis_dir, "ready", api_urls)
    logger.info("[%s] All artifacts generated: %s", evidence_id, list(disk_paths.keys()))
    return api_urls


def generate_artifact(
    evidence_id: str,
    image_path: Path,
    analysis_dir: Path,
    artifact_type: str,
    tampering: dict | None = None,
) -> str:
    """Generate a single artifact on demand."""
    path = _safe_generate(artifact_type, str(image_path), Path(analysis_dir))
    status = get_artifact_status(analysis_dir)
    artifacts = status.get("artifacts", {})
    artifacts.update(artifact_api_urls(evidence_id))
    _write_status(Path(analysis_dir), "partial", artifacts)
    return path


generate_background_artifacts = generate_all_forensic_artifacts
