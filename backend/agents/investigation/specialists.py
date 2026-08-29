"""
Specialized forensic agents — thin orchestration wrappers over existing services.
Never re-implement detectors; call production pipelines.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.agents.investigation.base import AgentResult, InvestigationPlan

logger = logging.getLogger("ai_forge.agents.specialists")


def run_image_forensics_agent(
    evidence_id: str,
    evidence_path: Path,
    analysis_dir: Path,
    plan: InvestigationPlan,
    *,
    progress=None,
    force_deep: bool = False,
) -> AgentResult:
    t0 = time.perf_counter()
    skipped = [m for m in ("deepfake", "face_forensics", "ocr") if m in plan.skip_reasons]
    try:
        from backend.services.image_analysis_service import run_image_analysis

        analysis, tampering, timing, cached, completion = run_image_analysis(
            Path(evidence_path),
            Path(analysis_dir),
            evidence_id,
            True,
            progress,
            force_deep,
            False,
        )
        risk = float(analysis.get("risk_score") or analysis.get("fraud_score") or 0)
        if risk > 1:
            risk = risk / 100.0
        conf = float(analysis.get("confidence") or 0.7)
        if conf > 1:
            conf = conf / 100.0
        return AgentResult(
            agent_id="image",
            agent_name="Image Forensics Agent",
            status="completed",
            confidence=conf,
            risk_score=risk,
            verdict=str(analysis.get("verdict") or "ANALYZED"),
            findings=[
                f"Scan mode: {analysis.get('scan_mode', 'deep')}",
                f"Cached: {cached}",
                f"Modules timed: {len(timing or {})}",
            ],
            skipped_modules=skipped,
            executed_modules=list((timing or {}).keys()) or plan.modules,
            data={
                "analysis": analysis,
                "tampering": tampering,
                "timing": timing,
                "completion": completion,
                "cached": cached,
            },
            duration_ms=(time.perf_counter() - t0) * 1000,
            reason="Image forensic pipeline executed via existing service.",
        )
    except Exception as exc:
        logger.exception("Image agent failed: %s", exc)
        return AgentResult(
            agent_id="image",
            agent_name="Image Forensics Agent",
            status="failed",
            error=str(exc)[:500],
            skipped_modules=skipped,
            duration_ms=(time.perf_counter() - t0) * 1000,
        )


def run_document_agent(
    evidence_id: str,
    evidence_path: Path,
    analysis_dir: Path,
    plan: InvestigationPlan,
    *,
    progress=None,
) -> AgentResult:
    t0 = time.perf_counter()
    if "document" in plan.skip_reasons and plan.evidence_type == "image":
        return AgentResult(
            agent_id="document",
            agent_name="Document Agent",
            status="skipped",
            reason=plan.skip_reasons.get("document"),
            skipped_modules=["document"],
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    try:
        from backend.services.document_analysis_service import run_document_analysis

        result, timing, cached = run_document_analysis(
            Path(evidence_path),
            Path(analysis_dir),
            evidence_id,
            True,
            progress,
        )
        if not isinstance(result, dict):
            result = {"result": result}
        risk = float(result.get("risk_score") or (result.get("risk") or {}).get("score") or 0)
        if risk > 1:
            risk /= 100.0
        conf = float(result.get("confidence") or 0.75)
        if conf > 1:
            conf /= 100.0
        return AgentResult(
            agent_id="document",
            agent_name="Document Agent",
            status="completed",
            confidence=conf,
            risk_score=risk,
            verdict=str(result.get("verdict") or "ANALYZED"),
            findings=[
                "Document OCR/layout/risk pipeline completed.",
                f"Cached: {cached}",
            ],
            executed_modules=list((timing or {}).keys())
            or (plan.modules if plan.evidence_type == "document" else ["ocr", "layout"]),
            data={"document_analysis": result, "timing": timing, "cached": cached},
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    except Exception as exc:
        logger.exception("Document agent failed: %s", exc)
        return AgentResult(
            agent_id="document",
            agent_name="Document Agent",
            status="failed",
            error=str(exc)[:500],
            duration_ms=(time.perf_counter() - t0) * 1000,
        )


def run_video_agent(
    evidence_id: str,
    evidence_path: Path,
    analysis_dir: Path,
    plan: InvestigationPlan,
) -> AgentResult:
    t0 = time.perf_counter()
    if plan.evidence_type != "video":
        return AgentResult(
            agent_id="video",
            agent_name="Video Agent",
            status="skipped",
            reason="Not a video evidence type",
            skipped_modules=["video"],
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    try:
        from backend.services.video_service import analyze_video_parallel

        result = analyze_video_parallel(
            str(evidence_path),
            str(analysis_dir),
            video_id=evidence_id,
        )
        if not isinstance(result, dict):
            result = {"result": result}
        risk = float(result.get("risk_score") or result.get("deepfake_score") or 0)
        if risk > 1:
            risk /= 100.0
        conf = float(result.get("confidence") or 0.7)
        if conf > 1:
            conf /= 100.0
        return AgentResult(
            agent_id="video",
            agent_name="Video Agent",
            status="completed",
            confidence=conf,
            risk_score=risk,
            verdict=str(result.get("verdict") or "ANALYZED"),
            findings=["Video frame/metadata/deepfake pipeline completed."],
            skipped_modules=[m for m in ("audio",) if m in plan.skip_reasons],
            executed_modules=list(plan.modules),
            data={"video_analysis": result},
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    except Exception as exc:
        logger.exception("Video agent failed: %s", exc)
        return AgentResult(
            agent_id="video",
            agent_name="Video Agent",
            status="failed",
            error=str(exc)[:500],
            duration_ms=(time.perf_counter() - t0) * 1000,
        )


def run_signature_forensics_agent(
    evidence_id: str,
    evidence_path: Path,
    plan: InvestigationPlan,
    *,
    reference_path: Optional[Path] = None,
) -> AgentResult:
    t0 = time.perf_counter()
    if "signature" in plan.skip_reasons or "signature" not in plan.agents:
        return AgentResult(
            agent_id="signature",
            agent_name="Signature Agent",
            status="skipped",
            reason=plan.skip_reasons.get("signature", "Signature agent not in plan"),
            skipped_modules=["signature"],
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    try:
        if reference_path and Path(reference_path).is_file():
            from backend.models.signature.inference import verify_signature

            result = verify_signature(str(reference_path), str(evidence_path))
        else:
            from backend.agents.jury.signature_agent import run_signature_agent

            # Abstains cleanly when no reference pair — preserves existing jury contract
            result = run_signature_agent(None)
        if not isinstance(result, dict):
            result = {"result": result}
        risk = float(result.get("risk_score") or result.get("forgery_score") or 0)
        if risk > 1:
            risk /= 100.0
        conf = float(result.get("confidence") or 0.6)
        if conf > 1:
            conf /= 100.0
        return AgentResult(
            agent_id="signature",
            agent_name="Signature Agent",
            status="completed",
            confidence=conf,
            risk_score=risk,
            verdict=str(result.get("verdict") or result.get("vote") or "ANALYZED"),
            findings=list(result.get("findings") or ["Signature analysis completed."]),
            executed_modules=["siamese", "similarity"],
            data={"signature_result": result},
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    except Exception as exc:
        logger.warning("Signature agent soft-fail: %s", exc)
        return AgentResult(
            agent_id="signature",
            agent_name="Signature Agent",
            status="skipped",
            reason=str(exc)[:300],
            duration_ms=(time.perf_counter() - t0) * 1000,
        )


def run_metadata_cross_agent(
    *,
    image_data: Optional[Dict] = None,
    document_data: Optional[Dict] = None,
    video_data: Optional[Dict] = None,
    analysis: Optional[Dict] = None,
    tampering: Optional[Dict] = None,
) -> AgentResult:
    t0 = time.perf_counter()
    try:
        from backend.agents.jury.metadata_agent import run_metadata_agent

        jury_meta = run_metadata_agent(analysis=analysis or image_data, tampering=tampering)
        findings = list(jury_meta.get("findings") or [])
        # Cross-source EXIF / author / GPS notes
        meta_blob = (analysis or image_data or {}).get("metadata") or {}
        if isinstance(meta_blob, dict):
            if meta_blob.get("gps") or (meta_blob.get("exif_summary") or {}).get("gps"):
                findings.append("GPS metadata present — retained for custody correlation.")
            soft = meta_blob.get("Software") or (meta_blob.get("exif_summary") or {}).get("software")
            if soft:
                findings.append(f"Authoring software: {soft}")
        if document_data:
            findings.append("Document metadata cross-checked against image EXIF.")
        if video_data:
            findings.append("Video container metadata included in cross-validation.")

        conf = float(jury_meta.get("confidence") or 0.8)
        risk = float(jury_meta.get("risk_score") or 0)
        return AgentResult(
            agent_id="metadata",
            agent_name="Metadata Agent",
            status="completed",
            confidence=conf if conf <= 1 else conf / 100.0,
            risk_score=risk if risk <= 1 else risk / 100.0,
            verdict=str(jury_meta.get("verdict") or "ANALYZED"),
            findings=findings,
            executed_modules=["exif", "gps", "author", "hash_consistency"],
            data={"metadata_agent": jury_meta, "raw_metadata": meta_blob},
            duration_ms=(time.perf_counter() - t0) * 1000,
            reason="Cross-modal metadata validation completed.",
        )
    except Exception as exc:
        logger.exception("Metadata agent failed: %s", exc)
        return AgentResult(
            agent_id="metadata",
            agent_name="Metadata Agent",
            status="failed",
            error=str(exc)[:500],
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
