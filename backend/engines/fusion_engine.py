"""
Evidence Fusion Engine — weighted detector confidence (not majority-only).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.engines.contracts import Citation, DetectorOutput, FusionResult


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def fuse_detector_outputs(
    detectors: List[DetectorOutput],
    *,
    profile: str = "natural_photo",
) -> FusionResult:
    """
    Weighted fusion:
      contribution_i = score_i * confidence_i * reliability_i
      overall = sum(contribution) / sum(confidence * reliability)  for active detectors
    """
    active = [d for d in detectors if d.get("status") == "ok"]
    if not active:
        return {
            "overall_score": 0.0,
            "confidence": 40.0,
            "verdict": "INSUFFICIENT DETECTOR EVIDENCE",
            "detector_contributions": [],
            "elevated_detectors": [],
            "strong_detectors": [],
            "weighted_votes": {},
            "reasoning": "No active forensic detectors produced usable outputs.",
            "citations": [],
        }

    contributions: List[Dict[str, Any]] = []
    weighted_votes: Dict[str, float] = {}
    numer = 0.0
    denom = 0.0
    citations: List[Citation] = []

    for d in active:
        score = _clamp01(d.get("score", 0))
        conf = _clamp01(d.get("confidence", 0.5))
        rel = _clamp01(d.get("reliability", 0.65))
        weight = conf * rel
        contrib = score * weight
        numer += contrib
        denom += weight
        name = d.get("detector_name", "unknown")
        weighted_votes[name] = round(contrib, 4)
        contributions.append({
            "detector_name": name,
            "score": round(score, 4),
            "confidence": round(conf, 4),
            "reliability": round(rel, 4),
            "weight": round(weight, 4),
            "contribution": round(contrib, 4),
            "technical_reason": d.get("technical_reason") or "",
            "status": d.get("status"),
        })
        if score >= 0.28 and d.get("technical_reason"):
            citations.append({
                "detector_name": name,
                "confidence": round(conf, 4),
                "technical_reason": d.get("technical_reason") or "",
                "score": round(score, 4),
            })

    overall01 = _clamp01(numer / denom) if denom > 0 else 0.0

    elevated = [c["detector_name"] for c in contributions if c["score"] >= 0.28]
    strong = [c["detector_name"] for c in contributions if c["score"] >= 0.42]

    # Forensic consensus rules (evidence-driven, not decorative)
    if len(strong) >= 3:
        overall01 = max(overall01, 0.62)
    if len(elevated) >= 4:
        overall01 = max(overall01, 0.55)
    if len(elevated) >= 2:
        overall01 = max(overall01, 0.40)
    # Triad: ela + copy_move + noise
    names = {c["detector_name"]: c["score"] for c in contributions}
    if (
        names.get("ela", 0) >= 0.30
        and names.get("copy_move", 0) >= 0.30
        and names.get("noise", 0) >= 0.28
    ):
        overall01 = max(overall01, 0.72)

    if len(elevated) == 0 and max((c["score"] for c in contributions), default=0) < 0.22:
        overall01 = min(overall01, 0.15)

    overall_pct = round(overall01 * 100, 2)

    # Confidence = agreement among elevated detectors + mean detector confidence
    mean_conf = sum(c["confidence"] for c in contributions) / max(1, len(contributions))
    agreement = min(1.0, len(elevated) / max(1, len(contributions)) + len(strong) * 0.08)
    conf_pct = round(min(99.5, (mean_conf * 55 + agreement * 40 + min(10, len(elevated) * 2))), 2)

    if overall_pct >= 70:
        verdict = "HIGH RISK — LIKELY MANIPULATED"
    elif overall_pct >= 45:
        verdict = "MEDIUM RISK — SUSPICIOUS"
    elif overall_pct >= 20:
        verdict = "LOW RISK — MINOR ANOMALIES"
    else:
        verdict = "NO SIGNIFICANT ANOMALY DETECTED"

    # Never claim clean when 2+ detectors elevate
    if len(elevated) >= 2 and "NO SIGNIFICANT" in verdict:
        verdict = "MEDIUM RISK — SUSPICIOUS"
        overall_pct = max(overall_pct, 42.0)

    contributions.sort(key=lambda c: c["contribution"], reverse=True)
    reasoning = (
        f"Weighted fusion across {len(active)} detectors "
        f"({len(elevated)} elevated, {len(strong)} strong). "
        f"Profile={profile}."
    )

    return {
        "overall_score": overall_pct,
        "confidence": conf_pct,
        "verdict": verdict,
        "detector_contributions": contributions,
        "elevated_detectors": elevated,
        "strong_detectors": strong,
        "weighted_votes": weighted_votes,
        "reasoning": reasoning,
        "citations": citations,
    }
