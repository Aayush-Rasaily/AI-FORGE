"""
Structured analysis persistence — split JSON files per evidence item.

Files stored in analysis/<evidence_id>/:
  analysis.json   — full analysis result
  tampering.json  — tampering module output
  jury.json       — jury verdict (if available)
  metadata.json   — metadata forensics
  risk.json       — fused risk scores + explainability
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("ai_forge.persistence")

FILES = {
    "analysis": "analysis.json",
    "tampering": "tampering.json",
    "jury": "jury.json",
    "metadata": "metadata.json",
    "risk": "risk.json",
    "dashboard": "dashboard.json",
}


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    if path.exists():
        path.unlink(missing_ok=True)
    tmp.replace(path)


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read %s: %s", path, exc)
        return None


def save_analysis_bundle(
    analysis_dir: Path,
    *,
    analysis: Dict[str, Any],
    tampering: Dict[str, Any],
    timing: Optional[Dict[str, float]] = None,
    jury: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    risk: Optional[Dict[str, Any]] = None,
) -> None:
    """Persist all analysis artifacts to disk."""
    analysis_dir = Path(analysis_dir)
    analysis_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "evidence_id": analysis.get("evidence_id"),
        "cached": True,
        "analysis": analysis,
        "tampering": tampering,
        "timing": timing or analysis.get("timing", {}),
    }
    if jury:
        payload["jury"] = jury

    _write_json(analysis_dir / FILES["analysis"], payload)
    _write_json(analysis_dir / FILES["tampering"], tampering or {})

    meta = metadata or analysis.get("metadata_forensics") or {}
    if meta:
        _write_json(analysis_dir / FILES["metadata"], meta)

    risk_payload = risk or _build_risk_from_analysis(analysis, tampering)
    _write_json(analysis_dir / FILES["risk"], risk_payload)

    if jury:
        _write_json(analysis_dir / FILES["jury"], jury)

    logger.info("Analysis bundle saved to %s", analysis_dir)


def _build_risk_from_analysis(analysis: Dict[str, Any], tampering: Dict[str, Any]) -> Dict[str, Any]:
    fusion = analysis.get("risk_fusion") or analysis.get("ensemble") or {}
    ai_det = analysis.get("ai_generation") or {}
    return {
        "risk_score": analysis.get("risk_score", fusion.get("overall_fraud_risk", 0)),
        "verdict": analysis.get("verdict", fusion.get("verdict", "UNKNOWN")),
        "confidence": analysis.get("confidence", fusion.get("confidence", 0)),
        "authenticity_score": fusion.get("authenticity_score"),
        "manipulation_score": fusion.get("manipulation_score"),
        "ai_generation_score": fusion.get("ai_generation_score") or ai_det.get("ai_generated_probability"),
        "overall_fraud_risk": fusion.get("overall_fraud_risk", analysis.get("risk_score", 0)),
        "explainability": fusion.get("explainability", []),
        "component_scores": fusion.get("component_scores", {}),
        "tampering_verdict": tampering.get("verdict"),
    }


def load_analysis_bundle(analysis_dir: Path) -> Optional[Dict[str, Any]]:
    """Load analysis bundle from split files; rebuild missing files if possible."""
    analysis_dir = Path(analysis_dir)
    if not analysis_dir.exists():
        return None

    main = _read_json(analysis_dir / FILES["analysis"])
    tampering = _read_json(analysis_dir / FILES["tampering"])
    jury = _read_json(analysis_dir / FILES["jury"])
    metadata = _read_json(analysis_dir / FILES["metadata"])
    risk = _read_json(analysis_dir / FILES["risk"])

    if main and main.get("analysis"):
        analysis = main["analysis"]
        record = {
            "analysis": analysis,
            "tampering": tampering or main.get("tampering") or _extract_tampering(analysis),
            "jury": jury or main.get("jury", {}),
            "metadata": metadata or analysis.get("metadata_forensics", {}),
            "risk": risk or _build_risk_from_analysis(analysis, tampering or {}),
            "timing": main.get("timing", analysis.get("timing", {})),
        }
        _rebuild_missing(analysis_dir, record)
        return record

    if any((analysis_dir / f).exists() for f in FILES.values()):
        return _rebuild_from_partial(analysis_dir, tampering, jury, metadata, risk)

    return None


def _extract_tampering(analysis: Dict[str, Any]) -> Dict[str, Any]:
    td = analysis.get("tampering_detection") or {}
    signals = analysis.get("signals") or {}
    return {
        "success": td.get("success", True),
        "verdict": td.get("verdict", signals.get("tampering_verdict", "UNKNOWN")),
        "severity": td.get("severity", signals.get("tampering_severity", "LOW")),
        "tampering_score": td.get("tampering_score", signals.get("tampering_score", 0)),
        "confidence": td.get("confidence", signals.get("tampering_confidence", 0)),
        "signals": td.get("signals", signals.get("tampering_signals", [])),
        "analysis": td.get("analysis", {}),
    }


def _rebuild_missing(analysis_dir: Path, record: Dict[str, Any]) -> None:
    """Write any missing split files from the loaded record."""
    paths = {k: analysis_dir / v for k, v in FILES.items()}
    if not paths["tampering"].exists() and record.get("tampering"):
        _write_json(paths["tampering"], record["tampering"])
    if not paths["risk"].exists():
        _write_json(paths["risk"], record.get("risk") or _build_risk_from_analysis(
            record["analysis"], record.get("tampering", {})
        ))
    if not paths["metadata"].exists() and record.get("metadata"):
        _write_json(paths["metadata"], record["metadata"])
    if not paths["jury"].exists() and record.get("jury"):
        _write_json(paths["jury"], record["jury"])


def _rebuild_from_partial(
    analysis_dir: Path,
    tampering: Optional[Dict],
    jury: Optional[Dict],
    metadata: Optional[Dict],
    risk: Optional[Dict],
) -> Optional[Dict[str, Any]]:
    """Attempt to reconstruct bundle from partial files."""
    for candidate in ("analysis.json",):
        main = _read_json(analysis_dir / candidate)
        if main and main.get("analysis"):
            return load_analysis_bundle(analysis_dir)
    if risk and tampering:
        return {
            "analysis": {"risk_score": risk.get("overall_fraud_risk"), "verdict": risk.get("verdict")},
            "tampering": tampering,
            "jury": jury or {},
            "metadata": metadata or {},
            "risk": risk,
            "timing": {},
        }
    return None


def bundle_exists(analysis_dir: Path) -> bool:
    analysis_dir = Path(analysis_dir)
    return (analysis_dir / FILES["analysis"]).is_file()
