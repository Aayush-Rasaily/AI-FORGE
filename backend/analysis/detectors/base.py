"""
Standard detector result contract for forensic modules.

Prefer backend.engines.contracts.DetectorOutput for new code.
This module remains for backward compatibility with multispectral detectors.
"""

from __future__ import annotations

from typing import Any, Dict, List, TypedDict


class DetectorResult(TypedDict, total=False):
    score: float
    confidence: float
    explanation: str
    detector: str
    detector_name: str
    technical_reason: str
    affected_regions: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    details: Dict[str, Any]


def make_result(
    detector: str,
    score: float,
    confidence: float,
    explanation: str,
    **details: Any,
) -> DetectorResult:
    return {
        "detector": detector,
        "detector_name": detector,
        "score": round(max(0.0, min(1.0, float(score))), 4),
        "confidence": round(max(0.0, min(1.0, float(confidence))), 4),
        "explanation": explanation,
        "technical_reason": explanation,
        "affected_regions": details.pop("affected_regions", []) if "affected_regions" in details else [],
        "metrics": details.pop("metrics", {}) if "metrics" in details else {},
        "details": details,
    }


def failed_result(detector: str, error: str) -> DetectorResult:
    return make_result(
        detector,
        score=0.0,
        confidence=0.3,
        explanation=f"Analysis unavailable: {error}",
        error=error,
    )
