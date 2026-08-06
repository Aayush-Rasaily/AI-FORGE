"""
Risk Fusion Agent — weighted confidence fusion, majority vote, minority opinion.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.agents.jury.utils import clamp, normalize_verdict, verdict_from_score


AGENT_WEIGHTS: Dict[str, float] = {
    "vision": 0.18,
    "metadata": 0.12,
    "ocr": 0.12,
    "video": 0.12,
    "gan": 0.15,
    "deepfake": 0.16,
    "signature": 0.15,
}


def risk_level_from_score(score: float) -> str:
    if score >= 0.70:
        return "CRITICAL"
    if score >= 0.45:
        return "HIGH"
    if score >= 0.25:
        return "MEDIUM"
    return "LOW"


def _agent_vote(agent: Dict[str, Any]) -> str:
    if agent.get("abstained"):
        return "abstain"
    vote = agent.get("vote")
    if vote in ("risk", "authentic", "abstain"):
        return vote
    return normalize_verdict(agent.get("verdict", ""))


def _compute_majority_vote(agents: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    votes: List[Dict[str, Any]] = []
    for agent_id, agent in agents.items():
        vote = _agent_vote(agent)
        if vote == "abstain":
            continue
        votes.append({
            "agent_id": agent_id,
            "agent_name": agent.get("agent_name", agent_id),
            "vote": vote,
            "verdict": agent.get("verdict"),
            "confidence": agent.get("confidence", 0),
            "risk_score": agent.get("risk_score", 0),
        })

    risk_votes = [v for v in votes if v["vote"] == "risk"]
    auth_votes = [v for v in votes if v["vote"] == "authentic"]
    abstained = len(agents) - len(votes)

    if len(risk_votes) > len(auth_votes):
        majority = "risk"
        majority_label = "Manipulated / Suspicious"
    elif len(auth_votes) > len(risk_votes):
        majority = "authentic"
        majority_label = "Authentic"
    else:
        majority = "split"
        majority_label = "Split Decision"

    return {
        "majority": majority,
        "majority_label": majority_label,
        "risk_votes": len(risk_votes),
        "authentic_votes": len(auth_votes),
        "abstained": abstained,
        "total_voting": len(votes),
        "votes": votes,
        "margin": abs(len(risk_votes) - len(auth_votes)),
    }


def _compute_minority_opinion(
    agents: Dict[str, Dict[str, Any]],
    majority: Dict[str, Any],
) -> List[Dict[str, Any]]:
    majority_side = majority.get("majority")
    if majority_side in ("split", None):
        return [{
            "agent_id": v["agent_id"],
            "agent_name": v["agent_name"],
            "verdict": v["verdict"],
            "vote": v["vote"],
            "confidence": v["confidence"],
            "opinion": (
                f"{v['agent_name']} voted {v['verdict']} — "
                f"no clear majority (split {majority.get('risk_votes', 0)}-{majority.get('authentic_votes', 0)})."
            ),
            "why": agents.get(v["agent_id"], {}).get("explanation", ""),
        } for v in majority.get("votes", [])]

    minority: List[Dict[str, Any]] = []
    for v in majority.get("votes", []):
        if v["vote"] != majority_side:
            agent = agents.get(v["agent_id"], {})
            minority.append({
                "agent_id": v["agent_id"],
                "agent_name": v["agent_name"],
                "verdict": v["verdict"],
                "vote": v["vote"],
                "confidence": v["confidence"],
                "risk_score": v["risk_score"],
                "opinion": (
                    f"{v['agent_name']} dissents — voted {v['verdict']} "
                    f"({v['confidence']:.0%} confidence) against majority "
                    f"'{majority.get('majority_label')}'."
                ),
                "why": agent.get("explanation", ""),
                "findings": (agent.get("findings") or [])[:2],
            })
    return minority


def _build_confidence_distribution(
    agents: Dict[str, Dict[str, Any]],
    weighted_scores: Dict[str, float],
) -> Dict[str, Any]:
    distribution: Dict[str, Any] = {}
    for agent_id, agent in agents.items():
        distribution[agent_id] = {
            "agent_name": agent.get("agent_name", agent_id),
            "confidence": round(float(agent.get("confidence", 0)), 4),
            "confidence_pct": round(float(agent.get("confidence", 0)) * 100, 1),
            "weight": round(weighted_scores.get(agent_id, 0), 4),
            "risk_score": round(float(agent.get("risk_score", 0)), 4),
            "risk_pct": round(float(agent.get("risk_score", 0)) * 100, 1),
            "verdict": agent.get("verdict"),
            "vote": _agent_vote(agent),
            "abstained": bool(agent.get("abstained")),
        }
    return distribution


def _detect_disagreements(agents: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    disagreements: List[Dict[str, Any]] = []
    verdicts = {aid: normalize_verdict(a.get("verdict", "")) for aid, a in agents.items() if not a.get("abstained")}

    risk_agents = [aid for aid, v in verdicts.items() if v == "risk"]
    auth_agents = [aid for aid, v in verdicts.items() if v == "authentic"]

    if risk_agents and auth_agents:
        disagreements.append({
            "agents": risk_agents + auth_agents,
            "issue": "Verdict conflict",
            "details": (
                f"Agents {', '.join(risk_agents)} flagged manipulation risk while "
                f"{', '.join(auth_agents)} assessed the evidence as authentic."
            ),
        })

    confidences = {aid: a.get("confidence", 0) for aid, a in agents.items() if not a.get("abstained")}
    if confidences:
        spread = max(confidences.values()) - min(confidences.values())
        if spread >= 0.35:
            high = max(confidences, key=confidences.get)
            low = min(confidences, key=confidences.get)
            disagreements.append({
                "agents": [high, low],
                "issue": "Confidence divergence",
                "details": (
                    f"{high} confidence ({confidences[high]:.0%}) differs significantly "
                    f"from {low} ({confidences[low]:.0%})."
                ),
            })

    return disagreements


def _build_evidence_ranking(
    agents: Dict[str, Dict[str, Any]],
    weights: Dict[str, float],
) -> List[Dict[str, Any]]:
    ranked: List[Dict[str, Any]] = []

    for agent_id, agent in agents.items():
        if agent.get("abstained"):
            continue
        weight = weights.get(agent_id, 0.1)
        for finding in agent.get("findings") or []:
            conf = finding.get("confidence", 0)
            ranked.append({
                "source": agent.get("agent_name", agent_id),
                "module": finding.get("module", "unknown"),
                "finding": finding.get("what", ""),
                "why": finding.get("why", ""),
                "confidence": conf,
                "weight": weight,
                "score": conf * weight,
            })

    ranked.sort(key=lambda x: x["score"], reverse=True)
    for i, item in enumerate(ranked[:12], start=1):
        item["rank"] = i

    return ranked[:12]


def _build_report(
    final_verdict: str,
    confidence: float,
    risk_score: float,
    risk_level: str,
    majority: Dict[str, Any],
    minority: List[Dict[str, Any]],
    agents: Dict[str, Dict[str, Any]],
    disagreements: List[Dict[str, Any]],
    evidence_ranking: List[Dict[str, Any]],
    reasoning: str,
) -> Dict[str, Any]:
    agent_summaries = [
        {
            "agent": a.get("agent_name"),
            "verdict": a.get("verdict"),
            "confidence": a.get("confidence"),
            "vote": _agent_vote(a),
            "key_finding": (a.get("findings") or [{}])[0].get("what", ""),
        }
        for a in agents.values()
    ]

    recommendations: List[str] = []
    if risk_level == "CRITICAL":
        recommendations.append("Escalate immediately for certified forensic examiner review.")
        recommendations.append("Preserve original file hash and full chain-of-custody documentation.")
    elif risk_level == "HIGH":
        recommendations.append("Request source document or alternate capture for comparison.")
        recommendations.append("Cross-reference metadata with known device profiles.")
    else:
        recommendations.append("No immediate escalation required based on automated jury analysis.")
        recommendations.append("Archive jury deliberation record for audit trail.")

    if minority:
        recommendations.append(
            f"Review minority opinion from {minority[0]['agent_name']} before final adjudication."
        )
    if disagreements:
        recommendations.append("Resolve agent disagreement through targeted manual inspection.")

    return {
        "title": "AI Jury Investigation Report",
        "summary": (
            f"Seven-agent forensic jury assessed this evidence as **{final_verdict}** "
            f"({risk_level} risk, {confidence:.0%} weighted confidence). "
            f"Majority vote: {majority.get('majority_label')} "
            f"({majority.get('risk_votes', 0)} risk / {majority.get('authentic_votes', 0)} authentic)."
        ),
        "reasoning": reasoning,
        "agent_summaries": agent_summaries,
        "top_evidence": [e["finding"] for e in evidence_ranking[:3]],
        "disagreement_count": len(disagreements),
        "minority_count": len(minority),
        "recommendations": recommendations,
        "methodology": (
            "Seven independent agents (Vision, Metadata, OCR, Video, GAN, Deepfake, Signature) "
            "vote separately. Risk Fusion applies weighted confidence fusion, majority vote, "
            "and minority opinion synthesis."
        ),
    }


def run_fusion_agent(
    agents: Dict[str, Dict[str, Any]],
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    weights = weights or AGENT_WEIGHTS

    weighted_scores: Dict[str, float] = {}
    total_weight = 0.0
    fused_risk = 0.0

    for agent_id, agent in agents.items():
        if agent.get("abstained"):
            weighted_scores[agent_id] = 0.0
            continue
        w = weights.get(agent_id, 0.1)
        risk = float(agent.get("risk_score", 0))
        conf = float(agent.get("confidence", 0))
        rel = float(agent.get("reliability", conf))
        imp = float(agent.get("importance", w))
        effective_weight = w * conf * rel * imp
        weighted_scores[agent_id] = round(effective_weight, 4)
        fused_risk += risk * effective_weight
        total_weight += effective_weight

    if total_weight > 0:
        fused_risk /= total_weight

    fused_risk = clamp(fused_risk)
    final_confidence = clamp(total_weight)
    final_verdict = verdict_from_score(fused_risk)
    risk_level = risk_level_from_score(fused_risk)

    majority = _compute_majority_vote(agents)
    minority = _compute_minority_opinion(agents, majority)
    confidence_distribution = _build_confidence_distribution(agents, weighted_scores)
    disagreements = _detect_disagreements(agents)
    evidence_ranking = _build_evidence_ranking(agents, weights)

    reasoning_parts = [
        f"Majority: {majority['majority_label']} ({majority['risk_votes']}R/{majority['authentic_votes']}A).",
        f"Weighted risk {fused_risk:.0%} → {final_verdict} ({risk_level}).",
    ]
    if minority:
        reasoning_parts.append(
            f"Minority dissent: {minority[0]['agent_name']} — {minority[0]['why'][:120]}."
        )
    top = evidence_ranking[0] if evidence_ranking else None
    if top:
        reasoning_parts.append(f"Strongest evidence: {top['finding'][:100]}.")

    reasoning = " ".join(reasoning_parts)

    report = _build_report(
        final_verdict, final_confidence, fused_risk, risk_level,
        majority, minority, agents, disagreements, evidence_ranking, reasoning,
    )

    return {
        "final_verdict": final_verdict,
        "confidence": round(final_confidence, 4),
        "confidence_pct": round(final_confidence * 100, 1),
        "risk_score": round(fused_risk, 4),
        "risk_score_pct": round(fused_risk * 100, 1),
        "risk_level": risk_level,
        "reasoning": reasoning,
        "weighted_scores": weighted_scores,
        "majority_vote": majority,
        "minority_opinion": minority,
        "confidence_distribution": confidence_distribution,
        "evidence_ranking": evidence_ranking,
        "disagreements": disagreements,
        "report": report,
    }
