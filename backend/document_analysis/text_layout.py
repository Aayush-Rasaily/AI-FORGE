"""
Backward-compatibility shim.

Some older imports reference ``backend.document_analysis.text_layout``.
The canonical implementation lives in ``text_layout_analysis``.
"""

from backend.document_analysis.text_layout_analysis import (
    analyze_text_layout,
    reader,
    get_center,
)

__all__ = [
    "analyze_text_layout",
    "reader",
    "get_center",
]
