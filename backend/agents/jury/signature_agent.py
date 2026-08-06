"""Signature Agent — signature verification verdict."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.agents.jury.utils import build_finding, clamp, safe_float, verdict_from_score


def run_signature_agent(signature_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not signature_result:
        return {
            "agent_id": "signature",
            "agent_name": "Signature Agent",
            "verdict": "Inconclusive",
            "confidence": 0.0,
            "risk_score": 0.0,
            "findings": [build_finding(
                "signature",
                "No signature verification performed.",
                "Signature agent abstains when no reference/query pair was submitted.",
                0.0,
            )],
            "explanation": "No signature evidence provided.",
            "signals": [],
            "raw_scores": {},
            "vote": "abstain",
            "abstained": True,
        }

    similarity = safe_float(signature_result.get("similarity", 0))
    confidence = safe_float(signature_result.get("confidence", 0.8))
    verdict_raw = str(signature_result.get("verdict", ""))
    is_match = signature_result.get("is_match")
    if is_match is None:
        is_match = similarity >= 0.7 or "match" in verdict_raw.lower()

    risk_score = clamp(1.0 - similarity)
    findings: List[Dict[str, Any]] = []

    if is_match and similarity >= 0.75:
        findings.append(build_finding(
            "signature",
            f"Signatures match with {similarity:.0%} similarity.",
            "Neural embedding distance and structural comparison support authenticity.",
            confidence,
        ))
        risk_score = clamp(1.0 - similarity) * 0.5
    elif similarity >= 0.5:
        findings.append(build_finding(
            "signature",
            f"Partial signature similarity ({similarity:.0%}) — possible forgery.",
            "Similarity below threshold suggests stylistic or stroke inconsistencies.",
            confidence,
        ))
    else:
        findings.append(build_finding(
            "signature",
            f"Signature mismatch detected ({similarity:.0%} similarity).",
            verdict_raw or "Query signature diverges significantly from reference.",
            confidence,
        ))

    verdict = verdict_from_score(risk_score)
    if "match" in verdict_raw.lower() and "mis" not in verdict_raw.lower():
        verdict = "Authentic" if similarity >= 0.75 else verdict
    elif "mismatch" in verdict_raw.lower() or "forg" in verdict_raw.lower():
        verdict = "Manipulated"

    return {
        "agent_id": "signature",
        "agent_name": "Signature Agent",
        "verdict": verdict,
        "confidence": round(clamp(confidence), 4),
        "risk_score": round(risk_score, 4),
        "findings": findings,
        "explanation": findings[0]["what"] if findings else "",
        "signals": [verdict_raw] if verdict_raw else [],
        "raw_scores": {
            "similarity": round(similarity, 4),
            "is_match": bool(is_match),
        },
        "vote": "risk" if risk_score >= 0.45 else "authentic",
        "abstained": False,
    }
