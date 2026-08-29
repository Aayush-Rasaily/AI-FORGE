"""
AI-Guided Forensic Localization Engine (Phase 6).

Modular segmentation providers with smart region detection, OCR diff,
signature/copy-move/video localization, and per-region explainability.
"""

from backend.analysis.localization.engine import run_phase6_localization

__all__ = ["run_phase6_localization"]
