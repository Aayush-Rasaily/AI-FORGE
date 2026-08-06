"""
Metadata analysis — delegates to metadata forensics engine.
Preserves backward-compatible API for unified_image_analysis.
"""

from backend.analysis.metadata_forensics.engine import analyze_metadata_forensics


def analyze_metadata(image_path: str):
    return analyze_metadata_forensics(image_path)
