"""
Autonomous Investigation API — additive endpoints (do not replace /evidence/analyze*).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.evidence.paths import find_evidence_file
from backend.graph.fraud_graph import get_fraud_graph
from backend.knowledge.rag_store import search_knowledge
from backend.memory.case_memory import find_similar_investigations, list_memories
from backend.pipelines.investigation_pipeline import investigate_evidence, load_investigation

logger = logging.getLogger("ai_forge.api.investigate")

router = APIRouter(prefix="/api", tags=["Autonomous Investigation"])


class CopilotRequest(BaseModel):
    question: str = Field(..., min_length=2)
    evidence_id: Optional[str] = None


@router.post("/investigate/{evidence_id}")
async def investigate_endpoint(
    evidence_id: str,
    force_deep: bool = Query(False, description="Force deep modules (faces, signature, etc.)"),
):
    """
    Autonomous AI investigation — Chief Investigator decides modules/agents.
    Existing /evidence/analyze* endpoints remain unchanged.
    """
    path = find_evidence_file(evidence_id)
    if path is None:
        raise HTTPException(status_code=404, detail="Evidence not found. Upload first.")

    try:
        result = await asyncio.to_thread(
            investigate_evidence,
            evidence_id,
            force_deep=force_deep,
        )
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Investigation failed for %s", evidence_id)
        return {
            "success": False,
            "status": "failed",
            "evidence_id": evidence_id,
            "reason": str(exc)[:800],
        }


@router.get("/investigate/{evidence_id}")
async def get_investigation(evidence_id: str):
    data = load_investigation(evidence_id)
    if not data:
        raise HTTPException(status_code=404, detail="Investigation not found. Run POST /api/investigate/{id}.")
    return data


@router.get("/investigate/{evidence_id}/timeline")
async def get_investigation_timeline(evidence_id: str):
    data = load_investigation(evidence_id)
    if not data:
        raise HTTPException(status_code=404, detail="Investigation not found.")
    return {
        "success": True,
        "evidence_id": evidence_id,
        "timeline": data.get("timeline") or [],
        "verdict": data.get("verdict"),
    }


@router.get("/investigate/{evidence_id}/agents")
async def get_investigation_agents(evidence_id: str):
    data = load_investigation(evidence_id)
    if not data:
        raise HTTPException(status_code=404, detail="Investigation not found.")
    return {
        "success": True,
        "evidence_id": evidence_id,
        "agents": data.get("agents") or {},
        "plan": data.get("plan"),
    }


@router.get("/memory/investigations")
async def memory_list(limit: int = Query(50, ge=1, le=500)):
    return {"success": True, "items": list_memories(limit)}


@router.get("/memory/similar/{evidence_id}")
async def memory_similar(evidence_id: str, limit: int = Query(5, ge=1, le=20)):
    return {
        "success": True,
        "evidence_id": evidence_id,
        "similar": find_similar_investigations(evidence_id, limit=limit),
    }


@router.get("/knowledge/search")
async def knowledge_search(q: str = Query(..., min_length=2), top_k: int = Query(5, ge=1, le=20)):
    return {"success": True, "query": q, "results": search_knowledge(q, top_k=top_k)}


@router.post("/copilot/ask")
async def copilot_ask(body: CopilotRequest):
    """Legacy endpoint — delegates to grounded copilot engine."""
    from backend.engines.copilot_engine import answer_with_context

    if not body.evidence_id:
        return {
            "success": False,
            "answer": "evidence_id is required for grounded copilot responses.",
            "sources": [],
        }
    result = answer_with_context(body.question, body.evidence_id)
    return {"success": True, **result}


@router.get("/graph/fraud")
async def fraud_graph(limit_nodes: int = Query(200, ge=10, le=1000)):
    return {"success": True, **get_fraud_graph(limit_nodes=limit_nodes)}
