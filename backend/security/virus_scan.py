"""
Virus / malware scanning — ClamAV with graceful fallback.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from backend.security.config import CLAMAV_HOST, CLAMAV_PORT, VIRUS_SCAN_ENABLED

logger = logging.getLogger("ai_forge.security.virus")


@dataclass
class ScanResult:
    clean: bool
    threat: Optional[str] = None
    engine: str = "none"
    message: str = ""


def scan_file(path: Path) -> ScanResult:
    """Scan file for malware. Returns clean=True when scan passes or is disabled."""
    path = Path(path)
    if not path.is_file():
        return ScanResult(clean=False, message="File not found", engine="validation")

    if not VIRUS_SCAN_ENABLED:
        return ScanResult(clean=True, message="Virus scan disabled", engine="disabled")

    # Try ClamAV daemon socket
    result = _scan_clamd(path)
    if result is not None:
        return result

    # Fallback: clamscan CLI
    result = _scan_clamscan(path)
    if result is not None:
        return result

    logger.warning("No virus scanner available — allowing file (configure ClamAV for production)")
    return ScanResult(clean=True, message="Scanner unavailable", engine="fallback")


def _scan_clamd(path: Path) -> Optional[ScanResult]:
    try:
        import clamd
        cd = clamd.ClamdNetworkSocket(CLAMAV_HOST, CLAMAV_PORT)
        cd.ping()
        reply = cd.scan(str(path))
        status = reply.get(str(path))
        if status is None:
            return ScanResult(clean=True, engine="clamd")
        if status[0] == "OK":
            return ScanResult(clean=True, engine="clamd")
        return ScanResult(clean=False, threat=status[1], engine="clamd", message=status[1])
    except ImportError:
        return None
    except Exception as exc:
        logger.debug("clamd scan failed: %s", exc)
        return None


def _scan_clamscan(path: Path) -> Optional[ScanResult]:
    try:
        proc = subprocess.run(
            ["clamscan", "--no-summary", str(path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode == 0:
            return ScanResult(clean=True, engine="clamscan")
        if proc.returncode == 1:
            threat = (proc.stdout or proc.stderr or "malware detected").strip()
            return ScanResult(clean=False, threat=threat, engine="clamscan", message=threat)
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    except Exception as exc:
        logger.debug("clamscan failed: %s", exc)
        return None
