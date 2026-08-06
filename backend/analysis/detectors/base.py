"""
Standard detector result contract for forensic modules.
"""

from __future__ import annotations

from typing import Any, Dict, List, TypedDict


class DetectorResult(TypedDict, total=False):
    score: float
    confidence: float
    explanation: str
    detector: str
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
        "score": round(max(0.0, min(1.0, float(score))), 4),
        "confidence": round(max(0.0, min(1.0, float(confidence))), 4),
        "explanation": explanation,
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
