"""
Professional forensic visualization helpers and failure placeholders.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger("ai_forge.artifact_viz")


def create_placeholder(
    output_path: Path,
    title: str,
    message: str,
    size: Tuple[int, int] = (800, 600),
) -> str:
    """Generate a placeholder image when a module fails."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    w, h = size
    canvas = np.zeros((h, w, 3), dtype=np.uint8)
    canvas[:] = (28, 32, 42)

    # Gradient header bar
    for y in range(60):
        alpha = y / 60.0
        canvas[y, :] = (
            int(20 + 30 * alpha),
            int(60 + 80 * alpha),
            int(100 + 100 * alpha),
        )

    cv2.putText(canvas, title, (24, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    cv2.putText(
        canvas, message[:80], (24, h // 2 - 10),
        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 190, 210), 1, cv2.LINE_AA,
    )
    cv2.putText(
        canvas, "AI-FORGE Forensic Placeholder", (24, h - 24),
        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 110, 130), 1,
    )

    cv2.imwrite(str(output_path), canvas)
    return str(output_path.resolve())


def render_ela_heatmap(original_bgr: np.ndarray, ela_gray: np.ndarray) -> np.ndarray:
    """ELA heatmap overlay — highlight suspicious compression regions."""
    if ela_gray.ndim == 3:
        ela_gray = cv2.cvtColor(ela_gray, cv2.COLOR_BGR2GRAY)

    ela_norm = cv2.normalize(ela_gray, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    heatmap = cv2.applyColorMap(ela_norm, cv2.COLORMAP_JET)

    if original_bgr.shape[:2] != heatmap.shape[:2]:
        heatmap = cv2.resize(heatmap, (original_bgr.shape[1], original_bgr.shape[0]))

    # Blend: suspicious regions glow red/yellow
    mask = (ela_norm > np.percentile(ela_norm, 75)).astype(np.float32)
    mask = cv2.GaussianBlur(mask, (15, 15), 0)[..., None]
    blended = (original_bgr * (1 - mask * 0.55) + heatmap * (mask * 0.55)).astype(np.uint8)
    return blended


def render_edge_overlay(original_bgr: np.ndarray, edges: np.ndarray) -> np.ndarray:
    """Edge overlay with suspicious high-density regions highlighted."""
    if edges.ndim == 3:
        edges = cv2.cvtColor(edges, cv2.COLOR_BGR2GRAY)

    overlay = original_bgr.copy()
    edge_color = np.zeros_like(original_bgr)
    edge_color[:, :, 2] = edges  # Red edges

    suspicious = edges > np.percentile(edges[edges > 0], 85) if np.any(edges > 0) else edges > 0
    suspicious_color = np.zeros_like(original_bgr)
    suspicious_color[:, :, 1] = (suspicious.astype(np.uint8) * 200)

    combined = cv2.addWeighted(overlay, 0.7, edge_color, 0.5, 0)
    combined = cv2.addWeighted(combined, 1.0, suspicious_color, 0.4, 0)
    return combined


def render_wavelet_heatmap(original_bgr: np.ndarray, wavelet_map: np.ndarray) -> np.ndarray:
    """Wavelet frequency anomaly heatmap."""
    if wavelet_map.ndim == 3:
        wavelet_map = cv2.cvtColor(wavelet_map, cv2.COLOR_BGR2GRAY)

    wnorm = cv2.normalize(wavelet_map, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    heatmap = cv2.applyColorMap(wnorm, cv2.COLORMAP_TURBO)

    if original_bgr.shape[:2] != heatmap.shape[:2]:
        heatmap = cv2.resize(heatmap, (original_bgr.shape[1], original_bgr.shape[0]))

    mask = (wnorm > np.percentile(wnorm, 80)).astype(np.float32)
    mask = cv2.GaussianBlur(mask, (11, 11), 0)[..., None]
    return (original_bgr * (1 - mask * 0.5) + heatmap * (mask * 0.5)).astype(np.uint8)


def load_bgr(image_path: str) -> Optional[np.ndarray]:
    img = cv2.imread(str(image_path))
    return img
