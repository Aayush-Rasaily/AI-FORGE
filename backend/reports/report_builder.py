"""
Aggregate analysis, custody, jury, and artifact data into a unified report bundle.
"""

from __future__ import annotations

import json
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
from backend.evidence.paths import find_original_evidence
from backend.utils.artifact_paths import resolve_artifact_path
from backend.utils.cache import AnalysisCache
from backend.utils.analysis_persistence import load_analysis_bundle, bundle_exists

from backend.reports.legal_sections import build_legal_sections

logger = logging.getLogger("ai_forge.reports")

UPLOAD_DIR = Path("data/temp/uploads")
_bundle_cache: Dict[str, Any] = {}


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _build_executive_summary(
    analysis: Dict,
    tampering: Dict,
    evidence: Optional[Dict],
    explainable: Optional[Dict[str, Any]] = None,
    forensic_dossier: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    risk = _safe_float(analysis.get("risk_score") or analysis.get("forensic_score", 0) * 100)
    verdict = analysis.get("verdict") or tampering.get("verdict", "UNKNOWN")
    confidence = _safe_float(
        (explainable or {}).get("primary_confidence")
        or analysis.get("confidence")
        or tampering.get("confidence", 0)
    )
    xai = explainable or analysis.get("explainable_ai") or {}

    tampering_level = str(xai.get("tampering_probability") or "").upper()
    if tampering_level == "HIGH" or risk >= 61:
        risk_level = "HIGH"
    elif tampering_level == "MEDIUM" or risk >= 31:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    reasoning = analysis.get("forensic_reasoning") or {}
    findings = list(xai.get("key_evidence") or [])
    if not findings and reasoning.get("findings"):
        findings = [f.get("finding") for f in reasoning["findings"][:5] if f.get("finding")]
    if not findings:
        findings = analysis.get("findings") or tampering.get("signals") or []
    if isinstance(findings, dict):
        findings = list(findings.values()) if findings else []
    top_findings = [str(f) for f in findings[:5]]

    primary_rec = None
    if reasoning.get("findings"):
        primary_rec = (reasoning["findings"][0] or {}).get("recommendation")

    # Extract the Human-Centered Explanations from the Dossier
    xai_findings_strings = []
    investigation_text = ""
    
    if forensic_dossier and forensic_dossier.get("explanations"):
        for exp in forensic_dossier["explanations"]:
            block = (
                f"Finding: {exp.get('title', '')}\n"
                f"Location: Page {exp.get('page', 1)} - {exp.get('location', '')}\n"
                f"Reason recorded during examination: {exp.get('reason', '')}\n"
                f"Possible consequence: {exp.get('impact', '')}\n"
                f"Recommended verification: Cross-reference with original issuer"
            )
            xai_findings_strings.append(block)
            investigation_text += block + "\n\n"
    
    # If no XAI explanations, fallback
    final_key_findings = xai_findings_strings if xai_findings_strings else top_findings
    final_inv_summary = investigation_text.strip() if investigation_text else (xai.get("investigation_summary") or analysis.get("detailed_investigation") or "")
    
    return {
        "verdict": verdict,
        "risk_score": round(risk, 1),
        "risk_level": risk_level,
        "confidence": round(confidence, 1),
        "tampering_probability": xai.get("tampering_probability"),
        "recommendation": primary_rec or analysis.get("recommendation") or "",
        "key_findings": final_key_findings,
        "evidence_id": evidence.get("evidence_id") if evidence else None,
        "filename": evidence.get("original_filename") if evidence else None,
        "narrative": xai.get("executive_summary") or analysis.get("executive_summary_text") or analysis.get("explanation") or "",
        "investigation_summary": final_inv_summary,
        "technical_explanation": xai.get("technical_explanation") or analysis.get("technical_explanation") or "",
        "court_explanation": xai.get("court_explanation") or analysis.get("court_explanation") or "",
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
        completed_at = (
            analysis.get("completed_at")
            or analysis.get("generated_at")
            or analysis.get("analysis_completed_at")
        )
        if not completed_at:
            return timeline
        timeline.append({
            "timestamp": completed_at,
            "type": "ANALYSIS_TIMING",
            "description": f"Pipeline completed in {sum(analysis['timing'].values()):.1f}s",
            "actor": "Forensic Examination Service",
        })
    return timeline


def _find_artifacts(evidence_id: str, analysis_dir: Path, stem: str) -> Dict[str, str]:
    artifacts = {}
    original = find_original_evidence(evidence_id)
    if original and original.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}:
        artifacts["evidence_original"] = str(original)

    for art_type in ("ela", "edges", "wavelet", "copy_move", "noise"):
        path = resolve_artifact_path(evidence_id, art_type, analysis_dir, stem)
        if path and path.exists():
            artifacts[art_type] = str(path)
    heatmap = analysis_dir / "heatmap.png"
    if heatmap.exists():
        artifacts["heatmap"] = str(heatmap)

    # Forgery localization engine outputs
    for key, fname in (
        ("localization_heatmap", "localization_heatmap.png"),
        ("forgery_mask", "forgery_mask.png"),
        ("forgery_mask_binary", "forgery_mask_binary.png"),
        ("localization_highlight", "localization_highlight.png"),
        ("localization_diff", "localization_diff.png"),
        ("localization_regions", "localization_regions.png"),
        ("localization_polygons", "localization_polygons.png"),
        ("localization_annotated", "localization_annotated.png"),
        ("localization_attention", "localization_attention.png"),
    ):
        p = analysis_dir / fname
        if p.is_file():
            artifacts[key] = str(p)

    explain_dir = analysis_dir / "explainability"
    if explain_dir.exists():
        for img in explain_dir.glob("*.png"):
            artifacts[f"explain_{img.stem}"] = str(img)
    return artifacts


def _load_explainable_ai(analysis_dir: Path) -> Dict[str, Any]:
    try:
        from backend.engines.explain_engine import load_explainable_ai
        return load_explainable_ai(analysis_dir)
    except Exception:
        path = analysis_dir / "explainable_ai.json"
        if not path.is_file():
            return {}
        try:
            import json
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}


