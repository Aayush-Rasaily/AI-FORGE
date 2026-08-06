"""
Unified report export orchestrator.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from backend.reports.docx_exporter import export_docx
from backend.reports.html_exporter import export_html
from backend.reports.json_exporter import export_json
from backend.reports.pdf_exporter import export_pdf
from backend.reports.report_builder import build_report_bundle

logger = logging.getLogger("ai_forge.reports.export")

EXPORT_DIR = Path("data/forensics/exports")
_file_cache: Dict[str, str] = {}

TEMPLATES = ("full", "executive", "technical", "court", "evidence")
FORMATS = ("pdf", "docx", "json", "html")


def export_report(
    evidence_id: str,
    *,
    format: str = "pdf",
    template: str = "full",
    jury_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate and export a forensic report.

    Returns dict with file_path, format, template, report_id.
    """
    fmt = format.lower()
    tpl = template.lower()

    if fmt not in FORMATS:
        raise ValueError(f"Unsupported format: {format}. Use: {', '.join(FORMATS)}")
    if tpl not in TEMPLATES:
        raise ValueError(f"Unsupported template: {template}. Use: {', '.join(TEMPLATES)}")

    cache_key = f"{evidence_id}:{fmt}:{tpl}"
    if cache_key in _file_cache:
        cached_path = Path(_file_cache[cache_key])
        if cached_path.exists():
            return {
                "success": True,
                "evidence_id": evidence_id,
                "report_id": f"RPT-{evidence_id}-cached",
                "format": fmt,
                "template": tpl,
                "file_path": str(cached_path),
                "filename": cached_path.name,
                "download_url": f"/api/reports/download/{evidence_id}/{cached_path.name}",
                "cached": True,
            }

    bundle = build_report_bundle(evidence_id, template=tpl, jury_data=jury_data)
    report_id = bundle["meta"]["report_id"]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{evidence_id}_{tpl}_{ts}.{fmt}"
    output_path = EXPORT_DIR / evidence_id / filename

    if fmt == "pdf":
        logger.info("[PDF] Creating report (template=%s) → %s", tpl, output_path)
        path = export_pdf(bundle, output_path)
        # Also place canonical report.pdf beside analysis artifacts for full template
        if tpl == "full":
            try:
                analysis_dest = Path("data/temp/uploads/analysis") / evidence_id / "report.pdf"
                analysis_dest.parent.mkdir(parents=True, exist_ok=True)
                if Path(path).resolve() != analysis_dest.resolve():
                    import shutil

                    shutil.copy2(path, analysis_dest)
                logger.info("[PDF] Saved successfully → %s", analysis_dest)
            except Exception as copy_exc:
                logger.warning("[PDF] Could not mirror to analysis dir: %s", copy_exc)
    elif fmt == "docx":
        path = export_docx(bundle, output_path)
    elif fmt == "html":
        path = export_html(bundle, output_path)
    else:
        path = export_json(bundle, output_path)

    _file_cache[cache_key] = path

    return {
        "success": True,
        "evidence_id": evidence_id,
        "report_id": report_id,
        "format": fmt,
        "template": tpl,
        "file_path": path,
        "filename": filename,
        "download_url": f"/api/reports/download/{evidence_id}/{filename}",
    }
