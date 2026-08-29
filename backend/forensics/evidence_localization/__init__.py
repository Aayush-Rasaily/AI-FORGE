"""
Evidence Localization Engine — Phase 1.

Public API:
    run_evidence_localization(evidence_id, image_path, analysis_dir,
                              analysis_result, jury_result)

Produces:
    <analysis_dir>/evidence_localization.json

This module is purely additive — it never mutates the existing
analysis_result or jury_result dictionaries, and its failure is
always caught at the call-site so the main pipeline is unaffected.
"""

from backend.forensics.evidence_localization.engine import run_evidence_localization

__all__ = ["run_evidence_localization"]
