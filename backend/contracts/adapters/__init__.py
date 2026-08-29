"""Adapters for legacy forensic output contracts."""

from .existing_outputs import (
    adapt_analysis,
    adapt_copy_move,
    adapt_detector_outputs,
    adapt_document_tampering,
    adapt_jury_or_dossier,
    adapt_localization,
    adapt_localized_detector_regions,
    adapt_metadata_structure,
    adapt_ocr_document,
    adapt_signature_analysis,
    adapt_signature_logo,
    adapt_video,
)
from .reference_comparison import adapt_reference_comparison

__all__ = [
    "adapt_analysis", "adapt_copy_move", "adapt_detector_outputs", "adapt_document_tampering", "adapt_jury_or_dossier",
    "adapt_localization", "adapt_localized_detector_regions", "adapt_metadata_structure",
    "adapt_ocr_document", "adapt_signature_analysis", "adapt_signature_logo", "adapt_video",
    "adapt_reference_comparison",
]
