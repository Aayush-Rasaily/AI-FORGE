"""Professional human-readable HTML report export."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from backend.reports.professional_report import export_professional_html


def export_html(bundle: Dict[str, Any], output_path: Path) -> str:
    """Export a printable three-page examiner-style report."""
    return export_professional_html(bundle, output_path)
