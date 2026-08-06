"""Deepfake Agent — face forensics and deepfake probability."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.agents.jury.utils import build_finding, clamp, safe_float, verdict_from_score


def run_deepfake_agent(analysis: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    analysis = analysis or {}
    face = analysis.get("face_forensics") or {}
    fusion = face.get("fusion") or face
    signals = analysis.get("signals") or {}

    deepfake_prob = safe_float(
        fusion.get("deepfake_probability")
        or face.get("deepfake_probability")
        or signals.get("deepfake_probability", 0)
    )
    authenticity = safe_float(
        fusion.get("face_authenticity_score")
        or face.get("face_authenticity_score")
        or signals.get("face_authenticity_score", 1.0)
    )
    confidence = safe_float(fusion.get("confidence") or face.get("confidence", 0.75))
    reasoning = fusion.get("reasoning") or face.get("reasoning", "")
    face_count = int(face.get("faces_detected", fusion.get("faces_detected", 0)) or 0)

    findings: List[Dict[str, Any]] = []

    if face_count == 0:
        findings.append(build_finding(
            "deepfake",
            "No faces detected — deepfake analysis not applicable.",
            "Face forensics requires detectable facial regions in the evidence.",
            0.5,
        ))
        risk_score = 0.15
        confidence = 0.4
    elif deepfake_prob >= 0.45:
        findings.append(build_finding(
            "deepfake",
            f"Deepfake probability {deepfake_prob:.0%} across {face_count} face(s).",
            reasoning or (
                "Xception/MesoNet and consistency checks (blink, lighting, skin texture) "
                "indicate synthetic or swapped facial content."
            ),
            max(deepfake_prob, confidence),
        ))
        risk_score = deepfake_prob
    elif deepfake_prob >= 0.25:
        findings.append(build_finding(
            "deepfake",
            f"Elevated deepfake signals ({deepfake_prob:.0%}) on {face_count} face(s).",
            "Partial facial inconsistency detected — manual review recommended.",
            deepfake_prob,
        ))
        risk_score = deepfake_prob
    else:
        findings.append(build_finding(
            "deepfake",
            f"Face authenticity score {authenticity:.0%} — faces appear genuine.",
            "Facial consistency checks did not flag strong deepfake indicators.",
            authenticity,
        ))
        risk_score = 1.0 - authenticity

    risk_score = clamp(risk_score)
    return {
        "agent_id": "deepfake",
        "agent_name": "Deepfake Agent",
        "verdict": verdict_from_score(risk_score),
        "confidence": round(clamp(confidence), 4),
        "risk_score": round(risk_score, 4),
        "findings": findings,
        "explanation": findings[0]["what"] if findings else "",
        "signals": face.get("signals", []) or [reasoning] if reasoning else [],
        "raw_scores": {
            "deepfake_probability": round(deepfake_prob, 4),
            "face_authenticity_score": round(authenticity, 4),
            "faces_detected": face_count,
        },
        "vote": "risk" if risk_score >= 0.45 else "authentic",
    }
