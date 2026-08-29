"""
Human-readable forensic verdict explanations — reasoning-only via Explainable AI v2.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def generate_forensic_explanation(
    verdict: str,
    signals: Dict[str, Any],
    findings: List[str] | None = None,
    *,
    analysis: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Return investigation summary from Explainable AI / Forensic Reasoning only.
    Never emits generic detector dumps or invented evidence.
    """
    if analysis:
        xai = analysis.get("explainable_ai") or {}
        if xai.get("investigation_summary"):
            return str(xai["investigation_summary"])
        if xai.get("executive_summary"):
            return str(xai["executive_summary"])
        reasoning = analysis.get("forensic_reasoning") or {}
        if reasoning.get("narrative"):
            return str(reasoning["narrative"])
        try:
            from backend.engines.adapters import collect_detector_outputs
            from backend.engines.fusion_engine import fuse_detector_outputs
            from backend.engines.reasoning_engine import run_forensic_reasoning
            from backend.engines.explain_engine import build_explainable_ai

            detectors = collect_detector_outputs(analysis)
            fusion = analysis.get("evidence_fusion") or fuse_detector_outputs(detectors)
            reasoning = run_forensic_reasoning(detectors, fusion, analysis)
            regions = (analysis.get("localization") or {}).get("regions") or []
            xai = build_explainable_ai(reasoning, fusion, regions=regions)
            return xai.get("investigation_summary") or xai.get("executive_summary") or ""
        except Exception:
            pass

    if findings:
        return f"Forensic examination: {verdict}. Documented findings: {'; '.join(findings[:3])}."
    return f"Forensic examination conclusion: {verdict}."
