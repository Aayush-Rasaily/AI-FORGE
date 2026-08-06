"""
Unified Attention Heatmap Generator.

Fuses spatial signals from ELA, wavelet, edge detection, copy-move,
and tampering analysis into a single color-coded manipulation heatmap.

Color scale:
  Green  — safe (low manipulation probability)
  Orange — medium risk
  Red    — high manipulation probability
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
import pywt
from PIL import Image, ImageChops, ImageEnhance

from backend.tampering.tampering_detector import analyze_tampering

logger = logging.getLogger(__name__)

MODULE_WEIGHTS = {
    "ela": 0.25,
    "wavelet": 0.20,
    "edges": 0.15,
    "copy_move": 0.20,
    "tampering": 0.20,
}


def _normalize_map(arr: np.ndarray) -> np.ndarray:
    arr = arr.astype(np.float32)
    lo, hi = float(arr.min()), float(arr.max())
    if hi - lo < 1e-6:
        return np.zeros_like(arr, dtype=np.float32)
    return (arr - lo) / (hi - lo)


def _compute_ela_map(image_path: str) -> np.ndarray:
    original = Image.open(image_path).convert("RGB")
    import io

    buffer = io.BytesIO()
    original.save(buffer, format="JPEG", quality=90)
    buffer.seek(0)
    recompressed = Image.open(buffer).convert("RGB")
    diff = ImageChops.difference(original, recompressed)
    enhanced = ImageEnhance.Brightness(diff).enhance(10)
    gray = cv2.cvtColor(np.array(enhanced), cv2.COLOR_RGB2GRAY)
    return _normalize_map(gray)


def _compute_wavelet_map(image_path: str) -> np.ndarray:
    gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if gray is None:
        raise ValueError(f"Cannot read image: {image_path}")
    gray = gray.astype(np.float32)
    _, (horizontal, vertical, diagonal) = pywt.dwt2(gray, "haar")
    hf = np.abs(horizontal) + np.abs(vertical) + np.abs(diagonal)
    hf = cv2.resize(hf, (gray.shape[1], gray.shape[0]))
    return _normalize_map(hf)


def _compute_edge_map(image_path: str) -> np.ndarray:
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Cannot read image: {image_path}")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    thresh_val = float(thresh)
    edges = cv2.Canny(gray, int(thresh_val * 0.5), int(thresh_val))
    blurred = cv2.GaussianBlur(edges.astype(np.float32), (15, 15), 0)
    return _normalize_map(blurred)


def _compute_copy_move_map(image_path: str) -> np.ndarray:
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Cannot read image: {image_path}")
    h, w = image.shape[:2]
    heatmap = np.zeros((h, w), dtype=np.float32)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    orb = cv2.ORB_create(nfeatures=5000)
    keypoints, descriptors = orb.detectAndCompute(gray, None)
    if descriptors is None or len(keypoints) < 10:
        return heatmap

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    matches = matcher.knnMatch(descriptors, descriptors, k=3)
    min_spatial = 50

    for pair in matches:
        if len(pair) < 2:
            continue
        m = pair[0]
        if m.queryIdx == m.trainIdx:
            candidates = [x for x in pair if x.queryIdx != x.trainIdx]
            if not candidates:
                continue
            m = candidates[0]
        pt1 = keypoints[m.queryIdx].pt
        pt2 = keypoints[m.trainIdx].pt
        dist = np.hypot(pt1[0] - pt2[0], pt1[1] - pt2[1])
        if dist < min_spatial:
            continue
        for pt in (pt1, pt2):
            cv2.circle(heatmap, (int(pt[0]), int(pt[1])), 25, 1.0, -1)

    if heatmap.max() > 0:
        heatmap = cv2.GaussianBlur(heatmap, (31, 31), 0)
    return _normalize_map(heatmap)


def _compute_tampering_map(image_path: str) -> np.ndarray:
    """Local edge-variance map inspired by tampering edge inconsistency."""
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Cannot read image: {image_path}")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
    edges = cv2.Canny(gray.astype(np.uint8), 50, 150).astype(np.float32)

    kernel = 15
    local_mean = cv2.blur(edges, (kernel, kernel))
    local_sq = cv2.blur(edges ** 2, (kernel, kernel))
    local_var = np.maximum(local_sq - local_mean ** 2, 0)
    local_std = np.sqrt(local_var)
    return _normalize_map(local_std)


def _colorize_attention_map(fused: np.ndarray) -> np.ndarray:
    """Map 0-1 fused scores to RGB: green → orange → red."""
    h, w = fused.shape
    colored = np.zeros((h, w, 3), dtype=np.uint8)

    safe = fused < 0.33
    medium = (fused >= 0.33) & (fused < 0.66)
    high = fused >= 0.66

    colored[safe] = [34, 197, 94]       # green
    colored[medium] = [249, 115, 22]    # orange
    colored[high] = [239, 68, 68]       # red

    # Smooth transitions
    blend_zone = 0.08
    for mask, c1, c2, lo, hi in [
        (medium, [34, 197, 94], [249, 115, 22], 0.33 - blend_zone, 0.33 + blend_zone),
        (high, [249, 115, 22], [239, 68, 68], 0.66 - blend_zone, 0.66 + blend_zone),
    ]:
        t = np.clip((fused - lo) / (hi - lo + 1e-6), 0, 1)
        for ch in range(3):
            colored[:, :, ch] = np.where(
                mask,
                (1 - t) * c1[ch] + t * c2[ch],
                colored[:, :, ch],
            ).astype(np.uint8)

    return colored


def _create_overlay(original_bgr: np.ndarray, heatmap_bgr: np.ndarray, alpha: float = 0.5) -> np.ndarray:
    return cv2.addWeighted(original_bgr, 1 - alpha, heatmap_bgr, alpha, 0)


def generate_attention_heatmap(
    image_path: str,
    output_dir: str,
    tampering_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate unified attention heatmap from all forensic modules.

    Returns paths, per-module scores, and human-readable explanations.
    """
    image_path = Path(image_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    stem = image_path.stem
    heatmap_path = output_dir / f"{stem}_attention_heatmap.jpg"
    overlay_path = output_dir / f"{stem}_attention_overlay.jpg"
    legend_path = output_dir / f"{stem}_attention_legend.jpg"

    original = cv2.imread(str(image_path))
    if original is None:
        raise ValueError(f"Cannot read image: {image_path}")

    h, w = original.shape[:2]

    module_maps: Dict[str, np.ndarray] = {}
    module_scores: Dict[str, float] = {}
    explanations: List[Dict[str, str]] = []

    try:
        module_maps["ela"] = _compute_ela_map(str(image_path))
        module_scores["ela"] = float(np.mean(module_maps["ela"]))
        if module_scores["ela"] > 0.5:
            explanations.append({
                "module": "ela",
                "what": "High JPEG compression inconsistency detected around object boundaries.",
                "why": "ELA spatial map shows localized recompression artifacts.",
            })
    except Exception as exc:
        logger.warning("ELA map failed: %s", exc)
        module_maps["ela"] = np.zeros((h, w), dtype=np.float32)

    try:
        module_maps["wavelet"] = _compute_wavelet_map(str(image_path))
        module_scores["wavelet"] = float(np.mean(module_maps["wavelet"]))
        if module_scores["wavelet"] > 0.45:
            explanations.append({
                "module": "wavelet",
                "what": "Wavelet artifacts indicate localized editing.",
                "why": "High-frequency energy is unevenly distributed across the image.",
            })
    except Exception as exc:
        logger.warning("Wavelet map failed: %s", exc)
        module_maps["wavelet"] = np.zeros((h, w), dtype=np.float32)

    try:
        module_maps["edges"] = _compute_edge_map(str(image_path))
        module_scores["edges"] = float(np.mean(module_maps["edges"]))
    except Exception as exc:
        logger.warning("Edge map failed: %s", exc)
        module_maps["edges"] = np.zeros((h, w), dtype=np.float32)

    try:
        module_maps["copy_move"] = _compute_copy_move_map(str(image_path))
        module_scores["copy_move"] = float(np.max(module_maps["copy_move"]))
        if module_scores["copy_move"] > 0.3:
            explanations.append({
                "module": "copy_move",
                "what": "Copy-move detector found duplicated regions.",
                "why": "Spatial feature matches cluster at separated locations.",
            })
    except Exception as exc:
        logger.warning("Copy-move map failed: %s", exc)
        module_maps["copy_move"] = np.zeros((h, w), dtype=np.float32)

    try:
        module_maps["tampering"] = _compute_tampering_map(str(image_path))
        module_scores["tampering"] = float(np.mean(module_maps["tampering"]))
    except Exception as exc:
        logger.warning("Tampering map failed: %s", exc)
        module_maps["tampering"] = np.zeros((h, w), dtype=np.float32)

    if tampering_result is None:
        try:
            tampering_result = analyze_tampering(str(image_path))
        except Exception:
            tampering_result = {}

    tamper_score = float(tampering_result.get("tampering_score", 0) or 0)
    if tamper_score > 0.5:
        explanations.append({
            "module": "tampering",
            "what": "Tampering detector flagged manipulation signals.",
            "why": f"Combined tampering score {tamper_score:.0%} exceeds threshold.",
        })

    # Fuse maps
    fused = np.zeros((h, w), dtype=np.float32)
    for name, weight in MODULE_WEIGHTS.items():
        if name in module_maps:
            fused += weight * module_maps[name]
    fused = _normalize_map(fused)

    colored = _colorize_attention_map(fused)
    overlay = _create_overlay(original, colored, alpha=0.5)

    cv2.imwrite(str(heatmap_path), colored)
    cv2.imwrite(str(overlay_path), overlay)
    _save_legend(legend_path)

    overall_risk = float(np.mean(fused))
    high_pct = float(np.mean(fused >= 0.66) * 100)
    med_pct = float(np.mean((fused >= 0.33) & (fused < 0.66)) * 100)
    safe_pct = float(np.mean(fused < 0.33) * 100)

    if not explanations:
        explanations.append({
            "module": "attention",
            "what": "No significant manipulation hotspots detected.",
            "why": "Fused forensic maps show predominantly safe (green) regions.",
        })

    return {
        "success": True,
        "overall_risk": round(overall_risk, 4),
        "risk_zones": {
            "high_manipulation_pct": round(high_pct, 1),
            "medium_risk_pct": round(med_pct, 1),
            "safe_pct": round(safe_pct, 1),
        },
        "module_scores": {k: round(v, 4) for k, v in module_scores.items()},
        "module_weights": MODULE_WEIGHTS,
        "explanations": explanations,
        "artifacts": {
            "heatmap": str(heatmap_path),
            "overlay": str(overlay_path),
            "legend": str(legend_path),
            "original": str(image_path),
        },
        "tampering_score": round(tamper_score, 4),
    }


def _save_legend(path: Path) -> None:
    legend = np.ones((120, 400, 3), dtype=np.uint8) * 30
    cv2.rectangle(legend, (20, 40), (120, 70), (34, 197, 94), -1)
    cv2.putText(legend, "Safe", (130, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    cv2.rectangle(legend, (20, 75), (120, 105), (249, 115, 22), -1)
    cv2.putText(legend, "Medium", (130, 97), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    cv2.rectangle(legend, (220, 40), (320, 70), (239, 68, 68), -1)
    cv2.putText(legend, "High Manipulation", (220, 97), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    cv2.imwrite(str(path), legend)
