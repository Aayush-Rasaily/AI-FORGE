"""Professional human-readable DOCX report export."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from backend.reports.professional_report import export_professional_docx


def export_docx(bundle: Dict[str, Any], output_path: Path) -> str:
    """Export the same concise examiner narrative used by the PDF report."""
    return export_professional_docx(bundle, output_path)
