"""
Generate all canonical reports after analysis completes.
"""

from __future__ import annotations

import json
import logging
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.reports.exporter import export_report
from backend.pipeline.module_logger import log_module

logger = logging.getLogger("ai_forge.pipeline.reports")

# Canonical filenames inside analysis/{evidence_id}/
CANONICAL_REPORTS = {
    "report.pdf": ("pdf", "full"),
    "report_executive.pdf": ("pdf", "executive"),
    "executive.pdf": ("pdf", "executive"),
    "report_court.pdf": ("pdf", "court"),
    "court.pdf": ("pdf", "court"),
    "report_technical.pdf": ("pdf", "technical"),
    "technical.pdf": ("pdf", "technical"),
    "report.json": ("json", "full"),
    "report.html": ("html", "full"),
    "report.docx": ("docx", "full"),
}

REPORT_STATUS_FILE = "report_status.json"


def get_report_status(analysis_dir: Path) -> Dict[str, Any]:
    """Read report generation status from disk."""
    analysis_dir = Path(analysis_dir)
    status_path = analysis_dir / "status.json"
    if status_path.exists():
        try:
            with open(status_path, encoding="utf-8") as f:
                data = json.load(f)
            data["ready"] = data.get("report_ready", (analysis_dir / "report.pdf").is_file())
            return data
        except (json.JSONDecodeError, OSError):
            pass

    legacy_path = analysis_dir / REPORT_STATUS_FILE
    if legacy_path.exists():
        try:
            with open(legacy_path, encoding="utf-8") as f:
                data = json.load(f)
            data["ready"] = (analysis_dir / "report.pdf").is_file()
            return data
        except (json.JSONDecodeError, OSError):
            pass

    files = {name: str(analysis_dir / name) for name in CANONICAL_REPORTS if (analysis_dir / name).exists()}
    ready = (analysis_dir / "report.pdf").is_file()
    return {
        "status": "ready" if ready else "pending",
        "ready": ready,
        "files": files,
    }


def generate_all_reports(
    evidence_id: str,
    analysis_dir: Path,
    jury_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generate all report formats in parallel; failures are isolated per file."""
    analysis_dir = Path(analysis_dir)
    analysis_dir.mkdir(parents=True, exist_ok=True)
    reports_meta: Dict[str, Any] = {"files": {}, "download_urls": {}, "errors": {}}

    # Deduplicate by (fmt, template) — copy aliases after primary write
    unique_tasks: Dict[tuple, str] = {}
    for name, (fmt, tpl) in CANONICAL_REPORTS.items():
        key = (fmt, tpl)
        if key not in unique_tasks:
            unique_tasks[key] = name

    def _gen(canonical_name: str, fmt: str, template: str) -> tuple:
        start = __import__("time").perf_counter()
        # Full PDF writes directly into analysis_dir for reliability
        if fmt == "pdf" and template == "full" and canonical_name == "report.pdf":
            from backend.reports.pdf_exporter import ensure_report_pdf

            dest = ensure_report_pdf(evidence_id, analysis_dir, jury_data=jury_data)
            elapsed = (__import__("time").perf_counter() - start) * 1000
            log_module(evidence_id, f"report_{template}_{fmt}", "completed", duration_ms=elapsed)
            return canonical_name, str(dest)

        result = export_report(evidence_id, format=fmt, template=template, jury_data=jury_data)
        src = Path(result["file_path"])
        dest = analysis_dir / canonical_name
        if src.exists() and src.resolve() != dest.resolve():
            shutil.copy2(src, dest)
        elif src.exists() and not dest.exists():
            shutil.copy2(src, dest)
        elapsed = (__import__("time").perf_counter() - start) * 1000
        log_module(evidence_id, f"report_{template}_{fmt}", "completed", duration_ms=elapsed)
        return canonical_name, str(dest)

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {
            pool.submit(_gen, name, fmt, tpl): (name, fmt, tpl)
            for (fmt, tpl), name in unique_tasks.items()
        }
        generated: Dict[tuple, str] = {}
        for future in as_completed(futures):
            name, fmt, tpl = futures[future]
            try:
                canonical, path = future.result()
                generated[(fmt, tpl)] = path
                reports_meta["files"][canonical] = path
            except Exception as exc:
                logger.error("[%s] Report %s failed: %s", evidence_id, name, exc)
                reports_meta["errors"][name] = str(exc)

    # Copy aliases (executive.pdf, court.pdf, technical.pdf)
    aliases = {
        "executive.pdf": "report_executive.pdf",
        "court.pdf": "report_court.pdf",
        "technical.pdf": "report_technical.pdf",
    }
    for alias, source in aliases.items():
        src = analysis_dir / source
        dest = analysis_dir / alias
        if src.exists() and not dest.exists():
            try:
                shutil.copy2(src, dest)
                reports_meta["files"][alias] = str(dest)
            except OSError:
                pass

    primary = analysis_dir / "report.pdf"
    reports_meta["primary"] = str(primary) if primary.exists() else None
    reports_meta["download_url"] = f"/api/report/{evidence_id}/download"
    reports_meta["ready"] = primary.exists()
    return reports_meta
