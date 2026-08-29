"""
Case-scoped evidence graph persistence.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ai_forge.graph.evidence")

GRAPH_ROOT = Path("data/graph/cases")


def _case_path(case_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in case_id)
    return GRAPH_ROOT / f"{safe}.json"


def load_case_graph(case_id: str) -> Dict[str, Any]:
    path = _case_path(case_id)
    if not path.is_file():
        return _empty_graph(case_id)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _empty_graph(case_id)


def save_case_graph(case_id: str, graph: Dict[str, Any]) -> Dict[str, Any]:
    GRAPH_ROOT.mkdir(parents=True, exist_ok=True)
    graph["case_id"] = case_id
    graph["updated_at"] = datetime.now(timezone.utc).isoformat()
    path = _case_path(case_id)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(graph, indent=2, default=str), encoding="utf-8")
    if path.exists():
        path.unlink(missing_ok=True)
    tmp.replace(path)
    return graph


def _empty_graph(case_id: str) -> Dict[str, Any]:
    return {
        "case_id": case_id,
        "nodes": [],
        "edges": [],
        "findings": [],
        "chains": [],
        "stats": {"node_count": 0, "edge_count": 0, "finding_count": 0},
        "updated_at": None,
    }


def graph_for_api(graph: Dict[str, Any], *, focus_evidence_id: Optional[str] = None) -> Dict[str, Any]:
    """Return graph payload optimized for frontend visualization."""
    nodes = list(graph.get("nodes") or [])
    edges = list(graph.get("edges") or [])

    if focus_evidence_id:
        focus = f"evidence:{focus_evidence_id}"
        related_ids = {focus}
        for e in edges:
            if e.get("source") == focus or e.get("target") == focus:
                related_ids.add(e.get("source"))
                related_ids.add(e.get("target"))
        for hop in edges:
            if hop.get("source") in related_ids or hop.get("target") in related_ids:
                related_ids.add(hop.get("source"))
                related_ids.add(hop.get("target"))
        nodes = [n for n in nodes if n.get("id") in related_ids]
        node_ids = {n["id"] for n in nodes}
        edges = [
            e for e in edges
            if e.get("source") in node_ids and e.get("target") in node_ids
        ]

    return {
        "case_id": graph.get("case_id"),
        "nodes": nodes,
        "edges": edges,
        "findings": graph.get("findings") or [],
        "chains": graph.get("chains") or [],
        "stats": graph.get("stats") or {},
        "updated_at": graph.get("updated_at"),
    }
