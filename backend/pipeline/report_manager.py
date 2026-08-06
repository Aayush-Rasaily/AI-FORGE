"""
Report Manager — status tracking, auto-generation, download resolution.

Status values (canonical): queued | processing | completed | failed
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from backend.evidence.paths import get_analysis_dir
from backend.pipeline.report_pipeline import generate_all_reports
from backend.pipeline.module_logger import log_module

logger = logging.getLogger("ai_forge.report_manager")

STATUS_FILE = "status.json"
CANONICAL_STATUSES = {"queued", "processing", "completed", "failed"}

FORMAT_MAP = {
    "pdf": "report.pdf",
    "docx": "report.docx",
    "html": "report.html",
    "json": "report.json",
    "executive": "report_executive.pdf",
    "court": "report_court.pdf",
    "technical": "report_technical.pdf",
}


def _normalize_status(raw: str) -> str:
    s = str(raw or "queued").lower()
    mapping = {
        "pending": "queued",
        "generating": "processing",
        "ready": "completed",
        "partial": "completed",
    }
    s = mapping.get(s, s)
    return s if s in CANONICAL_STATUSES else "queued"


def _status_path(analysis_dir: Path) -> Path:
    return analysis_dir / STATUS_FILE


def write_status(analysis_dir: Path, **fields) -> Dict[str, Any]:
    analysis_dir = Path(analysis_dir)
    path = _status_path(analysis_dir)
    current = read_status(analysis_dir)
    current.update(fields)
    if "status" in current:
        current["status"] = _normalize_status(current["status"])
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2)
    if path.exists():
        path.unlink(missing_ok=True)
    tmp.replace(path)
    return current


def read_status(analysis_dir: Path) -> Dict[str, Any]:
    analysis_dir = Path(analysis_dir)
    path = _status_path(analysis_dir)
    if path.is_file():
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            data["status"] = _normalize_status(data.get("status", "queued"))
            return data
        except (json.JSONDecodeError, OSError):
            pass

    ready = (analysis_dir / "report.pdf").is_file()
    return {
        "status": "completed" if ready else "queued",
        "progress": 100 if ready else 0,
        "report_ready": ready,
        "files": _list_report_files(analysis_dir),
    }


def _list_report_files(analysis_dir: Path) -> Dict[str, str]:
    files = {}
    for fmt, name in FORMAT_MAP.items():
        p = analysis_dir / name
        if p.is_file():
            files[name] = str(p)
    return files


def analysis_exists(evidence_id: str) -> bool:
    adir = get_analysis_dir(evidence_id, create=False)
    return (
        (adir / "analysis.json").is_file()
        or (adir / "dashboard.json").is_file()
        or (adir / "document_analysis.json").is_file()
        or (adir / "video_analysis.json").is_file()
        or (adir / "signature_analysis.json").is_file()
        or (adir / "jury.json").is_file()
    )


def persist_analysis_payload(
    evidence_id: str,
    payload: Dict[str, Any],
    *,
    kind: str = "analysis",
) -> Path:
    """Write analysis payload so report generation can run for any modality."""
    adir = get_analysis_dir(evidence_id, create=True)
    filename = {
        "analysis": "analysis.json",
        "document": "document_analysis.json",
        "video": "video_analysis.json",
        "signature": "signature_analysis.json",
        "jury": "jury.json",
        "deepfake": "deepfake.json",
        "dashboard": "dashboard.json",
    }.get(kind, f"{kind}.json")

    path = adir / filename
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    if path.exists():
        path.unlink(missing_ok=True)
    tmp.replace(path)

    # Also ensure analysis.json exists for report builder
    if kind != "analysis" and not (adir / "analysis.json").is_file():
        stub = {
            "evidence_id": evidence_id,
            "media_type": kind,
            "verdict": payload.get("verdict") or payload.get("summary", {}).get("verdict"),
            "risk_score": payload.get("risk_score") or payload.get("summary", {}).get("risk_score", 0),
            "confidence": payload.get("confidence", 0),
            kind: payload,
        }
        stub_path = adir / "analysis.json"
        stub_tmp = stub_path.with_suffix(".tmp")
        with open(stub_tmp, "w", encoding="utf-8") as f:
            json.dump(stub, f, indent=2, default=str)
        if stub_path.exists():
            stub_path.unlink(missing_ok=True)
        stub_tmp.replace(stub_path)

    write_status(adir, status="queued", progress=0, report_ready=False)
    return adir


def get_status(evidence_id: str) -> Dict[str, Any]:
    """Never raises 404 — returns queued if analysis not started."""
    adir = get_analysis_dir(evidence_id, create=False)
    if not analysis_exists(evidence_id):
        return {
            "success": True,
            "evidence_id": evidence_id,
            "status": "queued",
            "progress": 0,
            "report_ready": False,
            "ready": False,
            "analysis_ready": False,
            "message": "Analysis not started — report queued when analysis completes.",
        }

    status = read_status(adir)
    status["status"] = _normalize_status(status.get("status", "queued"))
    ready = status.get("report_ready") or (adir / "report.pdf").is_file() or status["status"] == "completed"
    if ready:
        status["status"] = "completed"
        status["progress"] = 100
        status["report_ready"] = True
    status.update({
        "success": True,
        "evidence_id": evidence_id,
        "analysis_ready": True,
        "ready": ready,
        "report_ready": ready,
        "files": _list_report_files(adir),
        "download_url": f"/api/report/{evidence_id}/download?format=pdf",
    })
    status.setdefault("progress", 100 if ready else status.get("progress", 0))
    return status


def resolve_download_path(evidence_id: str, fmt: str = "pdf") -> Path:
    adir = get_analysis_dir(evidence_id, create=False)
    filename = FORMAT_MAP.get(fmt.lower(), f"report.{fmt}")
    path = adir / filename
    if path.is_file() and path.stat().st_size > 100:
        return path
    # Never substitute executive.pdf for the full report.pdf
    aliases = {
        "pdf": ["report.pdf"],
        "docx": ["report.docx"],
        "html": ["report.html"],
        "json": ["report.json"],
    }
    for name in aliases.get(fmt.lower(), [filename]):
        p = adir / name
        if p.is_file() and p.stat().st_size > 100:
            return p
    return path


def generate_reports(
    evidence_id: str,
    *,
    jury_data: Optional[Dict[str, Any]] = None,
    background: bool = True,
) -> Dict[str, Any]:
    """Generate all report formats. Optionally run in background thread."""
    if not analysis_exists(evidence_id):
        logger.info("report_generate_skipped | evidence_id=%s | reason=no_analysis", evidence_id)
        return {"success": False, "status": "queued", "error": "Analysis not found.", "evidence_id": evidence_id}

    adir = get_analysis_dir(evidence_id, create=True)
    logger.info("report_generate_start | evidence_id=%s | background=%s", evidence_id, background)

    if background:
        from backend.utils.worker_pool import get_worker_pool

        write_status(adir, status="queued", progress=5, report_ready=False)

        def _run():
            write_status(adir, status="processing", progress=15, report_ready=False)
            _generate_sync(evidence_id, adir, jury_data)

        get_worker_pool().submit(_run)
        return {"success": True, "status": "queued", "evidence_id": evidence_id}

    return _generate_sync(evidence_id, adir, jury_data)


def _generate_sync(evidence_id: str, adir: Path, jury_data: Optional[Dict]) -> Dict[str, Any]:
    write_status(adir, status="processing", progress=25, report_ready=False)
    try:
        meta = generate_all_reports(evidence_id, adir, jury_data=jury_data)
        errors = meta.get("errors", {})
        ready = (adir / "report.pdf").is_file()
        status = "completed" if ready else "failed"
        write_status(
            adir,
            status=status,
            progress=100 if ready else 50,
            report_ready=ready,
            files=_list_report_files(adir),
            errors=errors,
        )
        legacy = {
            "status": "ready" if ready else status,
            "ready": ready,
            "files": meta.get("files", {}),
            "errors": errors,
        }
        legacy_path = adir / "report_status.json"
        tmp = legacy_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(legacy, f, indent=2)
        if legacy_path.exists():
            legacy_path.unlink(missing_ok=True)
        tmp.replace(legacy_path)
        log_module(evidence_id, "report_manager", "completed" if ready else "failed")
        logger.info(
            "report_generate_end | evidence_id=%s | status=%s | files=%s",
            evidence_id,
            status,
            list(_list_report_files(adir).keys()),
        )
        return {"success": ready, "status": status, "files": _list_report_files(adir), "errors": errors}
    except Exception as exc:
        logger.exception("report_generate_error | evidence_id=%s | error=%s", evidence_id, exc)
        write_status(adir, status="failed", progress=0, report_ready=False, error=str(exc))
        log_module(evidence_id, "report_manager", "failed", error=str(exc))
        try:
            meta = generate_all_reports(evidence_id, adir, jury_data=jury_data)
            ready = (adir / "report.pdf").is_file()
            write_status(
                adir,
                status="completed" if ready else "failed",
                progress=100 if ready else 0,
                report_ready=ready,
            )
            return {"success": ready, "retried": True, "status": "completed" if ready else "failed"}
        except Exception as exc2:
            write_status(adir, status="failed", report_ready=False, error=str(exc2))
            return {"success": False, "status": "failed", "error": str(exc2)}
