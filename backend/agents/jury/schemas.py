"""
AI-FORGE Jury Agent Schemas.

Standard JSON output format for every agent in the jury system.
Now includes ForensicFinding — the core unit of evidence for court-ready reports.
"""

from typing import Any, Dict, List, Optional, TypedDict


class AgentFinding(TypedDict, total=False):
    module: str
    what: str
    why: str
    confidence: float


class ForensicFinding(TypedDict, total=False):
    """
    The canonical per-finding evidence unit produced by jury agents.
    Every finding represents a SINGLE localized manipulation in the document.
    """
    finding_id: str            # "finding-1", "finding-2", etc.
    finding_number: int        # 1, 2, 3 (for report labeling)
    page: int                  # Page number (1-indexed)
    location: str              # Human quadrant: "Top Right", "Bottom Left", "Center"
    field_name: str            # "Wheel", "Total Amount", "Signature Block", "Policy No."
    object_type: str           # "text_field", "signature", "stamp", "logo", "number"
    detected_value: str        # What was detected: "2000", "10000", "Signature present"
    claimed_original: str      # If known: "1500", "8500", "No Signature"
    edit_type: str             # "Modified Amount", "Fake Signature", "Inserted Text", etc.
    severity: str              # "Critical", "High", "Medium", "Low"
    evidence: List[str]        # Plain-language bullets: ["Character boundaries inconsistent…"]
    technical_explanation: str # For experts: "ELA score 0.82, wavelet subband divergence"
    plain_english_explanation: str  # For non-experts
    confidence_pct: float      # 0–100
    confidence: float          # 0.0–1.0 (same value / 100)
    bbox: Dict[str, Any]       # {"x":…,"y":…,"width":…,"height":…}
    bounding_box: Dict[str, Any]
    coordinates: List[float]   # [x1, y1, x2, y2] for IoU math
    detector_votes: Dict[str, bool]   # {"ELA": True, "Noise": True, …}
    detectors: List[str]       # Active detector names
    crop_url: str              # API URL for cropped region image
    overlay_url: str           # API URL for annotated overlay image
    investigation: str         # Multi-line narrative for Evidence Inspector
    recommendation: str        # What investigator should do
    source_agent: str          # Which jury agent raised this finding


class AgentOutput(TypedDict, total=False):
    agent_id: str
    agent_name: str
    verdict: str
    confidence: float
    risk_score: float
    findings: List[AgentFinding]
    forensic_findings: List[ForensicFinding]   # NEW — structured per-region findings
    explanation: str
    signals: List[str]
    raw_scores: Dict[str, float]


class Disagreement(TypedDict, total=False):
    agents: List[str]
    issue: str
    details: str


class EvidenceRankItem(TypedDict, total=False):
    rank: int
    source: str
    module: str
    finding: str
    confidence: float
    weight: float


class ForensicDossier(TypedDict, total=False):
    """
    Top-level structured forensic report produced after all agents vote.
    This is the authoritative output for the court-ready report and UI panel.
    """
    finding_count: int
    critical_count: int
    suspicious_count: int
    verify_count: int
    findings: List[ForensicFinding]   # Ranked by confidence, numbered 1..N
    overall_risk_pct: float
    overall_verdict: str
    generated_at: str


class FusionOutput(TypedDict, total=False):
    final_verdict: str
    confidence: float
    confidence_pct: float
    risk_score: float
    risk_score_pct: float
    risk_level: str
    reasoning: str
    weighted_scores: Dict[str, float]
    majority_vote: Dict[str, Any]
    minority_opinion: List[Dict[str, Any]]
    confidence_distribution: Dict[str, Any]
    evidence_ranking: List[EvidenceRankItem]
    disagreements: List[Disagreement]
    report: Dict[str, Any]


class JuryResult(TypedDict, total=False):
    success: bool
    evidence_id: Optional[str]
    filename: Optional[str]
    agents: Dict[str, AgentOutput]
    fusion: FusionOutput
    forensic_dossier: ForensicDossier   # NEW — top-level structured findings
    generated_at: str
