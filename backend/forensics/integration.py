"""
Integration helpers — wire forensic integrity into upload/analysis pipelines.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from backend.forensics.chain_of_custody import intake_evidence, log_analysis_event
from backend.forensics.immutable_report import seal_analysis_report
from backend.forensics.reproducibility import build_reproducibility_manifest
from backend.forensics.user_context import InvestigatorContext

logger = logging.getLogger("ai_forge.forensics.integration")


def on_evidence_uploaded(
    evidence_id: str,
    file_path: Path,
    *,
    original_filename: str,
    media_type: str,
    investigator: Optional[InvestigatorContext] = None,
    investigation_id: Optional[str] = None,
) -> Dict[str, Any]:
    if investigator is None:
        investigator = InvestigatorContext(user_id="anonymous", display_name="Anonymous")

    try:
        return intake_evidence(
            evidence_id,
            file_path,
            original_filename=original_filename,
            media_type=media_type,
            investigator=investigator,
            investigation_id=investigation_id,
        )
    except Exception as exc:
        logger.warning("Forensic intake failed for %s: %s", evidence_id, exc)
        return {"error": str(exc)}


def on_analysis_complete(
    evidence_id: str,
    analysis_result: Dict[str, Any],
    *,
    media_type: str,
    execution_times: Optional[Dict[str, float]] = None,
    investigator: Optional[InvestigatorContext] = None,
    investigation_id: Optional[str] = None,
    auto_seal: bool = True,
) -> Dict[str, Any]:
    if investigator is None:
        investigator = InvestigatorContext(user_id="system", display_name="System")

    from backend.forensics.repository import get_evidence_record

    record = get_evidence_record(evidence_id)
    if not record:
        logger.debug("Evidence %s not in registry — skipping custody log", evidence_id)
        return {}

    file_hashes = {"sha256": record["sha256"], "sha512": record["sha512"]}

    manifest = build_reproducibility_manifest(
        evidence_id=evidence_id,
        file_hashes=file_hashes,
        media_type=media_type,
        analysis_result=analysis_result,
        execution_times=execution_times,
    )
    analysis_result["reproducibility_manifest"] = manifest
    analysis_result["evidence_hashes"] = file_hashes
    analysis_result["intake_timestamp"] = record.get("intake_timestamp")

    try:
        log_analysis_event(
            evidence_id,
            analysis_type=media_type,
            investigator=investigator,
            investigation_id=investigation_id or record.get("investigation_id"),
            metadata={
                "verdict": analysis_result.get("verdict"),
                "risk_score": analysis_result.get("risk_score"),
                "manifest_hash": manifest.get("manifest_hash"),
            },
        )
    except Exception as exc:
        logger.warning("Custody log failed: %s", exc)

    snapshot = None
    if auto_seal:
        try:
            snapshot = seal_analysis_report(
                evidence_id,
                analysis_result,
                media_type=media_type,
                file_hashes=file_hashes,
                execution_times=execution_times,
                investigator=investigator,
                investigation_id=investigation_id or record.get("investigation_id"),
            )
            analysis_result["immutable_report"] = {
                "snapshot_id": snapshot["snapshot_id"],
                "content_sha256": snapshot["integrity"]["content_sha256"],
                "content_sha512": snapshot["integrity"]["content_sha512"],
                "signature": snapshot["integrity"]["signature"],
                "immutable": True,
            }
        except Exception as exc:
            logger.warning("Report sealing failed: %s", exc)

    return {"manifest": manifest, "snapshot": snapshot}
