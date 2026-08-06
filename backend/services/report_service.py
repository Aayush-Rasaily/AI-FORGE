"""
Report Service — generate / status / download using cached analysis only.

Never re-runs forensic models. Completes in ~1–3 seconds when analysis JSON exists.
"""

from __future__ import annotations

import logging
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

from backend.evidence.paths import get_analysis_dir
from backend.pipeline.report_manager import (
    analysis_exists,
    generate_reports,
    get_status,
    read_status,
    write_status,
)
from backend.reports.pdf_exporter import ensure_report_pdf

logger = logging.getLogger("ai_forge.report_service")

CANONICAL = {
    "pdf": "report.pdf",
    "executive": "report_executive.pdf",
    "court": "report_court.pdf",
    "technical": "report_technical.pdf",
    "json": "report.json",
    "html": "report.html",
    "docx": "report.docx",
}


def _download_urls(evidence_id: str) -> Dict[str, str]:
    return {
        "pdf": f"/api/report/{evidence_id}/download?format=pdf",
        "court": f"/api/report/{evidence_id}/download?format=pdf&template=court",
        "executive": f"/api/report/{evidence_id}/download?format=pdf&template=executive",
        "json": f"/api/report/{evidence_id}/download?format=json",
        "html": f"/api/report/{evidence_id}/download?format=html",
        "docx": f"/api/report/{evidence_id}/download?format=docx",
    }


def _existing_files(analysis_dir: Path) -> Dict[str, str]:
    files = {}
    for key, name in CANONICAL.items():
        p = analysis_dir / name
        if p.is_file() and p.stat().st_size > 100:
            files[key] = str(p)
    return files


def report_ready(analysis_dir: Path) -> bool:
    pdf = analysis_dir / "report.pdf"
    return pdf.is_file() and pdf.stat().st_size > 500


def get_report_payload(evidence_id: str) -> Dict[str, Any]:
    """
    GET /api/report/{id} — return ready state + download URLs.
    If PDF missing but analysis exists, generate synchronously (cached analysis only).
    """
    logger.info("Report status requested | evidence_id=%s", evidence_id)

    if not analysis_exists(evidence_id):
        return {
            "success": True,
            "evidence_id": evidence_id,
            "status": "pending",
            "progress": 0,
            "report_ready": False,
            "ready": False,
            "message": "Analysis not found. Run forensic analysis first.",
            "download_urls": _download_urls(evidence_id),
            "files": {},
        }

    analysis_dir = get_analysis_dir(evidence_id, create=True)

    if report_ready(analysis_dir):
        files = _existing_files(analysis_dir)
        write_status(analysis_dir, status="completed", progress=100, report_ready=True, files=files)
        logger.info("Report ready | evidence_id=%s", evidence_id)
        return {
            "success": True,
            "evidence_id": evidence_id,
            "status": "ready",
            "progress": 100,
            "report_ready": True,
            "ready": True,
            "download_urls": _download_urls(evidence_id),
            "files": files,
            "message": "Report ready.",
        }

    # Analysis present — generate now from cached JSON (no model re-run)
    logger.info("Report generation started | evidence_id=%s", evidence_id)
    write_status(analysis_dir, status="processing", progress=10, report_ready=False)
    try:
        logger.info("Analysis loaded | evidence_id=%s", evidence_id)
        meta = generate_reports(evidence_id, background=False)
        files = _existing_files(analysis_dir)
        ready = report_ready(analysis_dir)
        if not ready:
            # Ensure full PDF even if companion pipeline partially failed
            ensure_report_pdf(evidence_id, analysis_dir)
            files = _existing_files(analysis_dir)
            ready = report_ready(analysis_dir)
        logger.info("PDF generated | evidence_id=%s ready=%s", evidence_id, ready)
        write_status(
            analysis_dir,
            status="completed" if ready else "failed",
            progress=100 if ready else 50,
            report_ready=ready,
            files=files,
            errors=meta.get("errors") if isinstance(meta, dict) else {},
        )
        logger.info("Saved | Ready | evidence_id=%s ready=%s", evidence_id, ready)
        return {
            "success": ready,
            "evidence_id": evidence_id,
            "status": "ready" if ready else "failed",
            "progress": 100 if ready else 50,
            "report_ready": ready,
            "ready": ready,
            "download_urls": _download_urls(evidence_id),
            "files": files,
            "errors": (meta.get("errors") if isinstance(meta, dict) else {}) or {},
            "message": "Report ready." if ready else "Report generation incomplete.",
            "reason": None if ready else "Report generation incomplete.",
        }
    except Exception as exc:
        reason = str(exc)[:800]
        logger.error("Report generation failed | evidence_id=%s\n%s", evidence_id, traceback.format_exc())
        write_status(analysis_dir, status="failed", progress=0, report_ready=False, reason=reason)
        return {
            "success": False,
            "evidence_id": evidence_id,
            "status": "failed",
            "reason": reason,
            "progress": 0,
            "report_ready": False,
            "ready": False,
            "download_urls": _download_urls(evidence_id),
            "files": _existing_files(analysis_dir),
            "message": "Report generation failed.",
        }


