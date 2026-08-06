"""
Report export API — PDF, DOCX, JSON with multiple templates.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.forensics.user_context import get_investigator
from backend.reports.exporter import EXPORT_DIR, FORMATS, TEMPLATES, export_report
from backend.reports.report_builder import build_report_bundle

logger = logging.getLogger("ai_forge.report_api")

router = APIRouter(prefix="/api/reports", tags=["Report Export"])


class ExportRequest(BaseModel):
    format: str = "pdf"
    template: str = "full"
    jury: Optional[Dict[str, Any]] = None


@router.get("/formats")
def list_formats():
    return {
        "formats": [
            {"id": "pdf", "label": "PDF Report", "extension": ".pdf"},
            {"id": "docx", "label": "DOCX Report", "extension": ".docx"},
            {"id": "html", "label": "HTML Report", "extension": ".html"},
            {"id": "json", "label": "JSON Report", "extension": ".json"},
        ],
        "templates": [
            {"id": "full", "label": "Full Report", "sections": ["executive", "technical", "evidence", "timeline", "charts", "heatmaps"]},
            {"id": "executive", "label": "Executive Summary", "sections": ["executive", "risk_gauge", "timeline"]},
            {"id": "technical", "label": "Technical Summary", "sections": ["technical", "signals", "charts", "heatmaps"]},
            {"id": "court", "label": "Court Report", "sections": ["executive", "evidence", "custody", "certification", "hashes"]},
            {"id": "evidence", "label": "Evidence Summary", "sections": ["evidence", "hashes", "custody", "timeline"]},
        ],
    }


@router.get("/preview/{evidence_id}/html")
async def preview_report_html(
    evidence_id: str,
    template: str = Query("full"),
):
    """Return rendered HTML report for in-browser preview."""
    try:
        result = export_report(evidence_id, format="html", template=template)
        file_path = Path(result["file_path"])
        if not file_path.exists():
            raise HTTPException(status_code=500, detail="HTML preview not found")
        return FileResponse(
            path=str(file_path),
            media_type="text/html",
            filename=result["filename"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/preview/{evidence_id}")
async def preview_report(
    evidence_id: str,
    template: str = Query("full"),
):
    """Return report bundle JSON for preview (no file generation)."""
    try:
        bundle = build_report_bundle(evidence_id, template=template)
        return {"success": True, "bundle": bundle}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/export/{evidence_id}")
async def export_report_endpoint(evidence_id: str, body: ExportRequest):
    """One-click report export — generates file and returns download URL."""
    try:
        result = export_report(
            evidence_id,
            format=body.format,
            template=body.template,
            jury_data=body.jury,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Report export failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Export failed: {exc}") from exc


@router.get("/export/{evidence_id}")
async def export_report_get(
    evidence_id: str,
    format: str = Query("pdf", description="pdf | docx | json | html"),
    template: str = Query("full", description="full | executive | technical | court | evidence"),
):
    """GET-based one-click export (direct download)."""
    if format not in FORMATS:
        raise HTTPException(status_code=400, detail=f"Format must be one of: {FORMATS}")
    if template not in TEMPLATES:
        raise HTTPException(status_code=400, detail=f"Template must be one of: {TEMPLATES}")

    try:
        result = export_report(evidence_id, format=format, template=template)
        file_path = Path(result["file_path"])
        if not file_path.exists():
            raise HTTPException(status_code=500, detail="Export file not found")

        media_types = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "json": "application/json",
            "html": "text/html",
        }
        return FileResponse(
            path=str(file_path),
            filename=result["filename"],
            media_type=media_types.get(format, "application/octet-stream"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Export failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/download/{evidence_id}/{filename}")
async def download_report(evidence_id: str, filename: str):
    """Download a previously generated report file."""
    file_path = EXPORT_DIR / evidence_id / filename
    if not file_path.exists() or ".." in filename:
        raise HTTPException(status_code=404, detail="Report file not found")

    ext = file_path.suffix.lower()
    media = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".json": "application/json",
        ".html": "text/html",
    }
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=media.get(ext, "application/octet-stream"),
    )
