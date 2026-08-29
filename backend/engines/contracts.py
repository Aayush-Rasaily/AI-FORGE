"""
Production forensic engine contracts.

Every detector MUST emit DetectorOutput. Fusion and Explain engines
consume ONLY these structures — never free-form hallucination.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class AffectedRegion(TypedDict, total=False):
    id: str
    x: int
    y: int
    width: int
    height: int
    score: float
    label: str


class DetectorOutput(TypedDict, total=False):
    detector_name: str
    confidence: float  # 0–1
    score: float  # manipulation likelihood 0–1
    affected_regions: List[AffectedRegion]
    technical_reason: str
    metrics: Dict[str, Any]
    reliability: float  # detector trust weight 0–1
    status: str  # ok | skipped | failed
    error: Optional[str]


class Citation(TypedDict, total=False):
    detector_name: str
    confidence: float
    technical_reason: str
    score: float
    region_id: Optional[str]


class FusionResult(TypedDict, total=False):
    overall_score: float  # 0–100
    confidence: float  # 0–100
    verdict: str
    detector_contributions: List[Dict[str, Any]]
    elevated_detectors: List[str]
    strong_detectors: List[str]
    weighted_votes: Dict[str, float]
    reasoning: str
    citations: List[Citation]


class ReasoningFinding(TypedDict, total=False):
    id: str
    finding: str
    supporting_evidence: List[Dict[str, Any]]
    confidence: float
    contradictory_evidence: List[Dict[str, Any]]
    recommendation: str
    priority: int
    evidence_node_ids: List[str]


class ForensicReasoningResult(TypedDict, total=False):
    version: int
    primary_finding: str
    primary_confidence: float
    findings: List[ReasoningFinding]
    graph: Dict[str, Any]
    narrative: str
    recommendation: str
    inference_chain: List[Dict[str, str]]


# Empirical reliability priors (production-calibrated, not hard-coded scores)
DETECTOR_RELIABILITY: Dict[str, float] = {
    "copy_move": 0.92,
    "ela": 0.88,
    "wavelet": 0.82,
    "noise": 0.78,
    "metadata": 0.70,
    "edge": 0.65,
    "ocr": 0.80,
    "font": 0.75,
    "spacing": 0.72,
    "region_anomaly": 0.74,
    "tampering": 0.85,
    "deepfake": 0.86,
    "gan": 0.84,
    "ai_generation": 0.83,
    "jpeg_block": 0.76,
    "frequency": 0.74,
    "rgb": 0.60,
    "hsv": 0.58,
    "lab": 0.58,
    "ycbcr": 0.62,
    "face_forensics": 0.86,
    "color_channel": 0.68,
    "attention": 0.70,
    "segmentation": 0.72,
    "object_consistency": 0.70,
}


def _default_reliability(detector_name: str) -> float:
    try:
        from backend.learning.weighting import get_detector_reliability
        return get_detector_reliability(detector_name)
    except Exception:
        name = str(detector_name).strip().lower().replace(" ", "_")
        return DETECTOR_RELIABILITY.get(name, 0.65)


def make_detector_output(
    detector_name: str,
    *,
    score: float = 0.0,
    confidence: float = 0.5,
    technical_reason: str = "",
    affected_regions: Optional[List[AffectedRegion]] = None,
    metrics: Optional[Dict[str, Any]] = None,
    reliability: Optional[float] = None,
    status: str = "ok",
    error: Optional[str] = None,
) -> DetectorOutput:
    name = str(detector_name).strip().lower().replace(" ", "_")
    score_f = max(0.0, min(1.0, float(score)))
    conf_f = max(0.0, min(1.0, float(confidence)))
    rel = reliability if reliability is not None else _default_reliability(name)
    return {
        "detector_name": name,
        "score": round(score_f, 4),
        "confidence": round(conf_f, 4),
        "technical_reason": (technical_reason or "").strip(),
        "affected_regions": affected_regions or [],
        "metrics": metrics or {},
        "reliability": round(max(0.0, min(1.0, float(rel))), 4),
        "status": status,
        "error": error,
    }


def skipped_detector(detector_name: str, reason: str) -> DetectorOutput:
    return make_detector_output(
        detector_name,
        score=0.0,
        confidence=0.0,
        technical_reason=reason,
        status="skipped",
    )


def failed_detector(detector_name: str, error: str) -> DetectorOutput:
    return make_detector_output(
        detector_name,
        score=0.0,
        confidence=0.3,
        technical_reason=f"Detector unavailable: {error}",
        status="failed",
        error=str(error)[:500],
    )
