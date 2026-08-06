"""
AI-FORGE Jury Agent Schemas.

Standard JSON output format for every agent in the jury system.
Designed to be LLM-replaceable in future versions.
"""

from typing import Any, Dict, List, Optional, TypedDict


class AgentFinding(TypedDict, total=False):
    module: str
    what: str
    why: str
    confidence: float


class AgentOutput(TypedDict, total=False):
    agent_id: str
    agent_name: str
    verdict: str
    confidence: float
    risk_score: float
    findings: List[AgentFinding]
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
    generated_at: str
