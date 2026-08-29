"""Canonical finding and audited reference-link endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.evidence.paths import find_evidence_file, get_analysis_dir
from backend.forensics.user_context import get_investigator
from backend.services.forensic_findings_service import get_or_build_forensic_findings
from backend.services.reference_link_service import (
    create_reference_link, delete_reference_link, get_reference_link,
)

router = APIRouter(prefix="/api", tags=["Forensic Findings"])


class ReferenceLinkRequest(BaseModel):
    reference_id: str = Field(..., min_length=1, max_length=128)
    relationship: str = Field(..., min_length=1, max_length=250)
    authenticity_status: str = Field(default="unknown")


def _require_evidence(evidence_id: str) -> None:
    if find_evidence_file(evidence_id) is None:
        from backend.forensics.repository import get_evidence_record
        if get_evidence_record(evidence_id) is None:
            raise HTTPException(status_code=404, detail="Evidence not found")


@router.get("/evidence/{evidence_id}/findings")
async def get_findings(evidence_id: str):
    _require_evidence(evidence_id)
    payload = get_or_build_forensic_findings(evidence_id, get_analysis_dir(evidence_id))
    return {
        "success": True,
        "evidence_id": evidence_id,
        "findings": payload.get("findings") or [],
        "summary": payload.get("summary") or {},
    }


@router.get("/evidence/{examined_id}/reference")
async def get_reference(examined_id: str):
    try:
        reference = get_reference_link(examined_id)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "evidence_id": examined_id, "reference": reference}


@router.post("/evidence/{examined_id}/reference")
async def post_reference(examined_id: str, body: ReferenceLinkRequest, request: Request):
    try:
        reference = create_reference_link(
            examined_id, body.reference_id,
            relationship=body.relationship,
            authenticity_status=body.authenticity_status,
            investigator=get_investigator(request),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"success": True, "evidence_id": examined_id, "reference": reference}


@router.delete("/evidence/{examined_id}/reference")
async def delete_reference(examined_id: str, request: Request):
    try:
        reference = delete_reference_link(
            examined_id, investigator=get_investigator(request),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"success": True, "evidence_id": examined_id, "reference": reference}
