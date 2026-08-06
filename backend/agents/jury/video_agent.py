"""Video Agent — frame-level forensic synthesis for video evidence."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.agents.jury.utils import build_finding, clamp, safe_float, verdict_from_score


def run_video_agent(video_analysis: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not video_analysis:
        return {
            "agent_id": "video",
            "agent_name": "Video Agent",
            "verdict": "Inconclusive",
            "confidence": 0.0,
            "risk_score": 0.0,
            "findings": [build_finding(
                "video",
                "No video evidence provided for jury review.",
                "Video agent abstains when no video analysis is available.",
                0.0,
            )],
            "explanation": "No video evidence analyzed.",
            "signals": [],
            "raw_scores": {},
            "vote": "abstain",
            "abstained": True,
        }

    summary = video_analysis.get("summary") or video_analysis
    risk_raw = safe_float(summary.get("risk_score", summary.get("overall_risk", 0)))
    risk = risk_raw / 100.0 if risk_raw > 1 else risk_raw
    confidence = safe_float(summary.get("confidence", 0.75))
    verdict_raw = summary.get("verdict") or summary.get("overall_verdict", "")
    frame_count = int(summary.get("frame_count", summary.get("keyframes_analyzed", 0)) or 0)
    deepfake_frames = int(summary.get("deepfake_frames", 0) or 0)

    findings: List[Dict[str, Any]] = []
    if frame_count > 0:
        findings.append(build_finding(
            "video",
            f"Analyzed {frame_count} keyframe(s) from video evidence.",
            "Temporal forensic pipeline applied frame signals and keyframe forensics.",
            0.8,
        ))

    if deepfake_frames > 0:
        findings.append(build_finding(
            "video",
            f"{deepfake_frames} frame(s) flagged with deepfake/manipulation signals.",
            "Inter-frame inconsistency suggests localized or temporal tampering.",
            min(0.95, 0.5 + deepfake_frames * 0.1),
        ))

    signals_list = video_analysis.get("signals") or summary.get("signals") or []
    for sig in signals_list[:3]:
        findings.append(build_finding(
            "video",
            str(sig),
            "Video forensic module flagged this temporal indicator.",
            confidence,
        ))

    if risk >= 0.45 and not any(f.get("module") == "video" and "flagged" in f.get("what", "") for f in findings):
        findings.append(build_finding(
            "video",
            f"Video risk score {risk:.0%} exceeds manipulation threshold.",
            f"Aggregate verdict: {verdict_raw or 'suspicious'}.",
            confidence,
        ))

    if len(findings) == 1 and findings[0].get("confidence", 0) == 0.8:
        findings.append(build_finding(
            "video",
            "No strong temporal manipulation indicators in video stream.",
            "Frame signals and metadata appear consistent across keyframes.",
            0.85,
        ))
        risk = min(risk, 0.2)

    risk_score = clamp(risk)
    verdict = verdict_from_score(risk_score) if not verdict_raw else str(verdict_raw)

    return {
        "agent_id": "video",
        "agent_name": "Video Agent",
        "verdict": verdict,
        "confidence": round(clamp(confidence), 4),
        "risk_score": round(risk_score, 4),
        "findings": findings,
        "explanation": " ".join(f["what"] for f in findings[:3]),
        "signals": [str(s) for s in signals_list[:5]],
        "raw_scores": {
            "video_risk": round(risk_score, 4),
            "frame_count": frame_count,
            "deepfake_frames": deepfake_frames,
        },
        "vote": "risk" if risk_score >= 0.45 else "authentic",
        "abstained": False,
    }
