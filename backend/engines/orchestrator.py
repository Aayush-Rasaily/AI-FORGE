"""
Post-analysis orchestrator — Fusion → Reasoning → Localization → Explainable AI.

Additive: enriches existing analysis dict without removing fields.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from backend.engines.adapters import collect_detector_outputs
from backend.engines.explain_engine import (
    build_explainable_ai,
    save_explainable_ai,
)
from backend.engines.fusion_engine import fuse_detector_outputs
from backend.engines.reasoning_engine import run_forensic_reasoning, save_forensic_reasoning

logger = logging.getLogger("ai_forge.engines.orchestrator")


def _apply_explainable(analysis: Dict[str, Any], explainable: Dict[str, Any], fusion: Dict[str, Any]) -> None:
    analysis["explainable_ai"] = explainable
    analysis["explanation"] = explainable.get("investigation_summary") or explainable.get("executive_summary") or ""
    analysis["detailed_investigation"] = explainable.get("investigation_summary") or ""
    analysis["executive_summary_text"] = explainable.get("executive_summary") or ""
    analysis["technical_explanation"] = explainable.get("technical_explanation") or ""
    analysis["court_explanation"] = explainable.get("court_explanation") or ""
    analysis["recommendation"] = (
        ((analysis.get("forensic_reasoning") or {}).get("findings") or [{}])[0].get("recommendation")
        or explainable.get("primary_finding")
    )
    analysis["findings"] = [
        explainable.get("primary_finding"),
        *[
            f.get("finding")
            for f in (analysis.get("forensic_reasoning") or {}).get("findings") or []
            if f.get("finding") and f.get("finding") != explainable.get("primary_finding")
        ],
    ]
    analysis["findings"] = [f for f in analysis["findings"] if f][:8]
    rf = analysis.get("risk_fusion") or {}
    analysis["risk_fusion"] = {
        **rf,
        "explainability": explainable.get("key_evidence") or rf.get("explainability", []),
        "engine": "explainable_ai_v2",
    }


def enrich_analysis_with_engines(
    analysis: Dict[str, Any],
    *,
    evidence_id: Optional[str] = None,
    image_path: Optional[Path] = None,
    analysis_dir: Optional[Path] = None,
    run_localization: bool = True,
) -> Dict[str, Any]:
    """
    Attach fusion, forensic reasoning, localization, and explainable AI narratives.
    Preserves backward-compatible keys (verdict, risk_score, explanation, risk_fusion).
    """
    if not isinstance(analysis, dict):
        return analysis

    detectors = collect_detector_outputs(analysis)
    profile = str(
        analysis.get("profile")
        or (analysis.get("signals") or {}).get("profile")
        or "natural_photo"
    )
    fusion = fuse_detector_outputs(detectors, profile=profile)

    legacy = analysis.get("risk_fusion") or {}
    legacy_score = float(legacy.get("overall_fraud_risk") or analysis.get("risk_score") or 0)
    if legacy_score <= 1:
        legacy_score *= 100.0

    engine_score = float(fusion.get("overall_score") or 0)
    if legacy and engine_score > 0:
        blended = round(engine_score * 0.60 + legacy_score * 0.40, 2)
    else:
        blended = engine_score or legacy_score

    fusion["overall_score"] = blended
    if blended >= 70:
        fusion["verdict"] = "HIGH RISK — LIKELY MANIPULATED"
    elif blended >= 45:
        fusion["verdict"] = "MEDIUM RISK — SUSPICIOUS"
    elif blended >= 20:
        fusion["verdict"] = "LOW RISK — MINOR ANOMALIES"
    else:
        fusion["verdict"] = "NO SIGNIFICANT ANOMALY DETECTED"
    if len(fusion.get("elevated_detectors") or []) >= 2 and blended < 42:
        fusion["verdict"] = "MEDIUM RISK — SUSPICIOUS"
        fusion["overall_score"] = max(blended, 42.0)

    forensic_reasoning = run_forensic_reasoning(detectors, fusion, analysis)

    analysis["detector_outputs"] = detectors
    analysis["evidence_fusion"] = fusion
    analysis["forensic_reasoning"] = forensic_reasoning
    analysis["verdict"] = fusion.get("verdict") or analysis.get("verdict")
    analysis["risk_score"] = float(fusion.get("overall_score") or analysis.get("risk_score") or 0)
    analysis["confidence"] = float(fusion.get("confidence") or analysis.get("confidence") or 0)
    analysis["forensic_score"] = round(analysis["risk_score"] / 100.0, 4)
    analysis["risk_fusion"] = {
        **legacy,
        "overall_fraud_risk": analysis["risk_score"],
        "confidence": analysis["confidence"],
        "verdict": analysis["verdict"],
        "detector_contributions": fusion.get("detector_contributions"),
        "elevated_modules": fusion.get("elevated_detectors"),
        "strong_modules": fusion.get("strong_detectors"),
    }

    regions: list = []
    loc: Dict[str, Any] = {}
    if run_localization and evidence_id:
        try:
            from backend.analysis.forgery_localization import ensure_localization, _save_json
            from backend.evidence.paths import get_analysis_dir

            loc = ensure_localization(evidence_id, analysis=analysis)
            regions = loc.get("regions") or []
        except Exception as exc:
            logger.warning("localization_enrich_failed | %s | %s", evidence_id, exc)

    explainable = build_explainable_ai(forensic_reasoning, fusion, regions=regions)
    _apply_explainable(analysis, explainable, fusion)

    if evidence_id:
        try:
            from backend.evidence.paths import get_analysis_dir

            adir = Path(analysis_dir) if analysis_dir else get_analysis_dir(evidence_id, create=True)
            save_forensic_reasoning(evidence_id, forensic_reasoning, analysis_dir=adir)
            save_explainable_ai(adir, explainable)
        except Exception as exc:
            logger.warning("reasoning_persist_failed | %s | %s", evidence_id, exc)

    if run_localization and evidence_id and loc:
        try:
            from backend.analysis.forgery_localization import _save_json
            from backend.evidence.paths import get_analysis_dir

            enriched_regions = explainable.get("regions") or regions
            loc["regions"] = enriched_regions
            loc["explanation"] = analysis["explanation"]
            loc["detailed_investigation"] = analysis["detailed_investigation"]
            loc["explainable_ai"] = {
                "executive_summary": explainable.get("executive_summary"),
                "investigation_summary": explainable.get("investigation_summary"),
                "technical_explanation": explainable.get("technical_explanation"),
                "court_explanation": explainable.get("court_explanation"),
            }
            adir = Path(analysis_dir) if analysis_dir else get_analysis_dir(evidence_id, create=True)
            _save_json(adir / "localization.json", loc)
            analysis["localization"] = {
                "views": loc.get("views"),
                "regions": enriched_regions,
                "explanation": analysis["explanation"],
                "detailed_investigation": analysis["detailed_investigation"],
                "explainable_ai": loc.get("explainable_ai"),
                "coverage": loc.get("coverage"),
                "layers_used": loc.get("layers_used"),
                "investigation_panel": loc.get("investigation_panel"),
            }
        except Exception as exc:
            logger.warning("localization_save_failed | %s | %s", evidence_id, exc)

    return analysis
