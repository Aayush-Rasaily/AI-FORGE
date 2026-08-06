"""Delegates to unified OCR service with caching and engine fallback."""

from typing import Dict, Optional

from backend.services.ocr_service import extract_text as _extract_text


def extract_text(image_path: str, analysis_dir: Optional[str] = None) -> Dict:
    result = _extract_text(image_path, analysis_dir=analysis_dir)
    # Backward-compatible keys
    if "text" not in result and "full_text" in result:
        result["text"] = result["full_text"]
    return result
