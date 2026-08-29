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

def _build_forensic_dossier(
    agents: Dict[str, Dict[str, Any]],
    final_verdict: str,
    fused_risk: float,
    localization_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    import hashlib
    import datetime
    import json
    from backend.contracts.forensic_finding import investigative_severity
    from backend.utils.bbox_schema import region_bbox
    
    findings: List[Dict[str, Any]] = []
    
    # 1. Collect structured forensic findings if agents emit them natively
    for agent_id, agent in agents.items():
        if agent.get("forensic_findings"):
            for ff in agent["forensic_findings"]:
                if "source_agent" not in ff:
                    ff["source_agent"] = agent.get("agent_name", agent_id)
                findings.append(ff)
        # 2. Convert raw 'findings' from agents into ForensicFinding
        elif agent.get("findings"):
            for idx, f in enumerate(agent["findings"]):
                conf = f.get("confidence", 0.0)
                identity = json.dumps(
                    {"agent": agent_id, "index": idx, "finding": f},
                    sort_keys=True,
                    default=str,
                )
                item = {
                    "finding_id": f.get("finding_id") or (
                        "JURY-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16].upper()
                    ),
                    "page": f.get("page", 1),
                    "location": f.get("location", "Unknown"),
                    "field_name": f.get("what", "Document Feature"),
                    "object_type": f.get("object_type", "region"),
                    "detected_value": f.get("detected_value", "Unknown"),
                    "claimed_original": f.get("claimed_original", "Unknown"),
                    "edit_type": f.get("edit_type", "Anomaly"),
                    "severity": investigative_severity(
                        f.get("edit_type") or f.get("object_type") or f.get("what"),
                        f.get("severity"),
                        legal_or_authorization_impact=bool(
                            f.get("is_legal_document") or f.get("authorization_impact")
                        ),
                    ).title(),
                    "evidence": [f.get("why", "Suspicious region detected")],
                    "plain_english_explanation": f.get("why", "Suspicious region detected"),
                    "confidence_pct": round(conf * 100, 1),
                    "confidence": conf,
                    "detector_votes": {agent_id: True},
                    "detectors": [agent_id],
                    "source_agent": agent.get("agent_name", agent_id),
                }
                bbox = f.get("bbox") or f.get("bounding_box")
                if bbox:
                    try:
                        normalized = region_bbox({"bbox": bbox})
                        if normalized["width"] > 0 and normalized["height"] > 0:
                            item["bbox"] = normalized
                    except (TypeError, ValueError, KeyError):
                        pass
                findings.append(item)
                
    # Sort findings by confidence desc
    findings.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    
    # Number them
    for i, f in enumerate(findings):
        f["finding_number"] = i + 1
        
    critical = sum(1 for f in findings if str(f.get("severity", "")).lower() == "critical")
    suspicious = sum(
        1 for f in findings
        if str(f.get("severity", "")).lower() in {"high", "medium"}
    )
    
    localization_array = []
    if localization_data and localization_data.get("regions"):
        for reg in localization_data["regions"]:
            try:
                bbox = region_bbox(reg)
            except (TypeError, ValueError, KeyError):
                continue
            if bbox["width"] <= 0 or bbox["height"] <= 0:
                continue
            loc_dict = {key: int(bbox[key]) for key in ("x", "y", "width", "height")}
            # Special case: logo / signature / metadata 
            desc = reg.get("plain_english_explanation") or reg.get("reason") or "Manipulated region detected"
            t = reg.get("edit_type") or reg.get("type", "Anomaly")
            if "metadata" in t.lower() or t == "metadata_conflict":
                # Do not use metadata as localization
                continue
            
            localization_array.append({
                "region_id": reg.get("region_id") or reg.get("id"),
                "page": int(reg.get("page", 1)),
                "type": t,
                "confidence": round(float(reg.get("confidence", 0)), 4),
                "location": loc_dict,
                "description": desc
            })
    
    explanations = []
    
    # Generate Human-Centered XAI Explanations
    for loc in localization_array:
        if loc["type"] == "None" or "No localized manipulation" in loc["description"]:
            continue
            
        t = loc["type"]
        conf = loc["confidence"]
        bbox = loc["location"]
        
        severity = investigative_severity(t).title()
        
        # Reason and Impact Mapping
        summary = "The highlighted region contains signs of digital editing."
        reason = "The region shows forensic anomalies inconsistent with the rest of the document."
        impact = "Potential document tampering."
        
        if t == "Pasted Signature":
            summary = "The signature does not match the reference."
            reason = "The signature appears to have been copied and pasted from another source."
            impact = "Identity fraud or unauthorized contract approval."
        elif t == "Copied Logo":
            summary = "The logo appears digitally added."
            reason = "The corporate logo shows signs of being inserted after the document was created."
            impact = "Brand forgery or fake institutional document."
        elif t == "Edited Currency Values":
            summary = "This value seems altered."
            reason = "The number differs from surrounding typography and shows editing artefacts."
            impact = "Financial fraud or inflated insurance claims."
        elif t == "Changed Numbers":
            summary = "This value seems altered."
            reason = "The number differs from surrounding typography and shows editing artefacts."
            impact = "Financial or statistical misrepresentation."
        elif t == "Modified Dates":
            summary = "The date appears to have been changed."
            reason = "The date format or typography is inconsistent with the rest of the text."
            impact = "Contract manipulation or expired document extension."
        elif t == "Inserted Text":
            summary = "The text appears inserted."
            reason = "The text style differs from nearby text and contains digital insertion artifacts."
            impact = "Content manipulation and misrepresentation."
        elif t == "Replaced Text":
            summary = "The text style differs from nearby text."
            reason = "The text was likely typed over erased original content."
            impact = "Content manipulation."
        elif t == "Copied Content":
            summary = "Part of this image appears duplicated."
            reason = "A section of the document has been copied and pasted over another area."
            impact = "Information concealment or document tampering."
        elif t == "Digitally Inserted Object":
            summary = "The highlighted region contains signs of digital editing."
            reason = "This area appears saved separately from the rest of the document."
            impact = "Object insertion or content alteration."
        elif t == "Pasted Stamp":
            summary = "The stamp appears digitally added."
            reason = "The stamp shows insertion artifacts instead of physical ink properties."
            impact = "Fake certification or official approval bypass."
        elif t == "Pasted Seal":
            summary = "The seal appears digitally added."
            reason = "The seal shows insertion artifacts instead of physical ink properties."
            impact = "Fake certification or official approval bypass."

        # Location heuristic
        lx, ly = bbox.get("x", 0), bbox.get("y", 0)
        loc_str = "Center"
        if ly < 300:
            loc_str = "Top Right" if lx > 400 else "Top Left"
        elif ly > 800:
            loc_str = "Bottom Right" if lx > 400 else "Bottom Left"
        else:
            loc_str = "Middle Right" if lx > 400 else "Middle Left"
            
        explanations.append({
            "title": t,
            "region_id": loc.get("region_id"),
            "page": loc["page"],
            "severity": severity,
            "location": loc_str,
            "summary": summary,
            "reason": reason,
            "impact": impact
        })

    return {
        "finding_count": len(findings),
        "critical_count": critical,
        "suspicious_count": suspicious,
        "verify_count": len(findings) - critical - suspicious,
        "findings": findings,
        "localization": localization_array,
        "explanations": explanations,
        "overall_risk_pct": round(fused_risk * 100, 1),
        "overall_verdict": final_verdict,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }



def run_fusion_agent(
    agents: Dict[str, Dict[str, Any]],
    weights: Optional[Dict[str, float]] = None,
    localization_data: Optional[Dict[str, Any]] = None,
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

    forensic_dossier = _build_forensic_dossier(agents, final_verdict, fused_risk, localization_data)

    return {
        "final_verdict": final_verdict,
        "verdict": final_verdict,
        "confidence": round(final_confidence, 4),
        "confidence_pct": round(final_confidence * 100, 1),
        "risk_score": round(fused_risk, 4),
        "risk_score_pct": round(fused_risk * 100, 1),
        "risk_level": risk_level,
        "reasoning": reasoning,
        "weighted_scores": weighted_scores,
        "detector_contributions": [
            {
                "detector_name": aid,
                "contribution": weighted_scores.get(aid, 0),
                "confidence": float(agents.get(aid, {}).get("confidence", 0)),
                "risk_score": float(agents.get(aid, {}).get("risk_score", 0)),
                "verdict": agents.get(aid, {}).get("verdict"),
                "technical_reason": (agents.get(aid, {}).get("explanation") or "")[:300],
            }
            for aid in agents
        ],
        "majority_vote": majority,
        "minority_opinion": minority,
        "confidence_distribution": confidence_distribution,
        "evidence_ranking": evidence_ranking,
        "disagreements": disagreements,
        "report": report,
        "forensic_dossier": forensic_dossier,
    }
