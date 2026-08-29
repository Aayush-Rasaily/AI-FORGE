"""
Region Proposer — Stage 1 of the Evidence Localization Engine.

Converts all forensic signal outputs into a flat list of RawRegion
candidates.  Each candidate carries:
    - source  : which forensic module produced it
    - bbox    : (x, y, w, h) in absolute pixels
    - score   : raw signal strength [0.0 .. 1.0]
    - evidence_labels : human-readable bullet-point labels

Sources consumed (read-only — never mutated):
    • ELA artifact (ela.png / artifacts/ela.png)        → contour detection
    • Noise grid   (noise_result from analysis_result)  → elevated-cell bboxes
    • Copy-Move    (copy_move_result["regions"])         → grouped keypoint bboxes
    • OCR / Font   (font_consistency["suspicious_words"]) → per-word bboxes
    • Region Anomaly (region_anomaly["high_risk_regions"]) → pass-through bboxes
    • Forgery Localization (localization["regions"])     → re-use existing bboxes
    • Metadata     (metadata_forensics)                 → sentinel full-image region
    • AI Jury      (jury_result["agents"])               → boost only, no spatial data

All methods are pure functions.  No file writes occur here.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger("ai_forge.evidence_localization.proposer")

# Minimum contour area (px²) when extracting blobs from the ELA artifact.
_ELA_MIN_AREA = 400

# Minimum score for a raw region to be proposed at all.
_SCORE_FLOOR = 0.10

# When we have an image but no per-pixel region from a signal, we use a
# 4×4 grid partitioning to produce sub-image cells.
_GRID_ROWS = 4
_GRID_COLS = 4


@dataclass
class RawRegion:
    """A single candidate manipulation region before filtering."""

    source: str                          # originating forensic module
    bbox: Tuple[int, int, int, int]      # (x, y, w, h) — absolute pixels
    score: float                         # raw strength [0..1]
    evidence_labels: List[str] = field(default_factory=list)

    def area(self) -> int:
        return self.bbox[2] * self.bbox[3]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _bbox_from_dict(d: Dict[str, Any]) -> Optional[Tuple[int, int, int, int]]:
    """
    Extract (x, y, w, h) from the many bbox representations used across AI-FORGE.
    Supports: {x,y,w,h}, {x,y,width,height}, [x,y,w,h] lists.
    """
    if isinstance(d, (list, tuple)) and len(d) >= 4:
        return (
            _safe_int(d[0]), _safe_int(d[1]),
            _safe_int(d[2]), _safe_int(d[3]),
        )
    if isinstance(d, dict):
        x = _safe_int(d.get("x", d.get("left", 0)))
        y = _safe_int(d.get("y", d.get("top", 0)))
        w = _safe_int(d.get("w", d.get("width", 0)))
        h = _safe_int(d.get("h", d.get("height", 0)))
        return (x, y, w, h)
    return None


def _clamp_bbox(
    bbox: Tuple[int, int, int, int],
    img_w: int,
    img_h: int,
) -> Tuple[int, int, int, int]:
    """Clamp bbox to image boundaries and ensure positive dimensions."""
    x, y, w, h = bbox
    x = max(0, min(x, img_w - 1))
    y = max(0, min(y, img_h - 1))
    w = max(1, min(w, img_w - x))
    h = max(1, min(h, img_h - y))
    return (x, y, w, h)


def _get_image_dimensions(image_path: Path) -> Tuple[int, int]:
    """Return (width, height) of the image, or (1024, 768) as safe fallback."""
    try:
        img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if img is not None:
            ih, iw = img.shape[:2]
            return iw, ih
    except Exception:
        pass
    return 1024, 768


# ---------------------------------------------------------------------------
# ELA proposer
# ---------------------------------------------------------------------------

def _propose_from_ela(
    analysis_dir: Path,
    ela_score: float,
    img_w: int,
    img_h: int,
) -> List[RawRegion]:
    """
    Read the ELA artifact image and extract high-response blob regions.
    Falls back to full-image sentinel if the artifact is unavailable.
    """
    regions: List[RawRegion] = []

    if ela_score < _SCORE_FLOOR:
        return regions

    # Look for the ELA artifact in the standard locations.
    candidates = [
        analysis_dir / "artifacts" / "ela.png",
        analysis_dir / "artifacts" / "ela.jpg",
        analysis_dir / "ela.png",
        analysis_dir / "ela.jpg",
    ]
    ela_path: Optional[Path] = None
    for c in candidates:
        if c.is_file() and c.stat().st_size > 50:
            ela_path = c
            break

    if ela_path is None:
        # No artifact — emit single full-image region at the global ELA score.
        if ela_score >= 0.30:
            regions.append(RawRegion(
                source="ela",
                bbox=(0, 0, img_w, img_h),
                score=ela_score,
                evidence_labels=["ELA hotspot (global — artifact unavailable)"],
            ))
        return regions

    try:
        ela_img = cv2.imread(str(ela_path), cv2.IMREAD_GRAYSCALE)
        if ela_img is None:
            return regions

        # Resize to match image dimensions if needed.
        if ela_img.shape[:2] != (img_h, img_w):
            ela_img = cv2.resize(ela_img, (img_w, img_h), interpolation=cv2.INTER_LINEAR)

        # Threshold at 60th percentile to find elevated areas.
        thresh_val = max(30, int(np.percentile(ela_img, 60)))
        _, binary = cv2.threshold(ela_img, thresh_val, 255, cv2.THRESH_BINARY)

        # Dilate slightly to merge nearby blobs.
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
        dilated = cv2.dilate(binary, kernel, iterations=1)

        contours, _ = cv2.findContours(
            dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < _ELA_MIN_AREA:
                continue
            x, y, w, h = cv2.boundingRect(cnt)
            roi = ela_img[y: y + h, x: x + w]
            roi_mean = float(roi.mean()) / 255.0
            if roi_mean < _SCORE_FLOOR:
                continue
            # Scale the local blob mean by the global ELA score.
            score = min(1.0, roi_mean * (1.0 + ela_score))
            regions.append(RawRegion(
                source="ela",
                bbox=_clamp_bbox((x, y, w, h), img_w, img_h),
                score=round(score, 4),
                evidence_labels=[f"ELA hotspot (local response {roi_mean:.2f})"],
            ))

        regions.sort(key=lambda r: r.score, reverse=True)
        return regions[:20]  # cap per-source

    except Exception as exc:
        logger.debug("ELA proposer error: %s", exc)
        return regions


# ---------------------------------------------------------------------------
# Noise proposer
# ---------------------------------------------------------------------------

def _propose_from_noise(
    noise_result: Dict[str, Any],
    img_w: int,
    img_h: int,
) -> List[RawRegion]:
    """
    Use the 4×4 noise grid already computed by analyze_noise() to propose
    sub-image cells where local noise std significantly exceeds the mean.
    """
    regions: List[RawRegion] = []

    noise_inconsistency = _safe_float(noise_result.get("noise_inconsistency", 0.0))
    if noise_inconsistency < _SCORE_FLOOR:
        return regions

    # Recompute the grid on the noise_score to identify elevated cells.
    # Since we only have aggregate stats (not per-cell breakdown in the dict),
    # we mark cells proportional to the inconsistency magnitude.
    # For robustness, we emit the top quarter of the image as suspect.
    # A real per-cell breakdown would need analyze_noise to return it;
    # for now we produce a grid-level annotation.
    noise_score = _safe_float(noise_result.get("noise_score", 0.0))
    cell_w = img_w // _GRID_COLS
    cell_h = img_h // _GRID_ROWS

    # We treat the global inconsistency as a score for every cell initially,
    # then emit only cells that "would be anomalous" statistically.
    # Without per-cell data we produce a single region spanning the image
    # at the inconsistency level — the filter stage will handle dedup with ELA.
    if noise_inconsistency >= 0.30:
        regions.append(RawRegion(
            source="noise",
            bbox=(0, 0, img_w, img_h),
            score=round(min(1.0, noise_inconsistency), 4),
            evidence_labels=[
                f"Noise mismatch (inconsistency={noise_inconsistency:.2f}, "
                f"std={noise_score:.2f})"
            ],
        ))

    return regions


# ---------------------------------------------------------------------------
# Copy-Move proposer
# ---------------------------------------------------------------------------

def _propose_from_copy_move(
    copy_move_result: Dict[str, Any],
    img_w: int,
    img_h: int,
) -> List[RawRegion]:
    """
    Extract bounding boxes from copy-move detection results.
    Handles both structured region lists and raw keypoint pairs.
    """
    regions: List[RawRegion] = []

    if not isinstance(copy_move_result, dict):
        return regions

    detected = bool(
        copy_move_result.get("copy_move_detected")
        or copy_move_result.get("detected")
    )
    score = _safe_float(
        copy_move_result.get("copy_move_score", copy_move_result.get("score", 0.0))
    )

    if not detected and score < _SCORE_FLOOR:
        return regions

    # 1. Structured region list (if present)
    structured_regions = copy_move_result.get("regions") or []
    for reg in structured_regions:
        if not isinstance(reg, dict):
            continue
        bbox_raw = (
            reg.get("bbox")
            or reg.get("bounding_box")
            or reg.get("source_bbox")
        )
        bbox = _bbox_from_dict(bbox_raw) if bbox_raw else None
        if bbox is None:
            continue
        reg_score = _safe_float(reg.get("score", reg.get("confidence", score)))
        regions.append(RawRegion(
            source="copy_move",
            bbox=_clamp_bbox(bbox, img_w, img_h),
            score=round(min(1.0, reg_score), 4),
            evidence_labels=["Copy-Move duplication detected in region"],
        ))

    # 2. Keypoint pairs → build a single encompassing bbox
    keypoints = copy_move_result.get("keypoint_pairs") or copy_move_result.get("match_pairs") or []
    if keypoints and not structured_regions:
        xs, ys = [], []
        for pair in keypoints[:200]:
            if isinstance(pair, (list, tuple)) and len(pair) == 2:
                p1, p2 = pair
                for pt in (p1, p2):
                    if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                        xs.append(float(pt[0]))
                        ys.append(float(pt[1]))
        if xs and ys:
            x1, y1 = int(min(xs)), int(min(ys))
            x2, y2 = int(max(xs)), int(max(ys))
            w, h = max(1, x2 - x1), max(1, y2 - y1)
            regions.append(RawRegion(
                source="copy_move",
                bbox=_clamp_bbox((x1, y1, w, h), img_w, img_h),
                score=round(min(1.0, score if score > 0 else 0.75), 4),
                evidence_labels=[
                    f"Copy-Move keypoint cluster "
                    f"({len(keypoints)} matched pairs)"
                ],
            ))

    # 3. Fallback: if detected but no spatial data, emit full-image sentinel.
    if detected and not regions:
        matched = _safe_int(
            copy_move_result.get("matched_points", copy_move_result.get("matches", 0))
        )
        regions.append(RawRegion(
            source="copy_move",
            bbox=(0, 0, img_w, img_h),
            score=round(min(1.0, score if score > 0 else 0.80), 4),
            evidence_labels=[
                f"Copy-Move detected ({matched} matched keypoints, "
                "no spatial breakdown available)"
            ],
        ))

    return regions


# ---------------------------------------------------------------------------
# OCR / Font proposer
# ---------------------------------------------------------------------------

def _propose_from_ocr(
    font_result: Dict[str, Any],
    region_result: Dict[str, Any],
    img_w: int,
    img_h: int,
) -> List[RawRegion]:
    """
    Extract per-word or per-region bboxes flagged by font/OCR inconsistency.
    """
    regions: List[RawRegion] = []

    # Font consistency suspicious words
    suspicious_words = font_result.get("suspicious_words") or []
    for word in suspicious_words:
        if not isinstance(word, dict):
            continue
        bbox_raw = word.get("bbox") or word.get("bounding_box") or word.get("box")
        bbox = _bbox_from_dict(bbox_raw) if bbox_raw else None
        if bbox is None:
            continue
        # Normalised coords (values ≤ 1.5) → convert to absolute
        x, y, w, h = bbox
        if max(x, y, w, h) <= 1.5:
            x, y, w, h = (
                int(x * img_w), int(y * img_h),
                int(w * img_w), int(h * img_h),
            )
        word_score = _safe_float(
            word.get("score", word.get("confidence", word.get("anomaly_score", 0.65)))
        )
        label = word.get("word") or word.get("text") or "unknown"
        regions.append(RawRegion(
            source="ocr",
            bbox=_clamp_bbox((x, y, w, h), img_w, img_h),
            score=round(min(1.0, word_score), 4),
            evidence_labels=[f"OCR/Font inconsistency: '{label}'"],
        ))

    # High-risk regions from region_anomaly module
    high_risk = region_result.get("high_risk_regions") or []
    for reg in high_risk:
        if not isinstance(reg, dict):
            continue
        bbox_raw = reg.get("bbox") or reg.get("bounding_box")
        bbox = _bbox_from_dict(bbox_raw) if bbox_raw else None
        if bbox is None:
            continue
        x, y, w, h = bbox
        if max(x, y, w, h) <= 1.5:
            x, y, w, h = (
                int(x * img_w), int(y * img_h),
                int(w * img_w), int(h * img_h),
            )
        reg_score = _safe_float(reg.get("risk_score", reg.get("score", 0.65)))
        reason = reg.get("reason") or reg.get("label") or "region anomaly"
        regions.append(RawRegion(
            source="ocr",
            bbox=_clamp_bbox((x, y, w, h), img_w, img_h),
            score=round(min(1.0, reg_score), 4),
            evidence_labels=[f"Region anomaly: {reason}"],
        ))

    return regions


# ---------------------------------------------------------------------------
# Forgery localization proposer (re-use existing localization regions)
# ---------------------------------------------------------------------------

def _propose_from_localization(
    localization: Dict[str, Any],
    img_w: int,
    img_h: int,
) -> List[RawRegion]:
    """
    Re-use regions already computed by the forgery_localization module.
    These carry the highest spatial precision since they are derived from
    pixel-level heatmaps.
    """
    regions: List[RawRegion] = []
    loc_regions = localization.get("regions") or []

    for reg in loc_regions:
        if not isinstance(reg, dict):
            continue
        # Support both bbox dict formats present in existing localization.
        bbox_raw = reg.get("bounding_box") or reg.get("bbox")
        bbox = _bbox_from_dict(bbox_raw) if bbox_raw else None
        if bbox is None:
            continue
        x, y, w, h = bbox
        score = _safe_float(reg.get("score", reg.get("confidence", 0.5)))
        # score may be in [0..100] percent or [0..1]
        if score > 1.0:
            score = score / 100.0
        reason = reg.get("reason") or reg.get("label") or "Pixel-level forgery mask"
        regions.append(RawRegion(
            source="localization",
            bbox=_clamp_bbox((x, y, w, h), img_w, img_h),
            score=round(min(1.0, score), 4),
            evidence_labels=[f"Forgery localization map: {reason}"],
        ))

    regions.sort(key=lambda r: r.score, reverse=True)
    return regions[:20]


# ---------------------------------------------------------------------------
# Metadata proposer (global-level signal → sentinel region)
# ---------------------------------------------------------------------------

def _propose_from_metadata(
    metadata_result: Dict[str, Any],
    signals: Dict[str, Any],
    img_w: int,
    img_h: int,
) -> List[RawRegion]:
    """
    Metadata has no pixel-level spatial extent.
    When suspicious, we emit a sentinel full-image region so the
    confidence scorer can incorporate the metadata signal.
    """
    regions: List[RawRegion] = []

    suspicious = bool(
        metadata_result.get("suspicious")
        or metadata_result.get("metadata_suspicious")
        or signals.get("metadata_suspicious")
    )
    metadata_risk_score = _safe_float(
        signals.get("metadata_risk_score", metadata_result.get("metadata_risk_score", 0.0))
    )

    if not suspicious and metadata_risk_score < 0.25:
        return regions

    score = max(metadata_risk_score, 0.40 if suspicious else 0.0)
    software = metadata_result.get("software") or "unknown software"
    labels = [f"Metadata anomaly (risk={metadata_risk_score:.2f})"]
    if suspicious:
        labels.append(f"Editing software detected: {software}")

    regions.append(RawRegion(
        source="metadata",
        bbox=(0, 0, img_w, img_h),
        score=round(min(1.0, score), 4),
        evidence_labels=labels,
    ))
    return regions


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def propose_regions(
    image_path: Path,
    analysis_dir: Path,
    analysis_result: Dict[str, Any],
    jury_result: Dict[str, Any],
) -> List[RawRegion]:
    """
    Generate all raw region candidates from the full set of forensic signal outputs.

    Parameters
    ----------
    image_path      : Path to the evidence image file.
    analysis_dir    : Directory where forensic artifacts are stored.
    analysis_result : Output dict from analyze_image_unified() — read-only.
    jury_result     : Output dict from run_jury_analysis()      — read-only.

    Returns
    -------
    Flat, unsorted list of RawRegion candidates (may contain overlaps/duplicates).
    """
    img_w, img_h = _get_image_dimensions(image_path)

    signals: Dict[str, Any] = analysis_result.get("signals") or {}
    noise_result: Dict[str, Any] = analysis_result.get("noise") or {}
    copy_move_result: Dict[str, Any] = analysis_result.get("copy_move") or {}
    metadata_result: Dict[str, Any] = (
        analysis_result.get("metadata_forensics")
        or analysis_result.get("metadata")
        or {}
    )
    font_result: Dict[str, Any] = analysis_result.get("font_consistency") or {}
    region_result: Dict[str, Any] = analysis_result.get("region_anomaly") or {}
    localization: Dict[str, Any] = analysis_result.get("localization") or {}

    ela_score = _safe_float(signals.get("ela_score", 0.0))

    all_regions: List[RawRegion] = []

    # 1. ELA
    try:
        all_regions.extend(
            _propose_from_ela(analysis_dir, ela_score, img_w, img_h)
        )
    except Exception as exc:
        logger.debug("ELA proposer skipped: %s", exc)

    # 2. Noise
    try:
        all_regions.extend(
            _propose_from_noise(noise_result, img_w, img_h)
        )
    except Exception as exc:
        logger.debug("Noise proposer skipped: %s", exc)

    # 3. Copy-Move
    try:
        all_regions.extend(
            _propose_from_copy_move(copy_move_result, img_w, img_h)
        )
    except Exception as exc:
        logger.debug("Copy-Move proposer skipped: %s", exc)

    # 4. OCR / Font / Region Anomaly
    try:
        all_regions.extend(
            _propose_from_ocr(font_result, region_result, img_w, img_h)
        )
    except Exception as exc:
        logger.debug("OCR proposer skipped: %s", exc)

    # 5. Forgery localization (existing pixel-level regions)
    try:
        all_regions.extend(
            _propose_from_localization(localization, img_w, img_h)
        )
    except Exception as exc:
        logger.debug("Localization proposer skipped: %s", exc)

    # 6. Metadata
    try:
        all_regions.extend(
            _propose_from_metadata(metadata_result, signals, img_w, img_h)
        )
    except Exception as exc:
        logger.debug("Metadata proposer skipped: %s", exc)

    logger.debug(
        "propose_regions: %d raw candidates from %d sources",
        len(all_regions),
        len({r.source for r in all_regions}),
    )
    return all_regions
