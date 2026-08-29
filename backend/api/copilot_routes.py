"""
AI Investigator Copilot API — grounded chat with per-investigation memory.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.engines.copilot_engine import answer_with_context, load_investigation_context

logger = logging.getLogger("ai_forge.api.copilot")

router = APIRouter(prefix="/api/copilot", tags=["AI Investigator Copilot"])

# In-memory session store: session_id -> {evidence_id, messages[], updated_at}
_SESSIONS: Dict[str, Dict[str, Any]] = {}
_SESSION_TTL_SEC = 60 * 60 * 8  # 8 hours


class CopilotMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str
    intent: Optional[str] = None


class CopilotChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: Optional[str] = None
    history: Optional[List[CopilotMessage]] = None


def _prune_sessions() -> None:
    now = time.time()
    stale = [sid for sid, s in _SESSIONS.items() if now - s.get("updated_at", 0) > _SESSION_TTL_SEC]
    for sid in stale:
        _SESSIONS.pop(sid, None)


def _get_or_create_session(session_id: Optional[str], evidence_id: str) -> str:
    _prune_sessions()
    if session_id and session_id in _SESSIONS:
        sess = _SESSIONS[session_id]
        if sess.get("evidence_id") == evidence_id:
            return session_id
    sid = session_id or str(uuid.uuid4())
    _SESSIONS[sid] = {
        "evidence_id": evidence_id,
        "messages": [],
        "updated_at": time.time(),
    }
    return sid


@router.post("/{evidence_id}/chat")
async def copilot_chat(evidence_id: str, body: CopilotChatRequest):
    """
    Ask the AI Investigator a natural-language question.
    Answers are grounded in detector outputs, fusion, localization, jury, and reports.
    """
    session_id = _get_or_create_session(body.session_id, evidence_id)
    sess = _SESSIONS[session_id]

    # Build history from session + optional client history
    history: List[Dict[str, Any]] = []
    for msg in sess.get("messages") or []:
        history.append({"role": msg["role"], "content": msg["content"], "intent": msg.get("intent")})
    if body.history:
        for m in body.history:
            history.append({"role": m.role, "content": m.content, "intent": m.intent})

    result = answer_with_context(body.message, evidence_id, history=history)

    sess["messages"].append({"role": "user", "content": body.message, "intent": None})
    sess["messages"].append({
        "role": "assistant",
        "content": result.get("answer", ""),
        "intent": result.get("intent"),
        "actions": result.get("actions"),
    })
    # Cap memory
    if len(sess["messages"]) > 40:
        sess["messages"] = sess["messages"][-40:]
    sess["updated_at"] = time.time()

    return {
        "success": True,
        "session_id": session_id,
        "message": result.get("answer"),
        "intent": result.get("intent"),
        "sources": result.get("sources") or [],
        "evidence": result.get("evidence") or [],
        "actions": result.get("actions") or {},
        "confidence": result.get("confidence"),
        "grounded": True,
    }


@router.get("/{evidence_id}/context")
async def copilot_context(evidence_id: str):
    """Return available grounded data summary for the copilot."""
    ctx = load_investigation_context(evidence_id)
    return {
        "success": True,
        "evidence_id": evidence_id,
        "has_analysis": bool(ctx.get("analysis")),
        "region_count": len(ctx.get("regions") or []),
        "has_reasoning": bool(ctx.get("forensic_reasoning")),
        "has_jury": bool(ctx.get("jury")),
        "has_explainable": bool(ctx.get("explainable_ai")),
        "verdict": (
            ctx.get("fusion", {}).get("verdict")
            or ctx.get("analysis", {}).get("verdict")
        ),
        "suggested_questions": [
            "Why is this image suspicious?",
            "Which region is edited?",
            "Where was the amount changed?",
            "Explain detector disagreement.",
            "Show only edited areas.",
            "Summarize this case.",
            "What evidence supports the verdict?",
            "Generate a court-ready explanation.",
            "Which detector has the highest confidence?",
            "Why did OCR fail?",
            "Compare original vs suspicious region.",
        ],
    }


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    _SESSIONS.pop(session_id, None)
    return {"success": True, "cleared": session_id}
