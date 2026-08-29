"""Base utilities for segmentation providers."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np

from backend.analysis.localization.contracts import SegmentationOutput

logger = logging.getLogger("ai_forge.localization.providers")

MODELS_ROOT = Path("backend/models/localization")


def load_bgr(image_path: str, max_side: int = 1536) -> Optional[np.ndarray]:
    img = cv2.imread(str(image_path))
    if img is None:
        return None
    h, w = img.shape[:2]
    if max(h, w) > max_side:
        scale = max_side / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return img


def normalize_map(m: np.ndarray) -> np.ndarray:
    m = np.nan_to_num(m, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
    lo, hi = float(m.min()), float(m.max())
    if hi - lo < 1e-6:
        return np.zeros_like(m)
    return (m - lo) / (hi - lo)


def save_segmentation_artifacts(
    output_dir: Path,
    prefix: str,
    heatmap: np.ndarray,
    mask: np.ndarray,
    original_bgr: np.ndarray,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    heat_u8 = (np.clip(heatmap, 0, 1) * 255).astype(np.uint8)
    colored = cv2.applyColorMap(heat_u8, cv2.COLORMAP_JET)
    overlay = cv2.addWeighted(original_bgr, 0.55, colored, 0.45, 0)

    paths = {
        "heatmap": str((output_dir / f"{prefix}_confidence_heatmap.png").resolve()),
        "mask": str((output_dir / f"{prefix}_mask.png").resolve()),
        "overlay": str((output_dir / f"{prefix}_overlay.png").resolve()),
    }
    cv2.imwrite(paths["heatmap"], colored)
    cv2.imwrite(paths["mask"], mask)
    cv2.imwrite(paths["overlay"], overlay)
    return paths


def build_output(
    provider: str,
    heatmap: np.ndarray,
    mask: np.ndarray,
    score: float,
    confidence: float,
    explanation: str,
    artifact_paths: dict,
) -> SegmentationOutput:
    return SegmentationOutput(
        provider=provider,
        confidence_heatmap=heatmap,
        binary_mask=mask,
        score=score,
        confidence=confidence,
        explanation=explanation,
        available=True,
        artifact_paths=artifact_paths,
    )


def try_load_torch_weights(weights_path: Path) -> bool:
    return weights_path.is_file() and weights_path.stat().st_size > 10_000
