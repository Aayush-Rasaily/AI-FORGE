"""
Candidate Filter — Stage 2 of the Evidence Localization Engine.

Cleans the raw region list produced by region_proposer by:

    1. Minimum area filter      — drops regions smaller than MIN_AREA px²
    2. Score threshold filter   — drops regions below SCORE_THRESHOLD
    3. Deduplication            — removes exact duplicate (source, bbox) pairs
    4. IoU-based NMS merge      — merges overlapping regions (IoU > IOU_THRESHOLD)
                                  by taking the union bbox and combining evidence
    5. Cap                      — keeps at most MAX_REGIONS (sorted by score desc)

All operations are performed with pure NumPy — no OpenCV dependency.
All functions are pure (no I/O, no mutation of inputs).
"""

from __future__ import annotations

import logging
from typing import List, Tuple

import numpy as np

from backend.forensics.evidence_localization.region_proposer import RawRegion

logger = logging.getLogger("ai_forge.evidence_localization.filter")

# ── Tuneable thresholds ─────────────────────────────────────────────────────
MIN_AREA: int = 400          # px² — minimum bbox area to keep
SCORE_THRESHOLD: float = 0.12  # minimum raw score to keep
IOU_THRESHOLD: float = 0.45    # merge two regions when IoU exceeds this
MAX_REGIONS: int = 50          # maximum number of output regions
# ────────────────────────────────────────────────────────────────────────────


def _iou(
    a: Tuple[int, int, int, int],
    b: Tuple[int, int, int, int],
) -> float:
    """
    Intersection-over-Union for two bboxes in (x, y, w, h) format.
    Returns float in [0.0, 1.0].
    """
    ax1, ay1 = a[0], a[1]
    ax2, ay2 = a[0] + a[2], a[1] + a[3]
    bx1, by1 = b[0], b[1]
    bx2, by2 = b[0] + b[2], b[1] + b[3]

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    inter_w = max(0, inter_x2 - inter_x1)
    inter_h = max(0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h

    if inter_area == 0:
        return 0.0

    area_a = a[2] * a[3]
    area_b = b[2] * b[3]
    union_area = area_a + area_b - inter_area

    return inter_area / union_area if union_area > 0 else 0.0


def _union_bbox(
    a: Tuple[int, int, int, int],
    b: Tuple[int, int, int, int],
) -> Tuple[int, int, int, int]:
    """Return the bounding box that fully contains both a and b."""
    ax1, ay1 = a[0], a[1]
    ax2, ay2 = a[0] + a[2], a[1] + a[3]
    bx1, by1 = b[0], b[1]
    bx2, by2 = b[0] + b[2], b[1] + b[3]

    ux1 = min(ax1, bx1)
    uy1 = min(ay1, by1)
    ux2 = max(ax2, bx2)
    uy2 = max(ay2, by2)

    return (ux1, uy1, max(1, ux2 - ux1), max(1, uy2 - uy1))


def _merge_two(a: RawRegion, b: RawRegion) -> RawRegion:
    """
    Merge two overlapping regions into one.
    The merged region:
        - takes the union bbox
        - keeps the higher score
        - takes the source from the higher-scoring input
        - combines evidence labels (deduplicated)
    """
    if a.score >= b.score:
        primary, secondary = a, b
    else:
        primary, secondary = b, a

    merged_labels = list(primary.evidence_labels)
    for label in secondary.evidence_labels:
        if label not in merged_labels:
            merged_labels.append(label)

    return RawRegion(
        source=primary.source,
        bbox=_union_bbox(a.bbox, b.bbox),
        score=primary.score,
        evidence_labels=merged_labels,
    )


# ── Filter stages ───────────────────────────────────────────────────────────

def _filter_min_area(regions: List[RawRegion]) -> List[RawRegion]:
    return [r for r in regions if r.area() >= MIN_AREA]


def _filter_score(regions: List[RawRegion]) -> List[RawRegion]:
    return [r for r in regions if r.score >= SCORE_THRESHOLD]


def _deduplicate(regions: List[RawRegion]) -> List[RawRegion]:
    """Remove exact duplicates — same (source, bbox) pair."""
    seen: set = set()
    out: List[RawRegion] = []
    for r in regions:
        key = (r.source, r.bbox)
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def _nms_merge(regions: List[RawRegion]) -> List[RawRegion]:
    """
    Greedy IoU-based NMS merge.

    Algorithm:
        1. Sort regions by score descending.
        2. For each unprocessed region A:
            a. Add A to the output (or start a merge group).
            b. For each remaining region B: if IoU(A, B) > threshold,
               merge B into A and mark B as consumed.
        3. Repeat until all regions are processed.
    """
    if not regions:
        return regions

    # Sort by score descending (stable sort — preserves relative order)
    sorted_r = sorted(regions, key=lambda r: r.score, reverse=True)
    consumed = [False] * len(sorted_r)
    merged: List[RawRegion] = []

    for i, anchor in enumerate(sorted_r):
        if consumed[i]:
            continue
        current = anchor
        for j in range(i + 1, len(sorted_r)):
            if consumed[j]:
                continue
            if _iou(current.bbox, sorted_r[j].bbox) > IOU_THRESHOLD:
                current = _merge_two(current, sorted_r[j])
                consumed[j] = True
        merged.append(current)

    return merged


def filter_candidates(regions: List[RawRegion]) -> List[RawRegion]:
    """
    Full filter pipeline:
        area filter → score filter → dedup → NMS merge → cap

    Parameters
    ----------
    regions : Raw candidate list from region_proposer.propose_regions()

    Returns
    -------
    Cleaned, merged, and capped region list sorted by score descending.
    """
    n_raw = len(regions)

    # Stage 1 — minimum area
    regions = _filter_min_area(regions)

    # Stage 2 — score floor
    regions = _filter_score(regions)

    # Stage 3 — deduplication
    regions = _deduplicate(regions)

    # Stage 4 — NMS merge
    regions = _nms_merge(regions)

    # Stage 5 — final sort + cap
    regions.sort(key=lambda r: r.score, reverse=True)
    regions = regions[:MAX_REGIONS]

    logger.debug(
        "filter_candidates: %d raw → %d after filtering",
        n_raw,
        len(regions),
    )

    return regions
