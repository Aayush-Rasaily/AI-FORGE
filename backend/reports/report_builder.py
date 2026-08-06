"""
Aggregate analysis, custody, jury, and artifact data into a unified report bundle.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.database.repository import get_analysis_by_evidence_id
from backend.forensics.repository import (
    get_custody_chain,
    get_evidence_record,
    get_report_snapshots,
    verify_custody_chain,
)
from backend.utils.artifact_paths import resolve_artifact_path
from backend.utils.cache import AnalysisCache
from backend.utils.analysis_persistence import load_analysis_bundle, bundle_exists

logger = logging.getLogger("ai_forge.reports")

UPLOAD_DIR = Path("data/temp/uploads")
_bundle_cache: Dict[str, Any] = {}


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _build_executive_summary(analysis: Dict, tampering: Dict, evidence: Optional[Dict]) -> Dict[str, Any]:
    risk = _safe_float(analysis.get("risk_score") or analysis.get("forensic_score", 0) * 100)
    verdict = analysis.get("verdict") or tampering.get("verdict", "UNKNOWN")
    confidence = _safe_float(analysis.get("confidence") or tampering.get("confidence", 0))

    if risk >= 61:
        risk_level = "HIGH"
        action = "Immediate expert review and preservation of original evidence recommended."
    elif risk >= 31:
        risk_level = "MEDIUM"
        action = "Further verification against source documents and metadata review advised."
    else:
        risk_level = "LOW"
        action = "No strong manipulation indicators; routine verification sufficient."

    findings = analysis.get("findings") or tampering.get("signals") or []
    if isinstance(findings, dict):
        findings = list(findings.values()) if findings else []
    top_findings = [str(f) for f in findings[:5]]

    return {
        "verdict": verdict,
        "risk_score": round(risk, 1),
        "risk_level": risk_level,
        "confidence": round(confidence, 1),
        "recommendation": analysis.get("recommendation") or action,
        "key_findings": top_findings,
        "evidence_id": evidence.get("evidence_id") if evidence else None,
        "filename": evidence.get("original_filename") if evidence else None,
        "narrative": analysis.get("explanation") or analysis.get("recommendation", ""),
    }


def _build_technical_summary(analysis: Dict, tampering: Dict) -> Dict[str, Any]:
    signals = analysis.get("signals") or {}
    timing = analysis.get("timing") or {}
    multispectral = analysis.get("multispectral") or {}
    ensemble = analysis.get("ensemble") or {}

    modules = []
    for key in ("ela_score", "edge_density", "wavelet_score", "copy_move_score", "noise_score"):
        if key in signals:
            modules.append({"module": key.replace("_", " ").title(), "score": _safe_float(signals[key])})

    spectral = multispectral.get("fusion") or {}
    detectors = multispectral.get("detectors") or {}
    for name, det in detectors.items():
        if isinstance(det, dict):
            modules.append({
                "module": f"Spectral {name.upper()}",
                "score": _safe_float(det.get("score", 0)),
            })

    return {
        "scan_mode": analysis.get("scan_mode", "deep"),
        "module_scores": modules,
        "spectral_fusion_score": _safe_float(spectral.get("fused_score", 0)),
        "ensemble": ensemble,
        "tampering": {
            "verdict": tampering.get("verdict"),
            "severity": tampering.get("severity"),
            "score": tampering.get("tampering_score"),
            "confidence": tampering.get("confidence"),
        },
        "gan_detection": analysis.get("gan_detection", {}),
        "face_forensics": analysis.get("face_forensics", {}),
        "metadata_forensics": analysis.get("metadata_forensics", {}),
        "execution_times": timing,
        "signals": signals,
    }


def _build_evidence_summary(evidence: Optional[Dict], custody: List[Dict]) -> Dict[str, Any]:
    if not evidence:
        return {"registered": False}
    return {
        "registered": True,
        "evidence_id": evidence.get("evidence_id"),
        "original_filename": evidence.get("original_filename"),
        "media_type": evidence.get("media_type"),
        "size_bytes": evidence.get("size_bytes"),
        "sha256": evidence.get("sha256"),
        "sha512": evidence.get("sha512"),
        "intake_timestamp": evidence.get("intake_timestamp"),
        "intake_user": evidence.get("intake_user_name"),
        "custody_events": len(custody),
        "chain_verified": verify_custody_chain(evidence.get("evidence_id", "")).get("valid", False),
    }


def _build_timeline(custody: List[Dict], analysis: Dict) -> List[Dict[str, Any]]:
    timeline = []
    for event in custody:
        timeline.append({
            "timestamp": event.get("event_timestamp"),
            "type": event.get("event_type"),
            "description": event.get("action_description"),
            "actor": event.get("actor_name") or event.get("actor_id"),
            "event_hash": event.get("event_hash"),
        })
    if analysis.get("timing"):
        timeline.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "ANALYSIS_TIMING",
            "description": f"Pipeline completed in {sum(analysis['timing'].values()):.1f}s",
            "actor": "AI-FORGE",
        })
    return timeline


def _find_artifacts(evidence_id: str, analysis_dir: Path, stem: str) -> Dict[str, str]:
    artifacts = {}
    for art_type in ("ela", "edges", "wavelet", "copy_move"):
        path = resolve_artifact_path(analysis_dir, art_type, stem)
        if path.exists():
            artifacts[art_type] = str(path)
    heatmap = analysis_dir / "heatmap.png"
    if heatmap.exists():
        artifacts["heatmap"] = str(heatmap)
    explain_dir = analysis_dir / "explainability"
    if explain_dir.exists():
        for img in explain_dir.glob("*.png"):
            artifacts[f"explain_{img.stem}"] = str(img)
    return artifacts


def _evidence_file_exists(evidence_id: str) -> bool:
    try:
        files = [f for f in UPLOAD_DIR.glob(f"{evidence_id}.*") if f.is_file()]
        return bool(files)
    except Exception:
        return False


def _load_analysis_record(evidence_id: str) -> Dict[str, Any]:
    """Load analysis from split files, DB, or file cache — rebuild if partial."""
    analysis_dir = UPLOAD_DIR / "analysis" / evidence_id

    bundle = load_analysis_bundle(analysis_dir)
    if bundle and bundle.get("analysis"):
        return {
            "analysis": bundle["analysis"],
            "tampering": bundle.get("tampering", {}),
            "jury": bundle.get("jury", {}),
            "metadata": bundle.get("metadata", {}),
            "risk": bundle.get("risk", {}),
            "execution_times": bundle.get("timing", {}),
        }

    record = get_analysis_by_evidence_id(evidence_id)
    if record and record.get("analysis"):
        return record

    cached = AnalysisCache(evidence_id, analysis_dir).load()
    if cached and cached.get("analysis"):
        return {
            "analysis": cached["analysis"],
            "tampering": cached.get("tampering", {}),
            "jury": cached.get("jury", {}),
            "execution_times": cached.get("timing", {}),
        }

    if bundle_exists(analysis_dir):
        bundle = load_analysis_bundle(analysis_dir)
        if bundle:
            return {
                "analysis": bundle["analysis"],
                "tampering": bundle.get("tampering", {}),
                "jury": bundle.get("jury", {}),
                "execution_times": bundle.get("timing", {}),
            }

    if not _evidence_file_exists(evidence_id):
        raise ValueError(f"Evidence not found: {evidence_id}")

    raise ValueError(
        f"Analysis data for {evidence_id} is incomplete. Re-run forensic analysis to regenerate reports."
    )


def build_report_bundle(
    evidence_id: str,
    *,
    template: str = "full",
    jury_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build complete report data structure for any export format."""
    cache_key = f"{evidence_id}:{template}"
    if cache_key in _bundle_cache:
        return _bundle_cache[cache_key]

    record = _load_analysis_record(evidence_id)

    analysis = record.get("analysis") or {}
    tampering = record.get("tampering") or {}
    jury = jury_data or record.get("jury") or {}
    risk_data = record.get("risk") or analysis.get("risk_fusion") or {}

    evidence = get_evidence_record(evidence_id)
    custody = get_custody_chain(evidence_id)
    snapshots = get_report_snapshots(evidence_id)

    analysis_dir = UPLOAD_DIR / "analysis" / evidence_id
    stem = evidence_id
    try:
        files = list(UPLOAD_DIR.glob(f"{evidence_id}.*"))
        if files:
            stem = files[0].stem
    except Exception:
        pass

    artifacts = _find_artifacts(evidence_id, analysis_dir, stem) if analysis_dir.exists() else {}

    bundle = {
        "meta": {
            "report_id": f"RPT-{evidence_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "evidence_id": evidence_id,
            "template": template,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "platform": "AI-FORGE Digital Forensics Platform",
            "version": "2.0",
        },
        "executive_summary": _build_executive_summary(analysis, tampering, evidence),
        "technical_summary": _build_technical_summary(analysis, tampering),
        "evidence_summary": _build_evidence_summary(evidence, custody),
        "timeline": _build_timeline(custody, analysis),
        "custody_chain": custody,
        "analysis": analysis,
        "tampering": tampering,
        "jury": jury,
        "artifacts": artifacts,
        "immutable_reports": snapshots,
        "reproducibility": analysis.get("reproducibility_manifest"),
        "charts": {
            "risk_score": _safe_float(risk_data.get("overall_fraud_risk") or analysis.get("risk_score") or analysis.get("forensic_score", 0) * 100),
            "confidence": _safe_float(risk_data.get("confidence") or analysis.get("confidence", 75)),
            "authenticity_score": _safe_float(risk_data.get("authenticity_score", 0)),
            "manipulation_score": _safe_float(risk_data.get("manipulation_score", 0)),
            "ai_generation_score": _safe_float(risk_data.get("ai_generation_score", 0)),
            "module_scores": _build_technical_summary(analysis, tampering).get("module_scores", []),
        },
        "risk_fusion": risk_data,
        "explainability": risk_data.get("explainability", analysis.get("risk_fusion", {}).get("explainability", [])),
    }

    if template == "court":
        bundle["court_certification"] = _build_court_section(bundle)
    elif template == "executive":
        bundle = {k: v for k, v in bundle.items() if k in (
            "meta", "executive_summary", "evidence_summary", "timeline", "charts"
        )}
    elif template == "technical":
        bundle = {k: v for k, v in bundle.items() if k in (
            "meta", "technical_summary", "analysis", "tampering", "artifacts", "charts", "timeline"
        )}
    elif template == "evidence":
        bundle = {k: v for k, v in bundle.items() if k in (
            "meta", "evidence_summary", "custody_chain", "timeline", "immutable_reports", "charts"
        )}

    _bundle_cache[cache_key] = bundle
    return bundle


def _build_court_section(bundle: Dict) -> Dict[str, Any]:
    ev = bundle.get("evidence_summary") or {}
    exec_sum = bundle.get("executive_summary") or {}
    return {
        "certification": (
            "This report was generated by AI-FORGE, an AI-assisted digital forensic analysis platform. "
            "Results are based on automated forensic algorithms and should be reviewed by a qualified expert "
            "before use in legal proceedings."
        ),
        "chain_of_custody_attestation": (
            f"Evidence chain contains {ev.get('custody_events', 0)} documented events. "
            f"Chain integrity: {'VERIFIED' if ev.get('chain_verified') else 'UNVERIFIED'}."
        ),
        "hash_attestation": {
            "sha256": ev.get("sha256"),
            "sha512": ev.get("sha512"),
        },
        "findings_for_court": exec_sum.get("key_findings", []),
        "verdict": exec_sum.get("verdict"),
        "risk_level": exec_sum.get("risk_level"),
    }
