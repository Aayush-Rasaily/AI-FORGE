"""
Jury API Routes — multi-agent forensic reasoning endpoints.
"""

import logging
import asyncio
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.evidence.paths import get_analysis_dir
from backend.services.dossier_jury_service import run_dossier_jury

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jury", tags=["jury"])

AGENT_IDS = [
    "expert_01",
    "expert_02",
    "expert_03",
    "expert_04",
    "expert_05",
    "expert_06",
]


class JuryAnalyzeRequest(BaseModel):
    evidence_id: Optional[str] = None
    filename: Optional[str] = None
    analysis: Optional[Dict[str, Any]] = Field(default_factory=dict)
    tampering: Optional[Dict[str, Any]] = Field(default_factory=dict)
    document_analysis: Optional[Dict[str, Any]] = None
    video_analysis: Optional[Dict[str, Any]] = None
    signature_result: Optional[Dict[str, Any]] = None


@router.post("/analyze")
async def jury_analyze(request: JuryAnalyzeRequest):
    """
    Evaluate the existing forensic dossier without rerunning detectors.
    """
    if not request.evidence_id:
        raise HTTPException(
            status_code=400,
            detail="evidence_id is required; jury analysis uses forensic_dossier.json.",
        )

    analysis_dir = get_analysis_dir(request.evidence_id, create=False)
    try:
        result = await asyncio.to_thread(
            run_dossier_jury,
            request.evidence_id,
            analysis_dir,
        )
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Jury analysis failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Jury analysis failed: {exc}") from exc


@router.get("/health")
async def jury_health():
    return {
        "status": "ok",
        "service": "jury",
        "agents": AGENT_IDS,
        "agent_count": len(AGENT_IDS),
    }
