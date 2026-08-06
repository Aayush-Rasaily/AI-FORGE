"""
Hybrid weighted fusion — CNN + handcrafted forensic signals.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


TAMPERING_WEIGHTS: Dict[str, float] = {
    "cnn": 0.40,
    "ela": 0.20,
    "copy_move": 0.15,
    "wavelet": 0.10,
    "edge": 0.10,
    "metadata": 0.05,
}


def fuse_hybrid_tampering(
    scores: Dict[str, float],
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Fuse tampering module scores using fixed weights.

    Parameters
    ----------
    scores : dict
        Keys: cnn, ela, copy_move, wavelet, edge, metadata (0.0–1.0).
    """
    weights = weights or TAMPERING_WEIGHTS
    total_w = sum(weights.values()) or 1.0
    fused = 0.0
    breakdown: Dict[str, float] = {}

    for key, weight in weights.items():
        val = max(0.0, min(1.0, float(scores.get(key, 0.0))))
        contribution = val * weight / total_w
        breakdown[key] = round(contribution, 4)
        fused += contribution

    fused = max(0.0, min(1.0, fused))

    if fused >= 0.70:
        verdict, severity = "LIKELY_TAMPERED", "HIGH"
    elif fused >= 0.45:
        verdict, severity = "SUSPICIOUS", "MEDIUM"
    elif fused >= 0.20:
        verdict, severity = "MINOR_ANOMALY", "LOW"
    else:
        verdict, severity = "NO_STRONG_TAMPERING_SIGNAL", "LOW"

    confidence = round(55 + fused * 40, 2)

    return {
        "tampering_score": round(fused, 4),
        "tampering_percentage": round(fused * 100, 2),
        "confidence": confidence,
        "verdict": verdict,
        "severity": severity,
        "fusion_weights": weights,
        "score_breakdown": breakdown,
    }


def fuse_weighted_evidence(
    modules: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Weighted jury-style fusion using score × confidence × reliability.

    Each module dict: {name, score, confidence, importance, reliability}
    """
    if not modules:
        return {"risk_score": 0.0, "confidence": 0.0, "verdict": "UNKNOWN"}

    total = 0.0
    weight_sum = 0.0
    for mod in modules:
        score = max(0.0, min(1.0, float(mod.get("score", 0.0))))
        conf = max(0.0, min(1.0, float(mod.get("confidence", 0.5))))
        rel = max(0.0, min(1.0, float(mod.get("reliability", 0.5))))
        imp = max(0.0, min(1.0, float(mod.get("importance", 0.5))))
        w = conf * rel * imp
        total += score * w
        weight_sum += w

    risk = total / weight_sum if weight_sum > 0 else 0.0
    risk_pct = round(risk * 100, 2)

    if risk_pct >= 70:
        verdict = "HIGH RISK"
    elif risk_pct >= 45:
        verdict = "MEDIUM RISK"
    elif risk_pct >= 20:
        verdict = "LOW RISK"
    else:
        verdict = "NO SIGNIFICANT ANOMALY"

    return {
        "risk_score": risk_pct,
        "confidence": round(55 + risk * 40, 2),
        "verdict": verdict,
    }
