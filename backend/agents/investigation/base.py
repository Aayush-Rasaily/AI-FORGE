"""
Agentic investigation — shared types and base agent contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AgentResult:
    agent_id: str
    agent_name: str
    status: str = "completed"  # pending | running | completed | skipped | failed
    confidence: float = 0.0
    risk_score: float = 0.0
    verdict: Optional[str] = None
    findings: List[str] = field(default_factory=list)
    skipped_modules: List[str] = field(default_factory=list)
    executed_modules: List[str] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    error: Optional[str] = None
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "status": self.status,
            "confidence": round(float(self.confidence), 4),
            "risk_score": round(float(self.risk_score), 4),
            "verdict": self.verdict,
            "findings": self.findings,
            "skipped_modules": self.skipped_modules,
            "executed_modules": self.executed_modules,
            "duration_ms": round(self.duration_ms, 1),
            "error": self.error,
            "reason": self.reason,
            "data": self.data,
        }


@dataclass
class InvestigationPlan:
    evidence_id: str
    evidence_type: str
    profile: str
    modules: List[str]
    agents: List[str]
    skip_reasons: Dict[str, str] = field(default_factory=dict)
    priorities: List[str] = field(default_factory=list)
    estimated_seconds: float = 10.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type,
            "profile": self.profile,
            "modules": self.modules,
            "agents": self.agents,
            "skip_reasons": self.skip_reasons,
            "priorities": self.priorities,
            "estimated_seconds": self.estimated_seconds,
        }


@dataclass
class TimelineEvent:
    stage: str
    agent: Optional[str]
    status: str
    message: str
    timestamp: str = field(default_factory=utc_now)
    duration_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "agent": self.agent,
            "status": self.status,
            "message": self.message,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
        }
