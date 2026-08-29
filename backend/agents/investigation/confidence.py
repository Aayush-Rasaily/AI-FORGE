"""
Confidence calibration — multi-source calibrated fraud confidence.
Never report a single inflated percentage without component breakdown.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional


DEFAULT_WEIGHTS: Dict[str, float] = {
    "image": 0.22,
    "document": 0.18,
    "video": 0.16,
    "signature": 0.14,
    "metadata": 0.12,
    "reasoning": 0.10,
    "judge": 0.08,
}


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def calibrate_confidence(
    component_scores: Mapping[str, float],
    *,
    weights: Optional[Mapping[str, float]] = None,
) -> Dict[str, Any]:
    """
    component_scores: agent_id -> confidence (0..1)
    Returns calibrated final fraud confidence with breakdown.
    """
    wmap = dict(weights or DEFAULT_WEIGHTS)
    active = {k: _clamp(v) for k, v in component_scores.items() if v is not None}
    if not active:
        return {
            "components": {},
            "weights_used": {},
            "final_fraud_confidence": 0.0,
            "final_percent": 0,
            "calibration": "insufficient_evidence",
        }

    # Normalize weights over active components
    raw_w = {k: float(wmap.get(k, 0.1)) for k in active}
    total_w = sum(raw_w.values()) or 1.0
    norm_w = {k: raw_w[k] / total_w for k in active}

    # Confidence-weighted mean, tempered toward mid when few sources
    weighted = sum(active[k] * norm_w[k] for k in active)
    source_factor = min(1.0, 0.55 + 0.09 * len(active))
    calibrated = _clamp(0.5 + (weighted - 0.5) * source_factor)

    components_pct = {k: round(active[k] * 100, 1) for k in sorted(active)}

    return {
        "components": components_pct,
        "component_raw": {k: round(active[k], 4) for k in sorted(active)},
        "weights_used": {k: round(norm_w[k], 4) for k in sorted(norm_w)},
        "final_fraud_confidence": round(calibrated, 4),
        "final_percent": round(calibrated * 100, 1),
        "calibration": "multi_source_weighted",
        "source_count": len(active),
    }
