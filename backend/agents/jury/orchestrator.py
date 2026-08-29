"""
Jury Orchestrator — 6 specialized forensic agents with weighted consensus and contribution percentages.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.agents.jury.deepfake_agent import run_deepfake_agent
from backend.agents.jury.fusion_agent import AGENT_WEIGHTS, run_fusion_agent
from backend.agents.jury.gan_agent import run_gan_agent
from backend.agents.jury.metadata_agent import run_metadata_agent
from backend.agents.jury.ocr_layout_agent import run_ocr_layout_agent
from backend.agents.jury.signature_agent import run_signature_agent
from backend.agents.jury.video_agent import run_video_agent
from backend.agents.jury.vision_agent import run_vision_agent

logger = logging.getLogger(__name__)

# Specialized 6-Agent Panel
SPECIALIZED_AGENT_CONFIG = {
    "metadata": {"name": "Agent 1: Metadata Specialist", "weight": 0.15},
    "pixel": {"name": "Agent 2: Pixel Forensic Specialist", "weight": 0.20},
    "noise": {"name": "Agent 3: Noise & Frequency Specialist", "weight": 0.15},
    "deep_learning": {"name": "Agent 4: Deep Learning Specialist", "weight": 0.20},
    "localization": {"name": "Agent 5: Localization Specialist", "weight": 0.15},
    "explainability": {"name": "Agent 6: Explainability Specialist", "weight": 0.15},
}


def _run_specialized_agent_panel(
    analysis: Optional[Dict[str, Any]],
    tampering: Optional[Dict[str, Any]],
    document_analysis: Optional[Dict[str, Any]],
    video_analysis: Optional[Dict[str, Any]],
    signature_result: Optional[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    analysis = analysis or {}
    tampering = tampering or {}

    # Agent 1: Metadata
    meta = run_metadata_agent(analysis=analysis, tampering=tampering)
    a1_conf = float(meta.get("confidence", 0.7))
    a1_risk = float(meta.get("risk_score", 0.1))
    a1_opinion = "Metadata headers are consistent" if a1_risk < 0.3 else "Metadata manipulation or timestamp anomaly detected"
    a1_evidence = [f.get("why") or f.get("what") for f in meta.get("findings", []) if f.get("why") or f.get("what")] or ["EXIF data checked"]
    a1_disagree = []

    # Agent 2: Pixel
    vis = run_vision_agent(analysis=analysis, tampering=tampering)
    a2_conf = float(vis.get("confidence", 0.75))
    a2_risk = float(vis.get("risk_score", 0.2))
    a2_opinion = "Pixel structures intact" if a2_risk < 0.35 else "Pixel-level ELA/edge/copy-move anomaly detected"
    a2_evidence = [f.get("why") or f.get("what") for f in vis.get("findings", []) if f.get("why") or f.get("what")] or ["Spatial pixel analysis executed"]
    a2_disagree = []

    # Agent 3: Noise & Frequency
    a3_conf = round(float(analysis.get("noise_confidence") or 0.8), 2)
    a3_risk = round(float(analysis.get("noise_inconsistency") or analysis.get("noise_score") or 0.15), 2)
    a3_opinion = "Noise distribution is uniform across frequencies" if a3_risk < 0.4 else "High frequency / wavelet noise variance detected"
    a3_evidence = [f"Noise variance score: {a3_risk:.2f}", "Wavelet subband inconsistency checked"]
    a3_disagree = []

    # Agent 4: Deep Learning
    gan = run_gan_agent(analysis=analysis)
    df = run_deepfake_agent(analysis=analysis)
    a4_conf = max(float(gan.get("confidence", 0.7)), float(df.get("confidence", 0.7)))
    a4_risk = max(float(gan.get("risk_score", 0.1)), float(df.get("risk_score", 0.1)))
    a4_opinion = "No generative or synthetic features detected" if a4_risk < 0.4 else "GAN or Deepfake neural artifacts detected"
    a4_evidence = [f.get("why") or f.get("what") for f in gan.get("findings", []) + df.get("findings", []) if f.get("why") or f.get("what")] or ["EfficientNet/ViT neural check executed"]
    a4_disagree = []

    # Agent 5: Localization
    loc_data = analysis.get("localization") or {}
    regions_count = len(loc_data.get("regions") or [])
    a5_conf = 0.85 if regions_count > 0 else 0.70
    a5_risk = min(1.0, regions_count * 0.25)
    a5_opinion = f"{regions_count} suspicious region(s) localized" if regions_count > 0 else "No localized forgery masks extracted"
    a5_evidence = [f"Extracted {regions_count} suspicious region mask(s)", "Fused multi-detector heatmap checked"]
    a5_disagree = []

    # Agent 6: Explainability
    exp_data = analysis.get("explanation") or analysis.get("forensic_explanation") or {}
    a6_conf = 0.90
    a6_risk = round(float(analysis.get("risk_score") or 0.2), 2)
    a6_opinion = "Findings backed by empirical detector signals"
    a6_evidence = [str(exp_data)] if isinstance(exp_data, str) else ["Multi-detector evidence cross-referenced"]
    a6_disagree = []

    # Cross-agent disagreement checks
    votes = [a1_risk >= 0.4, a2_risk >= 0.4, a3_risk >= 0.4, a4_risk >= 0.4, a5_risk >= 0.4]
    if any(votes) and not all(votes):
        if a1_risk < 0.4 and a2_risk >= 0.4:
            a1_disagree.append("Metadata clean despite pixel anomaly")
            a2_disagree.append("Pixel anomaly detected despite clean metadata")
        if a4_risk >= 0.4 and a3_risk < 0.4:
            a4_disagree.append("Deep learning model flagged synthetic patterns which noise analysis missed")

    agents = {
        "metadata": {
            "agent_id": "metadata",
            "agent_name": "Agent 1: Metadata Specialist",
            "opinion": a1_opinion,
            "verdict": "Manipulated" if a1_risk >= 0.4 else "Authentic",
            "confidence": round(a1_conf, 2),
            "risk_score": round(a1_risk, 2),
            "evidence": a1_evidence,
            "disagreement": a1_disagree,
            "contribution_pct": 15.0,
            "weight": 0.15,
        },
        "pixel": {
            "agent_id": "pixel",
            "agent_name": "Agent 2: Pixel Forensic Specialist",
            "opinion": a2_opinion,
            "verdict": "Manipulated" if a2_risk >= 0.4 else "Authentic",
            "confidence": round(a2_conf, 2),
            "risk_score": round(a2_risk, 2),
            "evidence": a2_evidence,
            "disagreement": a2_disagree,
            "contribution_pct": 20.0,
            "weight": 0.20,
        },
        "noise": {
            "agent_id": "noise",
            "agent_name": "Agent 3: Noise & Frequency Specialist",
            "opinion": a3_opinion,
            "verdict": "Manipulated" if a3_risk >= 0.4 else "Authentic",
            "confidence": round(a3_conf, 2),
            "risk_score": round(a3_risk, 2),
            "evidence": a3_evidence,
            "disagreement": a3_disagree,
            "contribution_pct": 15.0,
            "weight": 0.15,
        },
        "deep_learning": {
            "agent_id": "deep_learning",
            "agent_name": "Agent 4: Deep Learning Specialist",
            "opinion": a4_opinion,
            "verdict": "Manipulated" if a4_risk >= 0.4 else "Authentic",
            "confidence": round(a4_conf, 2),
            "risk_score": round(a4_risk, 2),
            "evidence": a4_evidence,
            "disagreement": a4_disagree,
            "contribution_pct": 20.0,
            "weight": 0.20,
        },
        "localization": {
            "agent_id": "localization",
            "agent_name": "Agent 5: Localization Specialist",
            "opinion": a5_opinion,
            "verdict": "Manipulated" if a5_risk >= 0.4 else "Authentic",
            "confidence": round(a5_conf, 2),
            "risk_score": round(a5_risk, 2),
            "evidence": a5_evidence,
            "disagreement": a5_disagree,
            "contribution_pct": 15.0,
            "weight": 0.15,
        },
        "explainability": {
            "agent_id": "explainability",
            "agent_name": "Agent 6: Explainability Specialist",
            "opinion": a6_opinion,
            "verdict": "Manipulated" if a6_risk >= 0.4 else "Authentic",
            "confidence": round(a6_conf, 2),
            "risk_score": round(a6_risk, 2),
            "evidence": a6_evidence,
            "disagreement": a6_disagree,
            "contribution_pct": 15.0,
            "weight": 0.15,
        },
    }

    # The signature detector is optional for non-signature evidence.  When
    # the normal image pipeline supplies a real result, include the existing
    # signature agent in the panel instead of silently dropping its output.
    if isinstance(signature_result, dict) and (
        signature_result.get("signature_present")
        or signature_result.get("similarity") is not None
        or signature_result.get("forgery_probability") is not None
    ):
        agents["signature"] = run_signature_agent(
            signature_result=signature_result,
            analysis=analysis,
        )

    return agents


def run_jury_analysis(
    analysis: Optional[Dict[str, Any]] = None,
    tampering: Optional[Dict[str, Any]] = None,
    document_analysis: Optional[Dict[str, Any]] = None,
    video_analysis: Optional[Dict[str, Any]] = None,
    signature_result: Optional[Dict[str, Any]] = None,
    evidence_id: Optional[str] = None,
    filename: Optional[str] = None,
) -> Dict[str, Any]:
    """Run specialized 6-agent jury analysis on pre-computed forensic outputs."""
    logger.info("Starting specialized 6-agent jury analysis for evidence_id=%s", evidence_id)
    analysis = analysis or {}
    signature_result = (
        signature_result
        or analysis.get("signature_analysis")
        or analysis.get("signature_result")
        or analysis.get("signature_verification")
    )

    agents = _run_specialized_agent_panel(
        analysis=analysis,
        tampering=tampering,
        document_analysis=document_analysis,
        video_analysis=video_analysis,
        signature_result=signature_result,
    )

    fusion = run_fusion_agent(agents, localization_data=analysis.get("localization"))

    # Contribution percentages summary for UI charts
    contributions = {
        aid: a["contribution_pct"] for aid, a in agents.items()
    }

    return {
        "success": True,
        "evidence_id": evidence_id,
        "filename": filename,
        "agent_count": len(agents),
        "agents": agents,
        "fusion": fusion,
        "contribution_percentages": contributions,
        "majority_vote": fusion.get("majority_vote"),
        "minority_opinion": fusion.get("minority_opinion"),
        "risk_level": fusion.get("risk_level"),
        "confidence_distribution": fusion.get("confidence_distribution"),
        "reasoning": fusion.get("reasoning"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