def _load_forensic_reasoning(evidence_id: str, analysis_dir: Path) -> Dict[str, Any]:
    path = analysis_dir / "forensic_reasoning.json"
    if not path.is_file():
        return {}
    try:
        import json
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _load_localization_for_report(evidence_id: str, analysis_dir: Path) -> Dict[str, Any]:
    """Ensure localization artifacts exist and return summary for report templates."""
    try:
        from backend.analysis.forgery_localization import ensure_localization, load_localization

        data = load_localization(evidence_id)
        if not data or not (analysis_dir / "localization_heatmap.png").is_file():
            data = ensure_localization(evidence_id)
        if not data:
            return {}
        return {
            "explanation": data.get("explanation"),
            "detailed_investigation": data.get("detailed_investigation") or data.get("explanation"),
            "regions": (data.get("regions") or [])[:20],
            "layers_used": data.get("layers_used") or [],
            "coverage": data.get("coverage"),
            "video_timeline": data.get("video_timeline") or {},
            "views": data.get("views") or {},
            "files": data.get("files") or {},
            "investigation_panel": data.get("investigation_panel") or {},
        }
    except Exception as exc:
        logger.warning("localization_for_report_failed | %s | %s", evidence_id, exc)
        return {}


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
    localization = _load_localization_for_report(evidence_id, analysis_dir) if analysis_dir.exists() else {}
    forensic_reasoning = (
        analysis.get("forensic_reasoning")
        or _load_forensic_reasoning(evidence_id, analysis_dir)
        or {}
    )
    if forensic_reasoning and not analysis.get("forensic_reasoning"):
        analysis = {**analysis, "forensic_reasoning": forensic_reasoning}
    explainable_ai = (
        analysis.get("explainable_ai")
        or _load_explainable_ai(analysis_dir)
        or (localization or {}).get("explainable_ai")
        or {}
    )
    if explainable_ai and not analysis.get("explainable_ai"):
        analysis = {**analysis, "explainable_ai": explainable_ai}
    # Re-scan artifacts after localization may have written new files
    if localization and analysis_dir.exists():
        artifacts = _find_artifacts(evidence_id, analysis_dir, stem)

    canonical_findings = []
    findings_summary = {}
    if analysis_dir.exists():
        try:
            from backend.services.forensic_findings_service import get_or_build_forensic_findings
            canonical_payload = get_or_build_forensic_findings(evidence_id, analysis_dir)
            canonical_findings = canonical_payload.get("findings") or []
            findings_summary = canonical_payload.get("summary") or {}
        except Exception as exc:
            logger.warning("report_canonical_findings_failed | %s | %s", evidence_id, exc)

    # Build structured region findings (Where, What, Why, Confidence, Detector, Evidence, Impact)
    if isinstance(jury, list):
        forensic_dossier = analysis.get("forensic_dossier") or {}
    else:
        forensic_dossier = (
            jury.get("fusion", {}).get("forensic_dossier")
            or jury.get("forensic_dossier")
            or analysis.get("forensic_dossier")
            or {}
        )
    dossier_path = analysis_dir / "forensic_dossier.json"
    if dossier_path.is_file():
        try:
            loaded_dossier = json.loads(dossier_path.read_text(encoding="utf-8"))
            if isinstance(loaded_dossier, dict):
                forensic_dossier = loaded_dossier
        except (OSError, json.JSONDecodeError):
            logger.warning("report_dossier_load_failed | %s", evidence_id)
        
    raw_regions = (localization or {}).get("regions") or (analysis.get("localization") or {}).get("regions") or []
    region_findings = []
    for i, reg in enumerate(raw_regions[:25]):
        from backend.utils.bbox_schema import region_bbox as _rb  # noqa
        b = _rb(reg)
        coords_str = f"({int(b.get('x', 0))}, {int(b.get('y', 0))})"
        detectors_list = reg.get("detectors") or [lbl for lbl, f in (reg.get("detector_votes") or {}).items() if f] or ["Ensemble"]
        conf_val = reg.get("confidence_pct") or (round(reg["confidence"] * 100, 1) if reg.get("confidence", 0) <= 1.0 else reg.get("confidence"))
        
        region_findings.append({
            "region_id": reg.get("region_id") or i + 1,
            "where": f"Page {reg.get('page', 1)} — {reg.get('location') or reg.get('quadrant') or 'Center'} {coords_str}",
            "what": reg.get("edit_type") or reg.get("manipulation") or "Object Replacement",
            "why": reg.get("reason") or "Forensic signal mismatch",
            "confidence": conf_val,
            "risk": reg.get("risk_level") or reg.get("severity") or (
                "High" if conf_val >= 70 else "Medium"
            ),
            "detector": ", ".join(detectors_list),
            "evidence": "; ".join(reg.get("evidence") or [reg.get("reason") or "Signal anomaly"]),
            "potential_impact": "High risk of fraudulent representation" if conf_val >= 70 else "Medium risk of localized editing",
        })

    # Build page-by-page investigation audit
    doc_issues = (analysis.get("document_intelligence") or {}).get("issues") or []
    page_investigation = []
    max_pages = max([reg.get("page", 1) for reg in raw_regions] + [iss.get("page_number", 1) for iss in doc_issues] + [1])
    for p in range(1, max_pages + 1):
        p_regs = [r for r in region_findings if f"Page {p}" in r["where"]]
        p_issues = [iss for iss in doc_issues if iss.get("page_number") == p]
        if p_regs or p_issues:
            status = "⚠ Suspicious"
            reasons = [r["why"] for r in p_regs] + [iss.get("description", "") for iss in p_issues]
            page_investigation.append({
                "page": p,
                "status": status,
                "findings_count": len(p_regs) + len(p_issues),
                "reasons": list(set(filter(None, reasons))),
            })
        else:
            page_investigation.append({
                "page": p,
                "status": "✓ Authentic",
                "findings_count": 0,
                "reasons": ["No anomaly detected"],
            })

    # Build structured OCR field-level findings
    try:
        from backend.analysis.localization.ocr_diff import extract_structured_fields
        ocr_field_findings = extract_structured_fields(analysis)
    except Exception:
        ocr_field_findings = []

    # Court Ready Extract
    signature_analysis = analysis.get("signature_verification") or analysis.get("signature_result") or {}
    logo_analysis = analysis.get("logo_verification") or analysis.get("logo_result") or {}
    metadata_anomalies = analysis.get("metadata_forensics") or analysis.get("metadata") or {}
    video_timeline = analysis.get("video_timeline") or (localization or {}).get("suspicious_intervals") or (analysis.get("video") or {}).get("timeline") or []
    
    # Extract AI Jury Table data
    ai_jury_table = []
    if jury and jury.get("agent_verdicts"):
        for det, val in jury.get("agent_verdicts", {}).items():
            ai_jury_table.append({
                "Detector": det,
                "Decision": val.get("verdict", "Authentic"),
                "Confidence": val.get("confidence", 0),
                "Reason": val.get("reason", "Consistent")
            })

    # Consolidate Timeline
    timeline_arr = _build_timeline(custody, analysis)
    
    bundle = {
        "meta": {
            "report_id": f"RPT-{evidence_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "evidence_id": evidence_id,
            "template": template,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "platform": "AI-FORGE Digital Forensics Platform",
            "version": "2.0",
        },
        "executive_summary": _build_executive_summary(analysis, tampering, evidence, explainable_ai, forensic_dossier),
        "technical_summary": _build_technical_summary(analysis, tampering),
        "evidence_summary": _build_evidence_summary(evidence, custody),
        "timeline": _build_timeline(custody, analysis),
        "custody_chain": custody,
        "analysis": analysis,
        "tampering": tampering,
        "jury": jury,
        "artifacts": artifacts,
        "localization": localization,
        "region_findings": region_findings,
        "ocr_field_findings": ocr_field_findings,
        "page_investigation": page_investigation,
        "video_timeline": (analysis.get("video_analysis") or {}).get("timeline") or analysis.get("timeline") or [],
        "immutable_reports": snapshots,
        "reproducibility": analysis.get("reproducibility_manifest"),
        "forensic_dossier": forensic_dossier,
        "dossier_jury": (
            forensic_dossier.get("ai_jury")
            or forensic_dossier.get("jury_consensus")
            or {}
        ) if isinstance(forensic_dossier, dict) else {},
        "canonical_findings": canonical_findings,
        "findings_summary": findings_summary,
        "charts": {
            "risk_score": _safe_float(risk_data.get("overall_fraud_risk") or analysis.get("risk_score") or analysis.get("forensic_score", 0) * 100),
            "confidence": _safe_float(risk_data.get("confidence") or analysis.get("confidence", 75)),
            "authenticity_score": _safe_float(risk_data.get("authenticity_score", 0)),
            "manipulation_score": _safe_float(risk_data.get("manipulation_score", 0)),
            "ai_generation_score": _safe_float(risk_data.get("ai_generation_score", 0)),
            "module_scores": _build_technical_summary(analysis, tampering).get("module_scores", []),
        },
        "risk_fusion": risk_data,
        "explainability": explainable_ai.get("key_evidence") or risk_data.get(
            "explainability", analysis.get("risk_fusion", {}).get("explainability", [])
        ),
        "detector_outputs": analysis.get("detector_outputs") or [],
        "evidence_fusion": analysis.get("evidence_fusion") or {},
        "forensic_reasoning": analysis.get("forensic_reasoning") or {},
        "explainable_ai": explainable_ai,
        "detailed_investigation": (
            explainable_ai.get("investigation_summary")
            or (localization or {}).get("detailed_investigation")
            or analysis.get("detailed_investigation")
            or analysis.get("explanation")
        ),
        "technical_explanation": explainable_ai.get("technical_explanation") or analysis.get("technical_explanation"),
        "court_explanation": explainable_ai.get("court_explanation") or analysis.get("court_explanation"),
        "signature_analysis": signature_analysis,
        "logo_analysis": logo_analysis,
        "metadata_anomalies": metadata_anomalies,
        "video_timeline": video_timeline,
        "ai_jury_table": ai_jury_table,
    }

    bundle["legal"] = build_legal_sections(bundle)

    case_id = (evidence or {}).get("investigation_id")
    if case_id:
        try:
            from backend.graph.case_correlation import get_case_graph
            graph = get_case_graph(case_id, focus_evidence_id=evidence_id)
            bundle["case_context"] = {"case_id": case_id}
            bundle["investigation_graph"] = graph
            bundle["case_correlation"] = {
                "findings": graph.get("findings") or [],
                "chains": graph.get("chains") or [],
                "stats": graph.get("stats") or {},
            }
        except Exception:
            bundle["case_context"] = {"case_id": case_id}
            bundle["investigation_graph"] = {}
            bundle["case_correlation"] = {}

    if template == "court":
        bundle["court_certification"] = _build_court_section(bundle)
        bundle["report_type"] = "Court-Ready Forensic Evidence Report"
    elif template == "executive":
        bundle = {k: v for k, v in bundle.items() if k in (
            "meta", "executive_summary", "evidence_summary", "timeline", "charts",
            "localization", "artifacts", "legal", "legal_integrity", "recommendations",
            "forensic_dossier", "report_type", "signature_analysis", "logo_analysis",
            "metadata_anomalies", "ai_jury_table", "page_investigation", "ocr_field_findings",
            "canonical_findings", "findings_summary"
        )}
        bundle["report_type"] = "Executive Investigation Summary"
    elif template == "technical" or template == "court":
        bundle = {k: v for k, v in bundle.items() if k in (
            "meta", "technical_summary", "analysis", "tampering", "artifacts",
            "charts", "timeline", "localization", "legal", "legal_integrity",
            "detector_outputs", "forensic_reasoning", "custody_chain",
            "region_findings", "ocr_field_findings", "forensic_dossier", "report_type",
            "signature_analysis", "logo_analysis", "metadata_anomalies", "ai_jury_table",
            "page_investigation", "executive_summary", "evidence_summary", "jury",
            "canonical_findings", "findings_summary"
        )}
        bundle["report_type"] = "Technical Forensic Analysis Report"
    elif template == "evidence":
        bundle = {k: v for k, v in bundle.items() if k in (
            "meta", "evidence_summary", "custody_chain", "timeline", "immutable_reports",
            "charts", "executive_summary", "region_findings", "ocr_field_findings",
            "forensic_dossier", "signature_analysis", "logo_analysis",
            "metadata_anomalies", "jury", "canonical_findings", "findings_summary"
        )}

    _bundle_cache[cache_key] = bundle
    return bundle


def _build_court_section(bundle: Dict) -> Dict[str, Any]:
    ev = bundle.get("evidence_summary") or {}
    exec_sum = bundle.get("executive_summary") or {}
    return {
        "certification": (
            "This report records the observations produced by the AI-FORGE digital forensic examination "
            "workflow. The findings should be reviewed by a qualified forensic examiner before use in "
            "legal proceedings."
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
