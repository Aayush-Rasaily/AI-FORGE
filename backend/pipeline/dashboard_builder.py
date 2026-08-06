"""
Build dashboard.json — UI-ready forensic summary for frontend.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from backend.utils.artifact_paths import artifact_api_urls


def build_dashboard(
    evidence_id: str,
    analysis: Dict[str, Any],
    tampering: Dict[str, Any],
    *,
    jury: Optional[Dict[str, Any]] = None,
    timing: Optional[Dict[str, float]] = None,
    artifacts: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    signals = analysis.get("signals") or {}
    fusion = analysis.get("risk_fusion") or analysis.get("ensemble") or {}
    ai_gen = analysis.get("ai_generation") or analysis.get("gan_detection") or {}
    jury_fusion = (jury or {}).get("fusion") or jury or {}

    artifact_urls = artifacts or artifact_api_urls(evidence_id)
    total_time = sum(v for v in (timing or {}).values() if isinstance(v, (int, float)))

    module_scores = {
        "ela": round(float(signals.get("ela_score", 0)) * 100, 2),
        "wavelet": round(float(signals.get("wavelet_score", 0)) * 100, 2),
        "copy_move": round(float(signals.get("copy_move_score", 0)) * 100, 2),
        "edge": round(float(signals.get("edge_density", 0)) * 100, 2),
        "metadata": round(float(signals.get("metadata_risk_score", 0)) * 100, 2),
        "ai_generation": round(
            float(ai_gen.get("ai_generated_probability", signals.get("gan_ai_score", 0))) * 100, 2
        ),
        "deepfake": round(float(signals.get("deepfake_probability", 0)) * 100, 2),
    }

    timeline = _build_timeline(timing or analysis.get("timing", {}))

    return {
        "evidence_id": evidence_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "risk_score": analysis.get("risk_score", fusion.get("overall_fraud_risk", 0)),
        "confidence": analysis.get("confidence", fusion.get("confidence", 0)),
        "verdict": analysis.get("verdict", fusion.get("verdict", "UNKNOWN")),
        "recommendation": analysis.get("recommendation", ""),
        "explanation": analysis.get("explanation", ""),
        "module_scores": module_scores,
        "signals": {
            "ela_score": signals.get("ela_score", 0),
            "wavelet_score": signals.get("wavelet_score", 0),
            "copy_move_score": signals.get("copy_move_score", 0),
            "copy_move_detected": signals.get("copy_move_detected", False),
            "edge_density": signals.get("edge_density", 0),
            "metadata_risk_score": signals.get("metadata_risk_score", 0),
            "gan_ai_score": signals.get("gan_ai_score", 0),
        },
        "risk_fusion": {
            "authenticity_score": fusion.get("authenticity_score"),
            "manipulation_score": fusion.get("manipulation_score"),
            "ai_generation_score": fusion.get("ai_generation_score"),
            "overall_fraud_risk": fusion.get("overall_fraud_risk", analysis.get("risk_score")),
            "explainability": fusion.get("explainability", []),
        },
        "jury": {
            "verdict": jury_fusion.get("verdict") or jury_fusion.get("final_verdict"),
            "confidence": jury_fusion.get("confidence"),
            "risk_level": jury_fusion.get("risk_level"),
            "majority_opinion": jury_fusion.get("majority_opinion"),
            "score": jury_fusion.get("jury_score") or jury_fusion.get("score"),
        },
        "tampering": {
            "verdict": tampering.get("verdict"),
            "severity": tampering.get("severity"),
            "score": tampering.get("tampering_score"),
        },
        "artifacts": artifact_urls,
        "heatmap": artifact_urls.get("ela"),
        "timeline": timeline,
        "processing_time_ms": round(total_time * 1000 if total_time < 1000 else total_time, 2),
        "scan_mode": analysis.get("scan_mode", "deep"),
        "findings": analysis.get("findings", []),
    }


def _build_timeline(timing: Dict[str, Any]) -> list:
    events = []
    for module, duration in sorted(timing.items(), key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0):
        if module.startswith("_") or not isinstance(duration, (int, float)):
            continue
        events.append({
            "module": module,
            "duration_ms": round(duration * 1000 if duration < 100 else duration, 2),
            "status": "completed",
        })
    return events


def save_dashboard(analysis_dir: Path, dashboard: Dict[str, Any]) -> Path:
    import json
    path = Path(analysis_dir) / "dashboard.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dashboard, f, indent=2, default=str)
    if path.exists():
        path.unlink(missing_ok=True)
    tmp.replace(path)
    return path
