"""
Image loading and optimization utilities.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Tuple

import cv2
import numpy as np

logger = logging.getLogger("ai_forge.image")

MAX_DIMENSION = 1600
WORKING_IMAGE_NAME = "_working.jpg"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


def validate_path(file_path: Path) -> Path:
    """Resolve and validate that a file path exists and is readable."""
    resolved = file_path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"File not found: {resolved}")
    return resolved


def is_image_file(file_path: Path) -> bool:
    return file_path.suffix.lower() in IMAGE_EXTENSIONS


def is_document_file(file_path: Path) -> bool:
    return file_path.suffix.lower() in DOCUMENT_EXTENSIONS


def prepare_working_image(
    image_path: Path,
    analysis_dir: Path,
    max_dimension: int = MAX_DIMENSION,
) -> Tuple[Path, bool]:
    """
    Create a resized working copy for analysis if the image is very large.

    Returns (working_path, was_resized).
    """
    image_path = validate_path(image_path)
    analysis_dir.mkdir(parents=True, exist_ok=True)
    working_path = analysis_dir / WORKING_IMAGE_NAME

    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"OpenCV cannot read image: {image_path}")

    h, w = image.shape[:2]
    max_side = max(h, w)

    if max_side <= max_dimension:
        if working_path.exists():
            working_path.unlink(missing_ok=True)
        return image_path, False

    scale = max_dimension / max_side
    new_w = int(w * scale)
    new_h = int(h * scale)
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(working_path), resized, [cv2.IMWRITE_JPEG_QUALITY, 92])
    logger.info(
        "Resized image %dx%d -> %dx%d for analysis",
        w, h, new_w, new_h,
    )
    del image, resized
    return working_path, True


def load_image_bgr(image_path: Path) -> np.ndarray:
    """Load image once as BGR array."""
    image_path = validate_path(image_path)
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"Cannot read image: {image_path}")
    return image
