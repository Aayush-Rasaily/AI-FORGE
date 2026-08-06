"""
Forensic integrity API — chain of custody, audit, immutable reports, investigations.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from backend.forensics.chain_of_custody import get_full_custody_record
from backend.forensics.immutable_report import (
    list_sealed_reports,
    seal_analysis_report,
    verify_immutable_report,
)
from backend.forensics.repository import (
    create_investigation,
    get_audit_log,
    get_evidence_record,
    get_investigation,
    list_investigations,
    verify_custody_chain,
)
from backend.forensics.user_context import get_investigator

logger = logging.getLogger("ai_forge.custody_api")

router = APIRouter(prefix="/api/forensics", tags=["Forensic Integrity"])


@router.post("/investigations")
async def create_investigation_endpoint(
    request: Request,
    title: str = Query(..., description="Investigation title"),
    description: Optional[str] = Query(None),
):
    inv = get_investigator(request)
    result = create_investigation(
        title,
        description=description,
        lead_investigator_id=inv.user_id,
        lead_investigator_name=inv.display_name,
    )
    return {"success": True, "investigation": result}


@router.get("/investigations")
async def list_investigations_endpoint(limit: int = Query(50, ge=1, le=200)):
    return {"success": True, "investigations": list_investigations(limit)}


@router.get("/investigations/{investigation_id}")
async def get_investigation_endpoint(investigation_id: str):
    result = get_investigation(investigation_id)
    if not result:
        raise HTTPException(status_code=404, detail="Investigation not found")
    history = get_audit_log(investigation_id=investigation_id, limit=200)
    return {
        "success": True,
        "investigation": result,
        "audit_history": history,
    }


@router.get("/evidence/{evidence_id}/hashes")
async def get_evidence_hashes(evidence_id: str):
    record = get_evidence_record(evidence_id)
    if not record:
        raise HTTPException(status_code=404, detail="Evidence not registered")
    return {
        "success": True,
        "evidence_id": evidence_id,
        "sha256": record["sha256"],
        "sha512": record["sha512"],
        "size_bytes": record["size_bytes"],
        "intake_timestamp": record["intake_timestamp"],
        "algorithm": "SHA-256+SHA-512",
    }


@router.get("/evidence/{evidence_id}/custody")
async def get_chain_of_custody(evidence_id: str):
    record = get_full_custody_record(evidence_id)
    if not record.get("evidence"):
        raise HTTPException(status_code=404, detail="Evidence not registered")
    return {"success": True, **record}


@router.get("/evidence/{evidence_id}/custody/verify")
async def verify_chain_of_custody(evidence_id: str):
    result = verify_custody_chain(evidence_id)
    return {"success": True, "evidence_id": evidence_id, **result}


@router.get("/evidence/{evidence_id}/audit")
async def get_evidence_audit_log(
    evidence_id: str,
    limit: int = Query(100, ge=1, le=500),
):
    entries = get_audit_log(evidence_id=evidence_id, limit=limit)
    return {"success": True, "evidence_id": evidence_id, "entries": entries, "count": len(entries)}


@router.get("/audit")
async def get_global_audit_log(
    user_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    entries = get_audit_log(user_id=user_id, limit=limit)
    return {"success": True, "entries": entries, "count": len(entries)}


@router.post("/evidence/{evidence_id}/report/seal")
async def seal_report_endpoint(
    evidence_id: str,
    request: Request,
    report_type: str = Query("forensic_analysis"),
):
    """Seal current analysis as immutable signed report."""
    from backend.database.repository import get_analysis_by_evidence_id

    inv = get_investigator(request)
    cached = get_analysis_by_evidence_id(evidence_id)
    if not cached:
        raise HTTPException(status_code=404, detail="No analysis found to seal")

    record = get_evidence_record(evidence_id)
    if not record:
        raise HTTPException(status_code=404, detail="Evidence not registered")

    file_hashes = {"sha256": record["sha256"], "sha512": record["sha512"]}
    media_type = record.get("media_type", "image")

    snapshot = seal_analysis_report(
        evidence_id,
        cached["analysis"],
        media_type=media_type,
        file_hashes=file_hashes,
        execution_times=cached.get("execution_times"),
        investigator=inv,
        investigation_id=record.get("investigation_id"),
        report_type=report_type,
    )

    return {"success": True, "snapshot": snapshot}


@router.get("/evidence/{evidence_id}/reports")
async def list_reports_endpoint(evidence_id: str):
    return {"success": True, **list_sealed_reports(evidence_id)}


@router.get("/reports/{snapshot_id}/verify")
async def verify_report_endpoint(snapshot_id: str):
    result = verify_immutable_report(snapshot_id)
    return {"success": True, **result}


@router.get("/evidence/{evidence_id}/reproducibility")
async def get_reproducibility_manifest(evidence_id: str):
    from backend.database.repository import get_analysis_by_evidence_id
    from backend.forensics.reproducibility import build_reproducibility_manifest

    record = get_evidence_record(evidence_id)
    if not record:
        raise HTTPException(status_code=404, detail="Evidence not registered")

    cached = get_analysis_by_evidence_id(evidence_id)
    manifest = build_reproducibility_manifest(
        evidence_id=evidence_id,
        file_hashes={"sha256": record["sha256"], "sha512": record["sha512"]},
        media_type=record["media_type"],
        analysis_result=cached["analysis"] if cached else None,
        execution_times=cached.get("execution_times") if cached else None,
    )
    return {"success": True, "manifest": manifest}
