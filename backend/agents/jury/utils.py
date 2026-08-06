"""
Shared utilities for jury agents.
"""

from typing import Any, Dict, List, Optional


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def verdict_from_score(score: float) -> str:
    if score >= 0.70:
        return "Manipulated"
    if score >= 0.45:
        return "Suspicious"
    if score >= 0.25:
        return "Potentially Altered"
    return "Authentic"


def normalize_verdict(verdict: str) -> str:
    v = str(verdict or "").lower()
    if any(k in v for k in ("manipul", "forg", "fake", "suspicious", "highly")):
        return "risk"
    if any(k in v for k in ("authentic", "genuine", "clean", "no_strong")):
        return "authentic"
    return "uncertain"


def build_finding(
    module: str,
    what: str,
    why: str,
    confidence: float,
) -> Dict[str, Any]:
    return {
        "module": module,
        "what": what,
        "why": why,
        "confidence": round(clamp(confidence), 4),
    }
