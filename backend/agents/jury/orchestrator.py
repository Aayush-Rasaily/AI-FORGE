"""
Jury Orchestrator — 7 independent agents with weighted fusion.
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

AGENT_IMPORTANCE = {
    "vision": 0.18,
    "metadata": 0.12,
    "ocr": 0.12,
    "video": 0.12,
    "gan": 0.15,
    "deepfake": 0.16,
    "signature": 0.15,
}


def run_jury_analysis(
    analysis: Optional[Dict[str, Any]] = None,
    tampering: Optional[Dict[str, Any]] = None,
    document_analysis: Optional[Dict[str, Any]] = None,
    video_analysis: Optional[Dict[str, Any]] = None,
    signature_result: Optional[Dict[str, Any]] = None,
    evidence_id: Optional[str] = None,
    filename: Optional[str] = None,
) -> Dict[str, Any]:
    """Run all 7 jury agents in parallel on pre-computed forensic outputs."""
    logger.info("Starting 7-agent jury analysis for evidence_id=%s", evidence_id)

    tasks = {
        "vision": lambda: run_vision_agent(analysis=analysis, tampering=tampering),
        "metadata": lambda: run_metadata_agent(analysis=analysis, tampering=tampering),
        "ocr": lambda: run_ocr_layout_agent(
            analysis=analysis, document_analysis=document_analysis
        ),
        "video": lambda: run_video_agent(video_analysis=video_analysis),
        "gan": lambda: run_gan_agent(analysis=analysis),
        "deepfake": lambda: run_deepfake_agent(analysis=analysis),
        "signature": lambda: run_signature_agent(signature_result=signature_result),
    }

    agents: Dict[str, Dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=7) as executor:
        futures = {executor.submit(fn): name for name, fn in tasks.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                agents[name] = future.result()
            except Exception as exc:
                logger.warning("Jury agent %s failed: %s", name, exc)
                agents[name] = {
                    "agent_id": name,
                    "agent_name": name.replace("_", " ").title() + " Agent",
                    "verdict": "Inconclusive",
                    "confidence": 0.0,
                    "risk_score": 0.0,
                    "findings": [],
                    "vote": "abstain",
                    "abstained": True,
                    "error": str(exc),
                }

    for agent_id, agent in agents.items():
        if agent.get("abstained"):
            continue
        conf = float(agent.get("confidence", 0.5))
        agent["reliability"] = round(min(1.0, conf + 0.08), 3)
        agent["importance"] = AGENT_IMPORTANCE.get(agent_id, 0.12)
        agent["weight"] = AGENT_WEIGHTS.get(agent_id, 0.12)

    fusion = run_fusion_agent(agents)

    return {
        "success": True,
        "evidence_id": evidence_id,
        "filename": filename,
        "agent_count": len(agents),
        "agents": agents,
        "fusion": fusion,
        "majority_vote": fusion.get("majority_vote"),
        "minority_opinion": fusion.get("minority_opinion"),
        "risk_level": fusion.get("risk_level"),
        "confidence_distribution": fusion.get("confidence_distribution"),
        "reasoning": fusion.get("reasoning"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
