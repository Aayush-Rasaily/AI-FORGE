"""
Lightweight RAG knowledge store for investigation Q&A / similarity search.
Uses local embedding-free TF-IDF style scoring (no external API required).
"""

from __future__ import annotations

import json
import logging
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.agents.investigation.base import AgentResult

logger = logging.getLogger("ai_forge.knowledge")

KB_ROOT = Path("data/knowledge")
KB_DOCS = KB_ROOT / "documents.jsonl"

_TOKEN = re.compile(r"[a-z0-9]{3,}")


def _ensure() -> None:
    KB_ROOT.mkdir(parents=True, exist_ok=True)


def _tokenize(text: str) -> List[str]:
    return _TOKEN.findall((text or "").lower())


def index_investigation(
    evidence_id: str,
    judge: AgentResult,
    reasoning: AgentResult,
    correlation: Dict[str, Any],
) -> Dict[str, Any]:
    _ensure()
    parts = [
        f"Evidence {evidence_id}",
        f"Verdict {judge.verdict}",
        judge.reason or "",
        reasoning.reason or "",
        (reasoning.data or {}).get("explanation") or "",
        correlation.get("cross_modal_summary") or "",
    ]
    for inc in correlation.get("inconsistencies") or []:
        parts.append(str(inc.get("explanation") or ""))
        parts.append(str(inc.get("type") or ""))

    text = "\n".join(p for p in parts if p)
    doc = {
        "id": f"inv-{evidence_id}",
        "evidence_id": evidence_id,
        "text": text,
        "tokens": _tokenize(text),
        "verdict": judge.verdict,
        "risk_score": judge.risk_score,
        "indexed_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(KB_DOCS, "a", encoding="utf-8") as f:
        f.write(json.dumps(doc, default=str) + "\n")
    return {"indexed": True, "id": doc["id"]}


def _load_docs(limit: int = 2000) -> List[Dict[str, Any]]:
    _ensure()
    if not KB_DOCS.exists():
        return []
    docs = []
    with open(KB_DOCS, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                docs.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    # Keep latest per evidence_id
    latest: Dict[str, Dict] = {}
    for d in docs:
        latest[d.get("evidence_id") or d.get("id")] = d
    return list(latest.values())[-limit:]


def search_knowledge(query: str, *, top_k: int = 5) -> List[Dict[str, Any]]:
    """Simple TF overlap retrieval — production-safe offline RAG."""
    q_tokens = _tokenize(query)
    if not q_tokens:
        return []
    q_counts = Counter(q_tokens)
    results = []
    for doc in _load_docs():
        d_tokens = doc.get("tokens") or _tokenize(doc.get("text") or "")
        if not d_tokens:
            continue
        d_counts = Counter(d_tokens)
        overlap = sum(min(q_counts[t], d_counts[t]) for t in q_counts)
        if overlap <= 0:
            continue
        # length-normalized score
        score = overlap / math.sqrt(len(d_tokens))
        results.append({
            "evidence_id": doc.get("evidence_id"),
            "verdict": doc.get("verdict"),
            "risk_score": doc.get("risk_score"),
            "score": round(score, 4),
            "snippet": (doc.get("text") or "")[:280],
        })
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def answer_copilot(question: str, *, evidence_id: Optional[str] = None) -> Dict[str, Any]:
    """Investigator copilot — retrieve + compose grounded answer."""
    hits = search_knowledge(question, top_k=5)
    if evidence_id:
        # Prefer current evidence memory
        local = [h for h in hits if h.get("evidence_id") == evidence_id]
        hits = local + [h for h in hits if h.get("evidence_id") != evidence_id]

    if not hits:
        return {
            "answer": (
                "I do not yet have indexed investigations matching that question. "
                "Run Autonomous Investigate on evidence to build the knowledge base."
            ),
            "sources": [],
            "evidence_id": evidence_id,
        }

    top = hits[0]
    answer = (
        f"Based on prior investigation {top.get('evidence_id')}: "
        f"verdict was {top.get('verdict')} "
        f"(risk {round(float(top.get('risk_score') or 0) * 100, 1)}%). "
        f"Relevant context: {top.get('snippet')}"
    )
    if "signature" in question.lower():
        answer += " Use Signature Verification with a reference pair for definitive match scoring."
    if "metadata" in question.lower():
        answer += " Review Metadata Agent findings and EXIF/software/GPS fields in the investigation timeline."

    return {
        "answer": answer,
        "sources": hits,
        "evidence_id": evidence_id,
        "mode": "rag_local",
    }
