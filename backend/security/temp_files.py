"""
Secure temporary file handling and automatic cleanup.
"""

from __future__ import annotations

import logging
import os
import secrets
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Iterable

from backend.security.config import TEMP_MAX_AGE_HOURS

logger = logging.getLogger("ai_forge.security.temp")

SECURE_TEMP_ROOT = Path(os.getenv("SECURE_TEMP_DIR", "data/temp/secure"))
QUARANTINE_DIR = Path("data/evidence/quarantine")


def ensure_secure_dirs() -> None:
    SECURE_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(SECURE_TEMP_ROOT, 0o700)
    except OSError:
        pass


@contextmanager
def secure_temp_file(suffix: str = "", prefix: str = "aif_") -> Generator[Path, None, None]:
    """Create a secure temp file under SECURE_TEMP_ROOT; delete on exit."""
    ensure_secure_dirs()
    fd, path = tempfile.mkstemp(
        suffix=suffix,
        prefix=prefix,
        dir=str(SECURE_TEMP_ROOT),
    )
    os.close(fd)
    p = Path(path)
    try:
        os.chmod(p, 0o600)
        yield p
    finally:
        try:
            p.unlink(missing_ok=True)
        except OSError:
            pass


def quarantine_file(src: Path, evidence_id: str, reason: str) -> Path:
    """Move infected file to quarantine."""
    ensure_secure_dirs()
    dest = QUARANTINE_DIR / f"{evidence_id}_{secrets.token_hex(4)}{Path(src).suffix}"
    import shutil
    shutil.move(str(src), str(dest))
    meta = dest.with_suffix(dest.suffix + ".reason.txt")
    meta.write_text(reason, encoding="utf-8")
    logger.warning("Quarantined %s → %s (%s)", src, dest, reason)
    return dest


def cleanup_old_files(
    directories: Iterable[Path],
    *,
    max_age_hours: int = TEMP_MAX_AGE_HOURS,
) -> int:
    """Remove files older than max_age_hours. Returns count removed."""
    cutoff = time.time() - (max_age_hours * 3600)
    removed = 0
    for directory in directories:
        directory = Path(directory)
        if not directory.is_dir():
            continue
        for item in directory.rglob("*"):
            if not item.is_file():
                continue
            try:
                if item.stat().st_mtime < cutoff:
                    item.unlink(missing_ok=True)
                    removed += 1
            except OSError:
                pass
    if removed:
        logger.info("Temp cleanup removed %d files (>%dh old)", removed, max_age_hours)
    return removed


def run_scheduled_cleanup() -> int:
    """Clean secure temp, legacy uploads temp, and export cache."""
    from backend.evidence.paths import LEGACY_UPLOAD_DIR
    from backend.reports.exporter import EXPORT_DIR

    return cleanup_old_files([
        SECURE_TEMP_ROOT,
        Path("data/temp/uploads"),
        LEGACY_UPLOAD_DIR,
        EXPORT_DIR,
        Path("data/temp/report_images"),
    ])
