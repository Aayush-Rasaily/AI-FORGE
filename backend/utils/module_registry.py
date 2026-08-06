"""
File-type aware module selection — skip incompatible forensic modules.
"""

from __future__ import annotations

from pathlib import Path
from typing import Set

import cv2
import numpy as np

from backend.utils.image_utils import (
    DOCUMENT_EXTENSIONS,
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
)


def get_file_category(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in DOCUMENT_EXTENSIONS:
        return "document"
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    return "unknown"


# Core forensic modules — always run for images
IMAGE_CORE_MODULES = {
    "forensics", "copy_move", "metadata", "noise", "tampering",
    "rgb", "hsv", "lab", "ycbcr", "frequency", "jpeg_block",
    "gan_detection", "face_forensics",
}

# OCR/layout modules — only when text is likely present
IMAGE_OCR_MODULES = {"font", "spacing", "region"}


def classify_image_profile(image_path: str) -> str:
    """
    Classify image evidence profile for smart module selection.

    Returns: natural_photo | scanned_document | text_document | mixed
    """
    if likely_contains_text(image_path):
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is not None:
            h, w = img.shape
            aspect = w / h if h else 1.0
            if 0.55 < aspect < 0.85:
                return "scanned_document"
            return "text_document"
    return "natural_photo"


def modules_for_image(path: Path, ocr_applicable: bool, profile: str | None = None) -> Set[str]:
    profile = profile or classify_image_profile(str(path))
    modules = set(IMAGE_CORE_MODULES)

    if profile == "natural_photo":
        return modules  # Skip OCR/layout modules

    if profile in ("scanned_document", "text_document", "mixed") and ocr_applicable:
        modules.update(IMAGE_OCR_MODULES)

    return modules


def modules_for_document(path: Path) -> Set[str]:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return {"docx_text", "layout", "risk"}
    return {"pdf_convert", "ocr", "layout", "risk", "heatmap"}


def modules_for_video() -> Set[str]:
    return {"metadata", "keyframes", "frame_signals", "keyframe_forensics"}


def likely_contains_text(image_path: str) -> bool:
    """
    Fast heuristic — avoids expensive OCR on photos with no text.
    """
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return False

    h, w = img.shape
    if max(h, w) < 150:
        return False

    aspect = w / h if h else 1
    # Portrait document-like
    if 0.55 < aspect < 0.85 and h > w * 1.1:
        return True

    # Text band edge density
    band = img[int(h * 0.15): int(h * 0.85), int(w * 0.08): int(w * 0.92)]
    if band.size == 0:
        return False
    edges = cv2.Canny(band, 50, 150)
    density = float(np.count_nonzero(edges)) / edges.size
    return density > 0.018
