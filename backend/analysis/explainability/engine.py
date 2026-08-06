"""
Explainability engine — GradCAM, Attention, SHAP, LIME, overlays, forensic report.
Every prediction includes a WHY explanation.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from backend.analysis.explainability.attention_maps import generate_attention_maps
from backend.analysis.explainability.gradcam import generate_gradcam
from backend.analysis.explainability.lime_explainer import generate_lime_explanation
from backend.analysis.explainability.overlay import build_suspicious_overlay
from backend.analysis.explainability.report_generator import generate_explainability_report
from backend.analysis.explainability.shap_explainer import generate_shap_attribution

logger = logging.getLogger("ai_forge.explainability")


def run_explainability(
    image_path: str,
    output_dir: str,
    context: Optional[Dict[str, Any]] = None,
    tampering_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Run full explainability pipeline.

    Parameters
    ----------
    image_path : str
        Path to evidence image.
    output_dir : str
        Directory for heatmaps and overlays.
    context : dict, optional
        Analysis context: verdict, risk_score, confidence, signals, evidence.
    tampering_result : dict, optional
        Tampering detector output for attention fusion.
    """
    context = context or {}
    out = Path(output_dir) / "explainability"
    out.mkdir(parents=True, exist_ok=True)

    target_score = float(context.get("risk_score", 50)) / 100.0

    gradcam = generate_gradcam(image_path, str(out), target_score=target_score)
    attention = generate_attention_maps(image_path, str(out), tampering_result)
    shap = generate_shap_attribution(image_path, str(out))
    lime = generate_lime_explanation(image_path, str(out))

    overlay = build_suspicious_overlay(
        image_path, str(out), gradcam, attention, shap, lime,
    )

    report = generate_explainability_report(
        context, gradcam, attention, shap, lime, overlay,
    )

    return {
        "success": True,
        "gradcam": gradcam,
        "attention": attention,
        "shap": shap,
        "lime": lime,
        "overlay": overlay,
        "human_readable_report": report.get("human_readable_report"),
        "ai_explanation": report.get("ai_explanation"),
        "evidence_chain": report.get("evidence_chain"),
        "confidence_graph": report.get("confidence_graph"),
        "predictions": report.get("predictions"),
        "suspicious_regions": report.get("suspicious_regions"),
        "artifacts": {
            "gradcam_overlay": gradcam.get("overlay"),
            "gradcam_heatmap": gradcam.get("heatmap"),
            "attention_overlay": attention.get("overlay"),
            "attention_heatmap": attention.get("heatmap"),
            "shap_overlay": shap.get("overlay"),
            "lime_overlay": lime.get("overlay"),
            "fused_overlay": overlay.get("fused_overlay"),
            "fused_heatmap": overlay.get("fused_heatmap"),
            "boxed_regions": overlay.get("boxed_regions"),
        },
        "forensic_report": report,
    }
