"""
Tampering Agent — dedicated analysis of the tampering detection module only.
"""

from typing import Any, Dict, List, Optional

from backend.agents.jury.utils import (
    build_finding,
    clamp,
    safe_float,
    verdict_from_score,
)


def run_tampering_agent(
    tampering: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    tampering = tampering or {}
    tampering_analysis = tampering.get("analysis") or tampering

    score = safe_float(
        tampering.get("tampering_score")
        or tampering_analysis.get("tampering_score")
        or 0
    )
    confidence = safe_float(
        tampering.get("confidence")
        or tampering_analysis.get("confidence")
        or 0.5
    )
    verdict_raw = (
        tampering.get("verdict")
        or tampering_analysis.get("verdict")
        or verdict_from_score(score)
    )
    severity = tampering.get("severity") or tampering_analysis.get("severity") or "UNKNOWN"
    signals = tampering.get("signals") or tampering_analysis.get("signals") or []

    findings: List[Dict[str, Any]] = []

    for signal in signals:
        findings.append(build_finding(
            "tampering",
            str(signal),
            "Independent tampering module flagged this forensic indicator.",
            confidence,
        ))

    if not findings:
        if score >= 0.5:
            findings.append(build_finding(
                "tampering",
                f"Tampering score of {score * 100:.0f}% exceeds manipulation threshold.",
                "Weighted forensic fusion of ELA, copy-move, edge, and metadata signals "
                "indicates probable image manipulation.",
                confidence,
            ))
        else:
            findings.append(build_finding(
                "tampering",
                "No strong tampering indicators detected by the dedicated module.",
                "Combined tampering pipeline did not exceed manipulation thresholds.",
                confidence,
            ))

    # Human-readable verdict mapping
    verdict_map = {
        "HIGHLY_SUSPICIOUS": "Manipulated",
        "SUSPICIOUS": "Manipulated",
        "POTENTIALLY_MANIPULATED": "Suspicious",
        "NO_STRONG_TAMPERING_SIGNAL": "Authentic",
    }
    verdict = verdict_map.get(str(verdict_raw).upper(), verdict_from_score(score))

    explanation = (
        f"Tampering module verdict: {verdict_raw} (severity: {severity}). "
        + " ".join(f["what"] for f in findings[:3])
    )

    return {
        "agent_id": "tampering",
        "agent_name": "Tampering Agent",
        "verdict": verdict,
        "confidence": round(clamp(confidence), 4),
        "risk_score": round(clamp(score), 4),
        "findings": findings,
        "explanation": explanation,
        "signals": [str(s) for s in signals],
        "raw_scores": {
            "tampering_score": round(score, 4),
            "severity": severity,
        },
    }
