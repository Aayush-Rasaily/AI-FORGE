"""
JPEG block forensic analysis — grid detection, compression boundaries, double JPEG.
"""

from __future__ import annotations

import io
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from backend.analysis.detectors._utils import boundary_grid_score, load_working_bgr
from backend.analysis.detectors.base import DetectorResult, failed_result, make_result


def _double_jpeg_score(gray: np.ndarray) -> float:
    """Estimate double-JPEG via DCT coefficient histogram periodicity proxy."""
    h, w = gray.shape
    block = 8
    residuals = []
    for y in range(0, h - block, block):
        for x in range(0, w - block, block):
            patch = gray[y: y + block, x: x + block].astype(np.float32)
            dct = cv2.dct(patch)
            residuals.append(float(np.mean(np.abs(dct[1:, 1:]))))
    if len(residuals) < 16:
        return 0.0
    arr = np.array(residuals)
    # Bimodal residual distribution suggests double compression
    p75, p25 = np.percentile(arr, [75, 25])
    spread = (p75 - p25) / (np.mean(arr) + 1e-6)
    return float(min(1.0, max(0.0, (spread - 0.5) * 0.8)))


def _recompression_score(image_path: str) -> float:
    """Pixel-level recompression difference (in-memory, no disk writes)."""
    try:
        original = Image.open(image_path).convert("RGB")
        buf = io.BytesIO()
        original.save(buf, format="JPEG", quality=95)
        buf.seek(0)
        recompressed = np.asarray(Image.open(buf).convert("RGB"), dtype=np.float32)
        original_arr = np.asarray(original, dtype=np.float32)
        diff = float(np.mean(np.abs(original_arr - recompressed)))
        return float(min(1.0, diff / 15.0))
    except Exception:
        return 0.0


def _compression_boundary_score(gray: np.ndarray) -> float:
    """Detect sharp transitions at 8-pixel JPEG block boundaries."""
    return boundary_grid_score(gray, period=8)


def analyze_jpeg_blocks(image_path: str) -> DetectorResult:
    try:
        path = Path(image_path)
        is_jpeg = path.suffix.lower() in {".jpg", ".jpeg"} or _is_jpeg_format(path)

        bgr = load_working_bgr(str(path))
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

        grid_score = _compression_boundary_score(gray)
        double_score = _double_jpeg_score(gray)
        recomp_score = _recompression_score(str(path)) if is_jpeg else grid_score * 0.5

        score = min(1.0, grid_score * 0.35 + double_score * 0.35 + recomp_score * 0.30)

        flags = []
        if grid_score >= 0.35:
            flags.append("8×8 JPEG grid boundaries detected")
        if double_score >= 0.35:
            flags.append("double JPEG compression signatures")
        if recomp_score >= 0.35:
            flags.append("recompression / save artifacts")

        if score >= 0.5:
            expl = "JPEG block analysis: " + "; ".join(flags) + " — possible Photoshop save, splice, or social-media recompression."
        elif score >= 0.28:
            expl = "Moderate JPEG compression anomalies detected."
        elif not is_jpeg:
            expl = "Non-JPEG source; block analysis based on grid periodicity only."
        else:
            expl = "JPEG compression appears consistent with single-pass encoding."

        return make_result(
            "jpeg_block",
            score,
            confidence=0.76 if is_jpeg else 0.55,
            explanation=expl,
            is_jpeg=is_jpeg,
            grid_score=round(grid_score, 4),
            double_jpeg_score=round(double_score, 4),
            recompression_score=round(recomp_score, 4),
        )
    except Exception as exc:
        return failed_result("jpeg_block", str(exc))


def _is_jpeg_format(path: Path) -> bool:
    try:
        return Image.open(path).format == "JPEG"
    except Exception:
        return False
