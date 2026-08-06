"""Attention maps — forensic fusion + ViT-style spatial attention proxy."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import cv2
import numpy as np

from backend.analysis.attention_heatmap import generate_attention_heatmap

logger = logging.getLogger("ai_forge.attention_maps")


def generate_attention_maps(
    image_path: str,
    output_dir: str,
    tampering_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Unified forensic attention map with per-module explanations."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    try:
        result = generate_attention_heatmap(image_path, str(out), tampering_result)
        explanations = result.get("explanations", [])
        why_parts = [
            f"{e.get('module', 'module').upper()}: {e.get('why', e.get('what', ''))}"
            for e in explanations[:4]
        ]
        return {
            "method": "forensic_attention_fusion",
            "heatmap": result.get("artifacts", {}).get("heatmap"),
            "overlay": result.get("artifacts", {}).get("overlay"),
            "legend": result.get("artifacts", {}).get("legend"),
            "module_scores": result.get("module_scores", {}),
            "module_weights": result.get("module_weights", {}),
            "overall_risk": result.get("overall_risk", 0),
            "risk_zones": result.get("risk_zones", {}),
            "explanations": explanations,
            "why": " ".join(why_parts) if why_parts else "Fused forensic attention shows no dominant hotspots.",
            "confidence": 0.82,
            "score": float(result.get("overall_risk", 0)),
        }
    except Exception as exc:
        logger.warning("Attention map failed: %s", exc)
        gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if gray is None:
            return {"method": "attention_error", "error": str(exc), "why": "Attention map generation failed."}
        edges = cv2.Canny(gray, 50, 150).astype(np.float32) / 255.0
        heatmap_path = out / "attention_fallback.jpg"
        cv2.imwrite(str(heatmap_path), (edges * 255).astype(np.uint8))
        return {
            "method": "attention_fallback",
            "heatmap": str(heatmap_path),
            "score": float(np.mean(edges)),
            "why": f"Forensic fusion failed ({exc}) — edge-density proxy used.",
            "confidence": 0.35,
        }
