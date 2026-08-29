"""
Confidence Scorer — Stage 3 of the Evidence Localization Engine.

Assigns each filtered region a deterministic confidence score [0.0..1.0]
by combining multiple forensic signals using a fixed weighted formula.

Also classifies each region into one of five manipulation types:
    • text_manipulation   — OCR/font signals dominant
    • copy_move           — copy-move source
    • pixel_splice        — ELA + noise combination
    • metadata_anomaly    — metadata-only
    • general_manipulation — multi-source or unclassified

The formula is fully deterministic:
    confidence = clip(
        weighted_sum(signal_contributions) + corroboration_bonus,
        0.0, 1.0
    )

No random numbers, timestamps, or external state are used — identical
inputs always produce identical outputs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List

from backend.forensics.evidence_localization.region_proposer import RawRegion

logger = logging.getLogger("ai_forge.evidence_localization.scorer")

# ── Signal weights (must sum to 1.0) ───────────────────────────────────────
_WEIGHTS: Dict[str, float] = {
    "ela": 0.25,
    "copy_move": 0.25,
    "noise": 0.20,
    "ocr": 0.15,
    "localization": 0.10,  # existing pixel-level localization
    "metadata": 0.05,
}

# Bonus applied when ≥3 distinct sources corroborate a single region.
_CORROBORATION_BONUS: float = 0.10

# Minimum sources to award the corroboration bonus.
_CORROBORATION_MIN_SOURCES: int = 3

# Sources that are always weighted at 1.0 (binary signals).
_BINARY_SOURCES = frozenset({"copy_move"})
# ────────────────────────────────────────────────────────────────────────────


@dataclass
class ScoredRegion:
    """A region after confidence scoring, ready for serialization."""

    region_id: str
    manipulation_type: str
    bbox: tuple                     # (x, y, w, h)
    confidence: float               # [0.0..1.0]
    evidence: List[str]             # human-readable evidence bullet points
    source_signals: List[str]       # which forensic sources contributed
    corroborated: bool              # True if ≥3 distinct sources agree
    raw_score: float                # pre-normalised score from proposer
    signal_contributions: Dict[str, float] = field(default_factory=dict)


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


# ── Type classifier ─────────────────────────────────────────────────────────

def _classify_type(sources: List[str]) -> str:
    """
    Deterministically classify a region's manipulation type based on
    which forensic sources contributed.  Priority order matters.
    """
    src_set = set(sources)

    if "copy_move" in src_set:
        return "copy_move"

    if "ocr" in src_set and len(src_set) <= 2:
        return "text_manipulation"

    if "ela" in src_set and "noise" in src_set:
        return "pixel_splice"

    if "metadata" in src_set and len(src_set) == 1:
        return "metadata_anomaly"

    if "ocr" in src_set:
        return "text_manipulation"

    if "ela" in src_set or "localization" in src_set:
        return "pixel_splice"

    return "general_manipulation"


# ── Global signal extractor ─────────────────────────────────────────────────

def _global_signal_scores(
    analysis_result: Dict[str, Any],
    jury_result: Dict[str, Any],
) -> Dict[str, float]:
    """
    Extract the global (image-level) score for each known signal source
    from the analysis result dict.  Used to weight sources that have no
    per-region breakdown.
    """
    signals: Dict[str, Any] = analysis_result.get("signals") or {}

    ela = _safe_float(signals.get("ela_score", 0.0))

    noise_inc = _safe_float(signals.get("noise_inconsistency", 0.0))
    noise = min(1.0, noise_inc)

    cm = 1.0 if signals.get("copy_move_detected") else _safe_float(
        signals.get("copy_move_score", 0.0)
    )

    # OCR: derived from font_anomaly_count and spacing_risk
    font_count = _safe_float(signals.get("font_anomaly_count", 0.0))
    spacing_risk = _safe_float(signals.get("spacing_risk", 0.0))
    spacing_norm = spacing_risk / 100.0 if spacing_risk > 1.0 else spacing_risk
    ocr = min(1.0, (font_count / 10.0) * 0.5 + spacing_norm * 0.5)

    meta_risk = _safe_float(signals.get("metadata_risk_score", 0.0))
    meta_suspicious = bool(signals.get("metadata_suspicious", False))
    metadata = max(meta_risk, 0.5 if meta_suspicious else 0.0)

    # AI Jury boost: average risk score across all jury agents
    jury_boost = 0.0
    agents = (jury_result.get("agents") or {})
    if isinstance(agents, dict) and agents:
        risks = [
            _safe_float(a.get("risk_score", 0.0))
            for a in agents.values()
            if isinstance(a, dict)
        ]
        if risks:
            jury_boost = min(1.0, sum(risks) / len(risks))

    return {
        "ela": ela,
        "noise": noise,
        "copy_move": cm,
        "ocr": ocr,
        "metadata": metadata,
        "jury_boost": jury_boost,
    }


# ── Per-region confidence calculator ───────────────────────────────────────

def _score_region(
    region: RawRegion,
    global_scores: Dict[str, float],
) -> float:
    """
    Compute confidence for a single region.

    For each known signal source:
        - If the region's own source matches, use the raw region score.
        - Otherwise, use the global image-level score as a secondary signal,
          but weighted down by 50 % (it is not spatially localised here).

    Then blend the two contributions according to _WEIGHTS.
    """
    contributions: Dict[str, float] = {}

    for src, weight in _WEIGHTS.items():
        if src == region.source:
            # Primary signal: use the region's own score.
            contribution = region.score * weight
        elif src in _BINARY_SOURCES:
            # Binary sources: use global score directly.
            contribution = global_scores.get(src, 0.0) * weight * 0.5
        else:
            # Secondary cross-signal: halved to avoid over-weighting.
            contribution = global_scores.get(src, 0.0) * weight * 0.5

        contributions[src] = round(contribution, 6)

    weighted_sum = sum(contributions.values())

    # Normalization: the maximum possible weighted sum when all signals = 1.0
    max_possible = sum(_WEIGHTS.values())
    normalised = weighted_sum / max_possible if max_possible > 0 else 0.0

    # Jury bonus: +5 % when jury consensus is high.
    jury_boost = global_scores.get("jury_boost", 0.0)
    if jury_boost >= 0.60:
        normalised = min(1.0, normalised + 0.05)

    return round(max(0.0, min(1.0, normalised)), 4)


# ── Public entry point ──────────────────────────────────────────────────────

def score_regions(
    filtered_regions: List[RawRegion],
    analysis_result: Dict[str, Any],
    jury_result: Dict[str, Any],
) -> List[ScoredRegion]:
    """
    Score and classify every filtered region.

    Parameters
    ----------
    filtered_regions : Output from candidate_filter.filter_candidates()
    analysis_result  : Full result dict from analyze_image_unified() — read-only.
    jury_result      : Output dict from run_jury_analysis()          — read-only.

    Returns
    -------
    List of ScoredRegion objects sorted by confidence descending.
    """
    if not filtered_regions:
        return []

    global_scores = _global_signal_scores(analysis_result, jury_result)

    scored: List[ScoredRegion] = []

    for i, region in enumerate(filtered_regions):
        # Determine sources — for merged regions the source reflects the
        # dominant contributor.  We collect unique sources from evidence labels
        # plus the primary source tag.
        sources = [region.source]
        for label in region.evidence_labels:
            label_lower = label.lower()
            if "ela" in label_lower and "ela" not in sources:
                sources.append("ela")
            if ("noise" in label_lower or "inconsistency" in label_lower) and "noise" not in sources:
                sources.append("noise")
            if ("copy" in label_lower or "duplicate" in label_lower) and "copy_move" not in sources:
                sources.append("copy_move")
            if ("ocr" in label_lower or "font" in label_lower or "text" in label_lower) and "ocr" not in sources:
                sources.append("ocr")
            if "metadata" in label_lower and "metadata" not in sources:
                sources.append("metadata")
            if "localization" in label_lower and "localization" not in sources:
                sources.append("localization")

        sources = list(dict.fromkeys(sources))  # deduplicate while preserving order

        corroborated = len(sources) >= _CORROBORATION_MIN_SOURCES
        confidence = _score_region(region, global_scores)

        # Corroboration bonus
        if corroborated:
            confidence = round(min(1.0, confidence + _CORROBORATION_BONUS), 4)

        manip_type = _classify_type(sources)

        # Region id uses zero-padded index so sort order is preserved.
        region_id = f"region_{i + 1:03d}"

        signal_contributions = {
            src: round(region.score * _WEIGHTS.get(src, 0.0), 6)
            if src == region.source
            else round(global_scores.get(src, 0.0) * _WEIGHTS.get(src, 0.0) * 0.5, 6)
            for src in _WEIGHTS
        }

        scored.append(ScoredRegion(
            region_id=region_id,
            manipulation_type=manip_type,
            bbox=region.bbox,
            confidence=confidence,
            evidence=list(region.evidence_labels),
            source_signals=sources,
            corroborated=corroborated,
            raw_score=region.score,
            signal_contributions=signal_contributions,
        ))

    # Final sort: confidence descending, then region_id ascending (deterministic tiebreak).
    scored.sort(key=lambda r: (-r.confidence, r.region_id))

    # Re-assign sequential IDs after final sort.
    for idx, sr in enumerate(scored):
        sr.region_id = f"region_{idx + 1:03d}"

    logger.debug(
        "score_regions: %d regions scored | top confidence=%.4f",
        len(scored),
        scored[0].confidence if scored else 0.0,
    )

    return scored
