"""Professional human-readable PDF report export."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from backend.reports.professional_report import export_professional_pdf


def export_pdf(bundle: Dict[str, Any], output_path: Path) -> str:
    """Export a concise examiner-style investigation report."""
    return export_professional_pdf(bundle, output_path)


def ensure_report_pdf(
    evidence_id: str,
    analysis_dir: Any,
    jury_data: Optional[Dict[str, Any]] = None,
) -> Path:
    """Backward-compatible entry point used by the existing report pipeline."""
    from backend.reports.exporter import export_report

    result = export_report(
        evidence_id,
        format="pdf",
        template="full",
        jury_data=jury_data,
    )
    return Path(result.get("file_path", Path(analysis_dir) / "report.pdf"))
