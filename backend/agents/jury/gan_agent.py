"""GAN Agent — AI-generated image detection verdict."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.agents.jury.utils import build_finding, clamp, safe_float, verdict_from_score


def run_gan_agent(analysis: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    analysis = analysis or {}
    gan = analysis.get("gan_detection") or {}
    fusion = gan.get("fusion") or gan
    signals = analysis.get("signals") or {}

    ai_score = safe_float(
        fusion.get("ai_generated_score")
        or gan.get("ai_generated_score")
        or signals.get("gan_ai_score", 0)
    )
    confidence = safe_float(fusion.get("confidence") or gan.get("confidence", 0.7))
    generator = fusion.get("generator_prediction") or gan.get("generator_prediction", "Unknown")
    reasoning = fusion.get("reasoning") or gan.get("reasoning", "")

    findings: List[Dict[str, Any]] = []
    if ai_score >= 0.45:
        findings.append(build_finding(
            "gan",
            f"AI-generated content probability {ai_score:.0%} — predicted generator: {generator}.",
            reasoning or (
                "CNN/ViT/CLIP ensemble detected generative-model fingerprints "
                "inconsistent with natural camera capture."
            ),
            max(ai_score, confidence),
        ))
    elif ai_score >= 0.25:
        findings.append(build_finding(
            "gan",
            f"Moderate AI-generation signals ({ai_score:.0%}).",
            "Frequency and neural embeddings show partial alignment with synthetic generators.",
            ai_score,
        ))
    else:
        findings.append(build_finding(
            "gan",
            "No strong AI generator fingerprints detected.",
            "GAN detection ensemble found patterns consistent with natural photography.",
            1.0 - ai_score,
        ))

    risk_score = clamp(ai_score)
    return {
        "agent_id": "gan",
        "agent_name": "GAN Agent",
        "verdict": verdict_from_score(risk_score),
        "confidence": round(clamp(confidence if ai_score >= 0.2 else 1 - ai_score), 4),
        "risk_score": round(risk_score, 4),
        "findings": findings,
        "explanation": findings[0]["what"] if findings else "",
        "signals": [generator, reasoning] if reasoning else [generator],
        "raw_scores": {
            "ai_generated_score": round(ai_score, 4),
            "generator_prediction": generator,
        },
        "vote": "risk" if risk_score >= 0.45 else "authentic",
    }
