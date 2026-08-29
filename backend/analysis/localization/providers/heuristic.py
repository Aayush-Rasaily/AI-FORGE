"""Heuristic multi-signal segmentation — always available fallback."""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from backend.analysis.localization.contracts import SegmentationOutput
from backend.analysis.localization.providers.base import (
    build_output,
    load_bgr,
    normalize_map,
    save_segmentation_artifacts,
)

logger = logging.getLogger("ai_forge.localization.heuristic")


class HeuristicSegmentationProvider:
    name = "heuristic"

    def is_available(self) -> bool:
        return True

    def segment(self, image_path: str, output_dir: str) -> SegmentationOutput:
        out = Path(output_dir)
        original = load_bgr(image_path)
        if original is None:
            raise ValueError(f"Cannot read image: {image_path}")

        gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        h, w = gray.shape

        # ELA proxy
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        ela = normalize_map(np.abs(gray - blur))

        # Wavelet proxy (high-frequency residual)
        lap = normalize_map(np.abs(cv2.Laplacian(gray, cv2.CV_32F)))

        # Noise residual
        denoise = cv2.bilateralFilter((gray * 255).astype(np.uint8), 7, 50, 50)
        noise = normalize_map(np.abs(gray - denoise.astype(np.float32) / 255.0))

        # Edge density anomalies
        edges = cv2.Canny((gray * 255).astype(np.uint8), 60, 140).astype(np.float32) / 255.0
        edges = normalize_map(edges)

        fused = normalize_map(ela * 0.35 + lap * 0.25 + noise * 0.25 + edges * 0.15)
        fused = cv2.GaussianBlur(fused, (0, 0), 2.5)

        thresh = float(np.percentile(fused, 88))
        binary = ((fused >= max(0.35, thresh)) * 255).astype(np.uint8)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        score = float(fused.mean())
        confidence = min(0.95, 0.45 + score * 0.55)
        paths = save_segmentation_artifacts(out, "heuristic", fused, binary, original)

        logger.info("Generated: Heuristic Segmentation -> saved")
        return build_output(
            self.name,
            fused,
            binary,
            score,
            confidence,
            "Multi-signal heuristic segmentation (ELA + wavelet + noise + edge fusion).",
            paths,
        )
