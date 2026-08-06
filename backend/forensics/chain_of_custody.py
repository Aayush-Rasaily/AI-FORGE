"""
Chain of custody service — intake, transfer, analysis, export events.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from backend.forensics.evidence_hash import compute_evidence_hashes
from backend.forensics.repository import (
    append_audit_log,
    append_custody_event,
    get_custody_chain,
    get_evidence_record,
    register_evidence,
    verify_custody_chain,
)
from backend.forensics.user_context import InvestigatorContext


def intake_evidence(
    evidence_id: str,
    file_path: Path,
    *,
    original_filename: str,
    media_type: str,
    investigator: InvestigatorContext,
    investigation_id: Optional[str] = None,
    location: str = "AI-FORGE Evidence Vault",
) -> Dict[str, Any]:
    hashes = compute_evidence_hashes(file_path)

    record = register_evidence(
        evidence_id,
        original_filename=original_filename,
        stored_path=str(file_path.resolve()),
        media_type=media_type,
        sha256=hashes["sha256"],
        sha512=hashes["sha512"],
        size_bytes=hashes["size_bytes"],
        investigation_id=investigation_id,
        intake_user_id=investigator.user_id,
        intake_user_name=investigator.display_name,
    )

    custody = append_custody_event(
        evidence_id,
        "RECEIVED",
        f"Evidence received: {original_filename}",
        sha256=hashes["sha256"],
        sha512=hashes["sha512"],
        actor_id=investigator.user_id,
        actor_name=investigator.display_name,
        investigation_id=investigation_id,
        location=location,
        metadata={"size_bytes": hashes["size_bytes"], "media_type": media_type},
    )

    append_audit_log(
        "EVIDENCE_INTAKE",
        user_id=investigator.user_id,
        user_name=investigator.display_name,
        resource_type="evidence",
        resource_id=evidence_id,
        evidence_id=evidence_id,
        investigation_id=investigation_id,
        client_ip=investigator.client_ip,
        details={"hashes": hashes, "filename": original_filename},
    )

    return {"evidence": record, "hashes": hashes, "custody_event": custody}


def log_analysis_event(
    evidence_id: str,
    *,
    analysis_type: str,
    investigator: InvestigatorContext,
    investigation_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    record = get_evidence_record(evidence_id)
    if not record:
        raise ValueError(f"Evidence not registered: {evidence_id}")

    custody = append_custody_event(
        evidence_id,
        "ANALYZED",
        f"Forensic analysis completed: {analysis_type}",
        sha256=record["sha256"],
        sha512=record["sha512"],
        actor_id=investigator.user_id,
        actor_name=investigator.display_name,
        investigation_id=investigation_id or record.get("investigation_id"),
        metadata=metadata,
    )

    append_audit_log(
        "ANALYSIS_COMPLETE",
        user_id=investigator.user_id,
        user_name=investigator.display_name,
        resource_type="analysis",
        resource_id=evidence_id,
        evidence_id=evidence_id,
        investigation_id=investigation_id,
        client_ip=investigator.client_ip,
        details=metadata,
    )

    return custody


def log_report_sealed(
    evidence_id: str,
    snapshot_id: str,
    *,
    investigator: InvestigatorContext,
    investigation_id: Optional[str] = None,
) -> Dict[str, Any]:
    record = get_evidence_record(evidence_id)
    if not record:
        raise ValueError(f"Evidence not registered: {evidence_id}")

    custody = append_custody_event(
        evidence_id,
        "REPORT_SEALED",
        f"Immutable report sealed: {snapshot_id}",
        sha256=record["sha256"],
        sha512=record["sha512"],
        actor_id=investigator.user_id,
        actor_name=investigator.display_name,
        investigation_id=investigation_id,
        metadata={"snapshot_id": snapshot_id},
    )

    append_audit_log(
        "REPORT_SEALED",
        user_id=investigator.user_id,
        user_name=investigator.display_name,
        resource_type="report",
        resource_id=snapshot_id,
        evidence_id=evidence_id,
        client_ip=investigator.client_ip,
        details={"snapshot_id": snapshot_id},
    )

    return custody


def get_full_custody_record(evidence_id: str) -> Dict[str, Any]:
    record = get_evidence_record(evidence_id)
    chain = get_custody_chain(evidence_id)
    verification = verify_custody_chain(evidence_id)
    return {
        "evidence": record,
        "chain": chain,
        "verification": verification,
        "chain_length": len(chain),
    }
