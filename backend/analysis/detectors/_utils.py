"""
Shared tile-based anomaly utilities for spectral detectors.
"""

from __future__ import annotations

from typing import List, Tuple

import cv2
import numpy as np


def load_working_bgr(image_path: str, max_side: int = 1200) -> np.ndarray:
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"Cannot read image: {image_path}")
    h, w = img.shape[:2]
    if max(h, w) > max_side:
        scale = max_side / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return img


def tile_means(channel: np.ndarray, tile: int = 32) -> List[float]:
    h, w = channel.shape[:2]
    values: List[float] = []
    for y in range(0, h - tile, tile):
        for x in range(0, w - tile, tile):
            block = channel[y: y + tile, x: x + tile]
            values.append(float(np.mean(block)))
    return values


def anomaly_score_from_tiles(values: List[float]) -> float:
    if len(values) < 4:
        return 0.0
    arr = np.array(values, dtype=np.float32)
    mean = float(np.mean(arr))
    std = float(np.std(arr))
    if mean < 1e-6:
        return min(1.0, std / 50.0)
    cv = std / (mean + 1e-6)
    return float(min(1.0, cv * 2.5))


def boundary_grid_score(gray: np.ndarray, period: int = 8) -> float:
    """Detect periodic 8x8 JPEG grid boundaries."""
    h, w = gray.shape
    if h < period * 4 or w < period * 4:
        return 0.0

    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(gx, gy)

    h_edges = [float(np.mean(mag[y, :])) for y in range(period, h, period)]
    v_edges = [float(np.mean(mag[:, x])) for x in range(period, w, period)]
    all_edges = h_edges + v_edges
    if not all_edges:
        return 0.0

    baseline = float(np.mean(mag))
    peak = float(np.mean(all_edges))
    if baseline < 1e-6:
        return 0.0
    return float(min(1.0, max(0.0, (peak / baseline - 1.0) * 0.5)))
