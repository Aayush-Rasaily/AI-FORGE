"""
Case Memory — store investigation outcomes for future comparison.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.agents.investigation.base import AgentResult
from backend.utils.file_hash import compute_file_hash
from backend.evidence.paths import find_evidence_file, get_analysis_dir

logger = logging.getLogger("ai_forge.memory")

MEMORY_ROOT = Path("data/memory")
MEMORY_INDEX = MEMORY_ROOT / "investigations.jsonl"


def _ensure() -> None:
    MEMORY_ROOT.mkdir(parents=True, exist_ok=True)


def remember_investigation(
    evidence_id: str,
    judge: AgentResult,
    agents: Dict[str, AgentResult],
    correlation: Dict[str, Any],
) -> Dict[str, Any]:
    _ensure()
    path = find_evidence_file(evidence_id)
    file_hash = None
    try:
        if path:
            file_hash = compute_file_hash(Path(path))
    except Exception:
        pass

    features = {
        "verdict": judge.verdict,
        "risk_score": judge.risk_score,
        "confidence": judge.confidence,
        "agent_verdicts": {
            k: {"verdict": v.verdict, "risk": v.risk_score, "status": v.status}
            for k, v in agents.items()
        },
        "inconsistency_types": [
            i.get("type") for i in (correlation.get("inconsistencies") or [])
        ],
    }

    record = {
        "evidence_id": evidence_id,
        "file_hash": file_hash,
        "features": features,
        "stored_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(MEMORY_INDEX, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")

    # Also mirror into analysis dir
    try:
        adir = get_analysis_dir(evidence_id, create=True)
        with open(adir / "case_memory.json", "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)
    except Exception as exc:
        logger.debug("case_memory mirror skipped: %s", exc)

    return record


def list_memories(limit: int = 100) -> List[Dict[str, Any]]:
    _ensure()
    if not MEMORY_INDEX.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with open(MEMORY_INDEX, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows[-limit:]


def find_similar_by_hash(file_hash: str) -> List[Dict[str, Any]]:
    if not file_hash:
        return []
    return [r for r in list_memories(500) if r.get("file_hash") == file_hash]


def find_similar_investigations(
    evidence_id: str,
    *,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Heuristic similarity: shared inconsistency types / nearby risk."""
    memories = list_memories(500)
    current = next((m for m in reversed(memories) if m.get("evidence_id") == evidence_id), None)
    if not current:
        return []

    cur_feat = current.get("features") or {}
    cur_types = set(cur_feat.get("inconsistency_types") or [])
    cur_risk = float(cur_feat.get("risk_score") or 0)
    scored = []
    for m in memories:
        if m.get("evidence_id") == evidence_id:
            continue
        feat = m.get("features") or {}
        types = set(feat.get("inconsistency_types") or [])
        overlap = len(cur_types & types)
        risk_delta = abs(float(feat.get("risk_score") or 0) - cur_risk)
        score = overlap * 2.0 + max(0.0, 1.0 - risk_delta)
        if m.get("file_hash") and m.get("file_hash") == current.get("file_hash"):
            score += 5.0
        if score > 0.5:
            scored.append({**m, "similarity_score": round(score, 3)})
    scored.sort(key=lambda x: x["similarity_score"], reverse=True)
    return scored[:limit]
