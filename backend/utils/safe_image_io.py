"""
Safe image I/O — tempfile copies, atomic writes, resource release.
Prevents WinError 32 from locked originals on Windows.
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

import cv2
import numpy as np

logger = logging.getLogger("ai_forge.safe_io")


@contextmanager
def safe_image_copy(source: Path | str, suffix: Optional[str] = None) -> Generator[Path, None, None]:
    """Copy source image to a unique temp file; never read the original directly."""
    source = Path(source)
    if not source.exists():
        raise FileNotFoundError(f"Image not found: {source}")

    ext = suffix or source.suffix or ".jpg"
    fd, tmp_path = tempfile.mkstemp(suffix=ext, prefix="aiforge_")
    os.close(fd)
    tmp = Path(tmp_path)
    try:
        shutil.copy2(source, tmp)
        yield tmp
    finally:
        _safe_unlink(tmp)


def _safe_unlink(path: Path, retries: int = 5) -> None:
    for attempt in range(retries):
        try:
            path.unlink(missing_ok=True)
            return
        except (PermissionError, OSError) as exc:
            if attempt == retries - 1:
                logger.debug("Could not unlink %s: %s", path, exc)
            time.sleep(0.05 * (attempt + 1))


def read_image_bgr(source: Path | str) -> np.ndarray:
    """Read image via temp copy — releases file locks on original."""
    with safe_image_copy(source) as tmp:
        image = cv2.imread(str(tmp))
    if image is None:
        raise ValueError(f"Unable to read image: {source}")
    return image


def atomic_cv2_write(path: Path | str, image: np.ndarray, max_retries: int = 6) -> bool:
    """Write image atomically via temp file + replace to avoid lock conflicts."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(suffix=path.suffix or ".png", dir=path.parent)
    os.close(fd)
    tmp = Path(tmp_path)
    try:
        for attempt in range(max_retries):
            try:
                if not cv2.imwrite(str(tmp), image):
                    return False
                if path.exists():
                    path.unlink(missing_ok=True)
                tmp.replace(path)
                return True
            except (PermissionError, OSError) as exc:
                logger.debug("Write retry %d for %s: %s", attempt + 1, path, exc)
                time.sleep(0.08 * (attempt + 1))
        return False
    finally:
        _safe_unlink(tmp)
