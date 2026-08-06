"""
Immutable report sealing — signed snapshots with reproducibility manifest.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from backend.forensics.chain_of_custody import log_report_sealed
from backend.forensics.repository import (
    get_report_snapshots,
    seal_immutable_report,
    verify_report_snapshot,
)
from backend.forensics.reproducibility import build_reproducibility_manifest
from backend.forensics.user_context import InvestigatorContext


def seal_analysis_report(
    evidence_id: str,
    analysis_result: Dict[str, Any],
    *,
    media_type: str,
    file_hashes: Dict[str, str],
    execution_times: Optional[Dict[str, float]] = None,
    investigator: InvestigatorContext,
    investigation_id: Optional[str] = None,
    report_type: str = "forensic_analysis",
) -> Dict[str, Any]:
    manifest = build_reproducibility_manifest(
        evidence_id=evidence_id,
        file_hashes=file_hashes,
        media_type=media_type,
        analysis_result=analysis_result,
        execution_times=execution_times,
    )

    snapshot = seal_immutable_report(
        evidence_id,
        report_type,
        analysis_result,
        manifest=manifest,
        investigation_id=investigation_id,
        sealed_by_id=investigator.user_id,
        sealed_by_name=investigator.display_name,
    )

    log_report_sealed(
        evidence_id,
        snapshot["snapshot_id"],
        investigator=investigator,
        investigation_id=investigation_id,
    )

    return {
        **snapshot,
        "reproducibility_manifest": manifest,
    }


def verify_immutable_report(snapshot_id: str) -> Dict[str, Any]:
    return verify_report_snapshot(snapshot_id)


def list_sealed_reports(evidence_id: str) -> Dict[str, Any]:
    snapshots = get_report_snapshots(evidence_id)
    return {
        "evidence_id": evidence_id,
        "snapshots": snapshots,
        "count": len(snapshots),
    }
