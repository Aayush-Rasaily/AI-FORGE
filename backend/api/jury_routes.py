"""
Jury API Routes — multi-agent forensic reasoning endpoints.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.agents.jury import run_jury_analysis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jury", tags=["jury"])

AGENT_IDS = [
    "vision", "metadata", "ocr", "video", "gan", "deepfake", "signature",
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
    Run 7-agent jury analysis on pre-computed forensic outputs.

    Agents: Vision, Metadata, OCR, Video, GAN, Deepfake, Signature.
    Returns per-agent votes, majority verdict, minority opinion, and fused report.
    """
    has_input = any([
        request.analysis,
        request.tampering,
        request.document_analysis,
        request.video_analysis,
        request.signature_result,
    ])
    if not has_input:
        raise HTTPException(
            status_code=400,
            detail="At least one forensic analysis payload must be provided.",
        )

    try:
        result = run_jury_analysis(
            analysis=request.analysis,
            tampering=request.tampering,
            document_analysis=request.document_analysis,
            video_analysis=request.video_analysis,
            signature_result=request.signature_result,
            evidence_id=request.evidence_id,
            filename=request.filename,
        )
        if request.evidence_id:
            try:
                from backend.pipeline.report_manager import persist_analysis_payload, generate_reports

                persist_analysis_payload(request.evidence_id, result, kind="jury")
                generate_reports(request.evidence_id, jury_data=result, background=True)
                logger.info("jury_report_queued | evidence_id=%s", request.evidence_id)
            except Exception as report_exc:
                logger.warning("jury_report_queue_failed | error=%s", report_exc)
            result["reports_pending"] = True
            result["report_status"] = "queued"
            result["evidence_id"] = request.evidence_id
        return result
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
