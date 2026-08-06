"""
Pipeline API routes — report, dashboard, artifacts, timeline.

Additive endpoints (do not replace /api/evidence/* or /api/reports/*).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse, JSONResponse

from backend.evidence.paths import get_analysis_dir
from backend.pipeline.dashboard_builder import build_dashboard
from backend.pipeline.report_manager import analysis_exists, get_status
from backend.reports.report_builder import build_report_bundle
from backend.services.report_service import (
    _download_urls,
    _existing_files,
    get_report_payload,
    report_ready,
    start_report_generation,
    stream_download,
)
from backend.utils.analysis_persistence import load_analysis_bundle

logger = logging.getLogger("ai_forge.pipeline.api")

router = APIRouter(prefix="/api", tags=["Pipeline"])

_MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".json": "application/json",
    ".html": "text/html",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _ok(payload: dict, status_code: int = 200):
    return JSONResponse(content=payload, status_code=status_code)


@router.get("/report/{evidence_id}/status")
async def get_report_status_endpoint(evidence_id: str):
    """
    Lightweight status. If report already ready → status=ready immediately.
    Does not regenerate on every poll.
    """
    try:
        if not analysis_exists(evidence_id):
            return _ok({
                "success": True,
                "evidence_id": evidence_id,
                "status": "pending",
                "progress": 0,
                "report_ready": False,
                "ready": False,
                "message": "Analysis not started.",
                "download_urls": _download_urls(evidence_id),
            })

        analysis_dir = get_analysis_dir(evidence_id, create=False)
        if report_ready(analysis_dir):
            return _ok({
                "success": True,
                "evidence_id": evidence_id,
                "status": "ready",
                "progress": 100,
                "report_ready": True,
                "ready": True,
                "download_urls": _download_urls(evidence_id),
                "files": _existing_files(analysis_dir),
                "message": "Report ready.",
            })

        status = get_status(evidence_id)
        raw = str(status.get("status", "generating")).lower()
        if raw in ("completed", "ready"):
            mapped = "ready"
        elif raw == "failed":
            mapped = "failed"
        else:
            mapped = "generating"

        return _ok({
            "success": True,
            "evidence_id": evidence_id,
            "status": mapped,
            "progress": status.get("progress", 0),
            "report_ready": False,
            "ready": False,
            "download_urls": _download_urls(evidence_id),
            "files": status.get("files", {}),
            "message": status.get("message")
            or "Generating professional forensic report...",
            "estimated_seconds": 3,
        })
    except Exception as exc:
        logger.exception("status endpoint failed: %s", exc)
        return _ok({
            "success": False,
            "evidence_id": evidence_id,
            "status": "failed",
            "reason": str(exc)[:500],
            "report_ready": False,
            "ready": False,
        })


@router.post("/report/{evidence_id}/generate")
async def trigger_report_generation(evidence_id: str):
    """Start report generation from cached analysis. Returns generating | ready | failed."""
    try:
        result = start_report_generation(evidence_id)
        code = 200
        if result.get("status") == "failed" and "not found" in str(result.get("reason", "")).lower():
            code = 404
        return _ok(result, code)
    except Exception as exc:
        logger.exception("generate endpoint failed: %s", exc)
        return _ok({
            "success": False,
            "evidence_id": evidence_id,
            "status": "failed",
            "reason": str(exc)[:800],
        })


@router.get("/report/{evidence_id}")
async def get_report(evidence_id: str):
    """
    Return report metadata. Generates from cached analysis when PDF missing.
    {
      status: "ready",
      download_urls: { pdf, court, executive, json, html, docx }
    }
    """
    try:
        payload = get_report_payload(evidence_id)
        try:
            analysis_dir = get_analysis_dir(evidence_id, create=False)
            bundle = load_analysis_bundle(analysis_dir)
            if bundle:
                payload["risk"] = bundle.get("risk", {})
                payload["jury"] = bundle.get("jury", {})
            dash = _load_dashboard(analysis_dir)
            if dash:
                payload["dashboard"] = dash
        except Exception:
            pass
        return _ok(payload)
    except Exception as exc:
        logger.exception("get report failed: %s", exc)
        return _ok({
            "success": False,
            "evidence_id": evidence_id,
            "status": "failed",
            "reason": str(exc)[:800],
        })


@router.get("/report/{evidence_id}/download")
async def download_report(
    evidence_id: str,
    format: Optional[str] = Query(None, description="Report format: pdf, docx, html, json"),
    file: Optional[str] = Query(None, description="Legacy: canonical report filename"),
    template: Optional[str] = Query(None, description="PDF template: executive, court, technical, full"),
):
    """Stream report file. Auto-generates from cached analysis when missing."""
    fmt = (format or "pdf").lower()
    tpl = (template or "full").lower()

    if file:
        if ".." in file or "/" in file or "\\" in file:
            return _ok({"status": "failed", "reason": "Invalid filename"}, 400)
        analysis_dir = get_analysis_dir(evidence_id, create=False)
        path = analysis_dir / file
        if path.is_file():
            return FileResponse(
                path=str(path),
                filename=path.name,
                media_type=_MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream"),
            )
        return _ok({"status": "failed", "reason": "File not found"}, 404)

    result = stream_download(evidence_id, fmt=fmt, template=tpl)
    if result.get("status") == "failed":
        return _ok(result, 503)

    return FileResponse(
        path=result["path"],
        filename=result["filename"],
        media_type=result["media_type"],
    )


@router.get("/dashboard/{evidence_id}")
async def get_dashboard(evidence_id: str):
    """Return dashboard.json for frontend."""
    analysis_dir = get_analysis_dir(evidence_id, create=False)
    dashboard = _load_dashboard(analysis_dir)
    if not dashboard:
        bundle = load_analysis_bundle(analysis_dir)
        if not bundle:
            return _ok({"success": False, "status": "failed", "reason": "Dashboard not found."}, 404)
        dashboard = build_dashboard(
            evidence_id,
            bundle["analysis"],
            bundle.get("tampering", {}),
            jury=bundle.get("jury"),
            timing=bundle.get("timing"),
        )
    return _ok({"success": True, "evidence_id": evidence_id, "dashboard": dashboard})


@router.get("/artifacts/{evidence_id}")
async def list_artifacts(evidence_id: str):
    """Return artifact URLs and on-disk status."""
    from backend.utils.artifact_paths import artifact_api_urls, ARTIFACT_FILES

    analysis_dir = get_analysis_dir(evidence_id, create=False)
    urls = artifact_api_urls(evidence_id)
    files = {}
    for key, fname in ARTIFACT_FILES.items():
        p = analysis_dir / fname
        files[key] = {
            "url": urls.get(key),
            "exists": p.is_file() and p.stat().st_size > 0,
            "path": str(p),
        }
    return {"success": True, "evidence_id": evidence_id, "artifacts": files, "urls": urls}


@router.get("/timeline/{evidence_id}")
async def get_timeline(evidence_id: str):
    """Return investigation timeline for evidence."""
    analysis_dir = get_analysis_dir(evidence_id, create=False)
    bundle = load_analysis_bundle(analysis_dir)
    if not bundle:
        return _ok({"success": False, "status": "failed", "reason": "Analysis not found."}, 404)

    analysis = bundle["analysis"]
    timing = bundle.get("timing", analysis.get("timing", {}))

    module_timeline = []
    for module, duration in sorted(timing.items(), key=lambda x: x[0]):
        if isinstance(duration, (int, float)):
            module_timeline.append({
                "type": "module",
                "module": module,
                "duration_ms": round(duration * 1000 if duration < 100 else duration, 2),
            })

    try:
        report_bundle = build_report_bundle(evidence_id, template="full")
        custody_timeline = report_bundle.get("timeline", [])
    except Exception:
        custody_timeline = []

    dashboard_path = analysis_dir / "dashboard.json"
    dashboard_timeline = []
    if dashboard_path.exists():
        with open(dashboard_path, encoding="utf-8") as f:
            dash = json.load(f)
            dashboard_timeline = dash.get("timeline", [])

    return {
        "success": True,
        "evidence_id": evidence_id,
        "timeline": {
            "modules": module_timeline or dashboard_timeline,
            "custody": custody_timeline,
        },
    }


def _load_dashboard(analysis_dir: Path) -> dict:
    path = analysis_dir / "dashboard.json"
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
