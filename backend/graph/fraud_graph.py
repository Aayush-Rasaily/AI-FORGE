"""
Fraud relationship graph — nodes/edges persisted as JSON for visualization.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.agents.investigation.base import AgentResult
from backend.evidence.paths import find_evidence_file
from backend.utils.file_hash import compute_file_hash

logger = logging.getLogger("ai_forge.graph")

GRAPH_ROOT = Path("data/graph")
GRAPH_FILE = GRAPH_ROOT / "fraud_graph.json"


def _ensure() -> None:
    GRAPH_ROOT.mkdir(parents=True, exist_ok=True)


def _load() -> Dict[str, Any]:
    _ensure()
    if not GRAPH_FILE.exists():
        return {"nodes": {}, "edges": [], "updated_at": None}
    try:
        with open(GRAPH_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"nodes": {}, "edges": [], "updated_at": None}


def _save(graph: Dict[str, Any]) -> None:
    _ensure()
    graph["updated_at"] = datetime.now(timezone.utc).isoformat()
    tmp = GRAPH_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, default=str)
    if GRAPH_FILE.exists():
        GRAPH_FILE.unlink(missing_ok=True)
    tmp.replace(GRAPH_FILE)


def upsert_investigation_graph(
    evidence_id: str,
    judge: AgentResult,
    agents: Dict[str, AgentResult],
    correlation: Dict[str, Any],
) -> Dict[str, Any]:
    graph = _load()
    nodes = graph.setdefault("nodes", {})
    edges = graph.setdefault("edges", [])

    evid_node = f"evidence:{evidence_id}"
    nodes[evid_node] = {
        "id": evid_node,
        "type": "evidence",
        "label": evidence_id,
        "verdict": judge.verdict,
        "risk_score": judge.risk_score,
    }

    case_node = f"investigation:{evidence_id}"
    nodes[case_node] = {
        "id": case_node,
        "type": "investigation",
        "label": f"Investigation {evidence_id}",
        "verdict": judge.verdict,
    }
    edges.append({
        "source": case_node,
        "target": evid_node,
        "relation": "analyzes",
    })

    path = find_evidence_file(evidence_id)
    if path:
        try:
            h = compute_file_hash(Path(path))
            hash_node = f"hash:{h[:16]}"
            nodes[hash_node] = {"id": hash_node, "type": "hash", "label": h[:16], "full": h}
            edges.append({"source": evid_node, "target": hash_node, "relation": "has_hash"})
            prior = [
                e["source"] for e in edges
                if e.get("target") == hash_node
                and e.get("source", "").startswith("evidence:")
                and e.get("source") != evid_node
            ]
            for other in prior:
                edges.append({
                    "source": evid_node,
                    "target": other,
                    "relation": "duplicate_of",
                    "detail": "Shared file hash",
                })
        except Exception:
            pass

    for inc in correlation.get("inconsistencies") or []:
        inc_id = f"signal:{evidence_id}:{inc.get('type')}"
        nodes[inc_id] = {
            "id": inc_id,
            "type": "inconsistency",
            "label": inc.get("type"),
            "severity": inc.get("severity"),
        }
        edges.append({"source": evid_node, "target": inc_id, "relation": "exhibits"})

    for aid, agent in agents.items():
        if agent.status != "completed":
            continue
        anode = f"agent:{aid}"
        nodes[anode] = {"id": anode, "type": "agent", "label": agent.agent_name}
        edges.append({
            "source": case_node,
            "target": anode,
            "relation": "used_agent",
            "verdict": agent.verdict,
        })

    # Deduplicate edges loosely
    seen = set()
    unique_edges = []
    for e in edges:
        key = (e.get("source"), e.get("target"), e.get("relation"))
        if key in seen:
            continue
        seen.add(key)
        unique_edges.append(e)
    graph["edges"] = unique_edges[-5000:]
    _save(graph)
    return {"nodes": len(nodes), "edges": len(graph["edges"])}


def get_fraud_graph(*, limit_nodes: int = 200) -> Dict[str, Any]:
    graph = _load()
    nodes = list((graph.get("nodes") or {}).values())[-limit_nodes:]
    node_ids = {n["id"] for n in nodes}
    edges = [
        e for e in (graph.get("edges") or [])
        if e.get("source") in node_ids and e.get("target") in node_ids
    ]
    return {
        "nodes": nodes,
        "edges": edges[-1000:],
        "updated_at": graph.get("updated_at"),
        "stats": {
            "node_count": len(graph.get("nodes") or {}),
            "edge_count": len(graph.get("edges") or []),
        },
    }
