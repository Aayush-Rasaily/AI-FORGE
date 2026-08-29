"""
Evidence Localization Engine — Orchestrator (Phase 1).

Wires together the four pipeline stages:
    Stage 1 — region_proposer.propose_regions()
    Stage 2 — candidate_filter.filter_candidates()
    Stage 3 — confidence_scorer.score_regions()
    Stage 4 — evidence_serializer.serialize_evidence()

Public API:
    run_evidence_localization(
        evidence_id, image_path, analysis_dir,
        analysis_result, jury_result
    ) -> Dict[str, Any]

Contract
--------
• Never mutates analysis_result or jury_result.
• Always writes evidence_localization.json to analysis_dir.
• Returns the serialized output dict on success.
• On any internal failure: logs the error and returns a minimal
  error dict (so the caller's except block can log without re-raising).
• Fully deterministic — identical inputs produce identical output.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("ai_forge.evidence_localization.engine")


def run_evidence_localization(
    evidence_id: str,
    image_path: Path,
    analysis_dir: Path,
    analysis_result: Dict[str, Any],
    jury_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Run the Phase 1 Evidence Localization pipeline end-to-end.

    Parameters
    ----------
    evidence_id     : UUID string identifying this analysis case.
    image_path      : Absolute path to the evidence image file.
    analysis_dir    : Directory where all analysis artifacts live.
                      evidence_localization.json will be written here.
    analysis_result : Complete output dict from analyze_image_unified().
                      Treated as read-only — never mutated.
    jury_result     : Complete output dict from run_jury_analysis().
                      Treated as read-only — never mutated.

    Returns
    -------
    Dict matching the evidence_localization.json schema:
        {
          "schema_version": "1.0",
          "evidence_id": ...,
          "region_count": ...,
          "summary": { ... },
          "regions": [ ... ]
        }

    On failure, returns:
        {"success": False, "error": "<message>", "region_count": 0}
    """
    t_start = time.perf_counter()
    image_path = Path(image_path)
    analysis_dir = Path(analysis_dir)

    logger.info(
        "evidence_localization | evidence_id=%s | image=%s",
        evidence_id,
        image_path.name,
    )

    try:
        # ── Stage 1: Propose raw regions ─────────────────────────────────
        from backend.forensics.evidence_localization.region_proposer import propose_regions

        raw_regions = propose_regions(
            image_path=image_path,
            analysis_dir=analysis_dir,
            analysis_result=analysis_result,
            jury_result=jury_result,
        )
        logger.debug(
            "evidence_localization | stage=propose | raw_count=%d",
            len(raw_regions),
        )

        # ── Stage 2: Filter candidates ───────────────────────────────────
        from backend.forensics.evidence_localization.candidate_filter import filter_candidates

        filtered = filter_candidates(raw_regions)
        logger.debug(
            "evidence_localization | stage=filter | filtered_count=%d",
            len(filtered),
        )

        # ── Stage 3: Score and classify ──────────────────────────────────
        from backend.forensics.evidence_localization.confidence_scorer import score_regions

        scored = score_regions(
            filtered_regions=filtered,
            analysis_result=analysis_result,
            jury_result=jury_result,
        )
        logger.debug(
            "evidence_localization | stage=score | scored_count=%d",
            len(scored),
        )

        # ── Stage 4: Serialize to disk ───────────────────────────────────
        from backend.forensics.evidence_localization.evidence_serializer import serialize_evidence

        output = serialize_evidence(
            evidence_id=evidence_id,
            analysis_dir=analysis_dir,
            scored_regions=scored,
        )
        try:
            from backend.services.professional_localization_service import (
                build_professional_localization,
            )

            dossier = {}
            dossier_path = analysis_dir / "forensic_dossier.json"
            if dossier_path.is_file():
                import json

                with dossier_path.open(encoding="utf-8") as dossier_file:
                    loaded = json.load(dossier_file)
                dossier = loaded if isinstance(loaded, dict) else {"findings": loaded}
            jury_dossier = ((jury_result or {}).get("fusion") or {}).get(
                "forensic_dossier"
            )
            if jury_dossier and isinstance(jury_dossier, dict):
                dossier = {**dossier, **jury_dossier}
            professional = build_professional_localization(
                evidence_id,
                analysis_dir,
                image_paths={1: image_path},
                dossier=dossier,
                analysis=analysis_result,
            )
            output["professional_localization"] = professional
            output["regions"] = professional.get("regions", output.get("regions", []))
            output["region_count"] = len(output["regions"])
            output["summary"] = professional.get("summary", output.get("summary", {}))
            from backend.services.explainable_narrative_service import (
                build_explainable_narrative,
            )

            output["explainable_ai"] = build_explainable_narrative(
                evidence_id,
                analysis_dir,
                dossier=dossier,
                analysis=analysis_result,
            )
        except Exception as exc:
            logger.warning(
                "professional_localization_failed | evidence_id=%s | error=%s",
                evidence_id,
                exc,
            )

        elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
        logger.info(
            "evidence_localization | done | regions=%d | elapsed_ms=%.1f",
            output.get("region_count", 0),
            elapsed_ms,
        )

        return output

    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
        logger.error(
            "evidence_localization | FAILED | evidence_id=%s | error=%s | elapsed_ms=%.1f",
            evidence_id,
            exc,
            elapsed_ms,
        )
        # Return a minimal error dict — caller already wraps in try/except
        # so this keeps things informative without re-raising.
        return {
            "success": False,
            "error": str(exc),
            "evidence_id": str(evidence_id),
            "region_count": 0,
            "regions": [],
        }