def start_report_generation(evidence_id: str) -> Dict[str, Any]:
    """
    POST /api/report/{id}/generate
    If already ready → return ready immediately.
    Else queue / run generation from cached analysis.
    """
    logger.info("Report generation started | evidence_id=%s", evidence_id)

    if not analysis_exists(evidence_id):
        return {
            "success": False,
            "evidence_id": evidence_id,
            "status": "failed",
            "reason": "Analysis not found. Run forensic analysis first.",
        }

    analysis_dir = get_analysis_dir(evidence_id, create=True)
    if report_ready(analysis_dir):
        return {
            "success": True,
            "evidence_id": evidence_id,
            "status": "ready",
            "report_ready": True,
            "ready": True,
            "download_urls": _download_urls(evidence_id),
            "message": "Report already ready.",
        }

    write_status(analysis_dir, status="generating", progress=5, report_ready=False)

    # Background generation so POST returns quickly
    try:
        generate_reports(evidence_id, background=True)
    except Exception as exc:
        # Fallback sync
        logger.warning("Background queue failed, running sync: %s", exc)
        return get_report_payload(evidence_id)

    return {
        "success": True,
        "evidence_id": evidence_id,
        "status": "generating",
        "progress": 5,
        "report_ready": False,
        "ready": False,
        "download_urls": _download_urls(evidence_id),
        "message": "Generating professional forensic report...",
        "estimated_seconds": 3,
    }


def stream_download(
    evidence_id: str,
    *,
    fmt: str = "pdf",
    template: str = "full",
) -> Dict[str, Any]:
    """
    Resolve a downloadable file path. Generates from cache if missing.
    Returns {path, filename, media_type} or {status:failed, reason}.
    """
    logger.info("Download requested | evidence_id=%s format=%s template=%s", evidence_id, fmt, template)

    if not analysis_exists(evidence_id):
        return {"status": "failed", "reason": "Analysis not found."}

    analysis_dir = get_analysis_dir(evidence_id, create=True)
    fmt = (fmt or "pdf").lower()
    template = (template or "full").lower()

    media = {
        "pdf": "application/pdf",
        "json": "application/json",
        "html": "text/html",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    name_map = {
        ("pdf", "full"): "report.pdf",
        ("pdf", "executive"): "report_executive.pdf",
        ("pdf", "court"): "report_court.pdf",
        ("pdf", "technical"): "report_technical.pdf",
        ("json", "full"): "report.json",
        ("html", "full"): "report.html",
        ("docx", "full"): "report.docx",
    }
    filename = name_map.get((fmt, template), CANONICAL.get(fmt, f"report.{fmt}"))
    path = analysis_dir / filename

    try:
        if fmt == "pdf" and template == "full":
            if not (path.is_file() and path.stat().st_size > 500):
                logger.info("PDF missing — generating from cached analysis | %s", evidence_id)
                path = ensure_report_pdf(evidence_id, analysis_dir)
        elif not (path.is_file() and path.stat().st_size > 100):
            from backend.reports.exporter import export_report
            import shutil

            result = export_report(evidence_id, format=fmt, template=template)
            src = Path(result["file_path"])
            if src.exists():
                if src.resolve() != path.resolve():
                    shutil.copy2(src, path)
                path = path if path.exists() else src

        if not path.is_file() or path.stat().st_size < 100:
            return {"status": "failed", "reason": "Report file could not be generated."}

        logger.info("Completed download resolve | %s → %s (%s bytes)", evidence_id, path.name, path.stat().st_size)
        return {
            "status": "ready",
            "path": str(path),
            "filename": f"{evidence_id}_{path.name}" if path.name == "report.pdf" else path.name,
            "media_type": media.get(fmt, "application/octet-stream"),
        }
    except Exception as exc:
        logger.error("Download failed\n%s", traceback.format_exc())
        return {"status": "failed", "reason": str(exc)[:800]}
