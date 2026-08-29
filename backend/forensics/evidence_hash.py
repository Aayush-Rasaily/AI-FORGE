"""
Dual-hash evidence fingerprinting — SHA-256 + SHA-512.

Computed at intake and verified on every custody event.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict

CHUNK_SIZE = 1024 * 1024


from functools import lru_cache

@lru_cache(maxsize=256)
def _cached_evidence_hashes(resolved_path: str, mtime_ns: int, size_bytes: int) -> Dict[str, str | int]:
    path = Path(resolved_path)
    sha256 = hashlib.sha256()
    sha512 = hashlib.sha512()
    size = 0

    with open(path, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            size += len(chunk)
            sha256.update(chunk)
            sha512.update(chunk)

    return {
        "sha256": sha256.hexdigest(),
        "sha512": sha512.hexdigest(),
        "size_bytes": size,
        "algorithm": "SHA-256+SHA-512",
    }


def compute_evidence_hashes(file_path: Path) -> Dict[str, str | int]:
    """Stream file once, return SHA-256, SHA-512, and byte size (cached by mtime+size)."""
    path = Path(file_path).resolve()
    try:
        stat = path.stat()
        return _cached_evidence_hashes(str(path), stat.st_mtime_ns, stat.st_size)
    except Exception:
        # Fallback for dynamic/virtual files
        sha256 = hashlib.sha256()
        sha512 = hashlib.sha512()
        size = 0
        with open(path, "rb") as f:
            while chunk := f.read(CHUNK_SIZE):
                size += len(chunk)
                sha256.update(chunk)
                sha512.update(chunk)
        return {
            "sha256": sha256.hexdigest(),
            "sha512": sha512.hexdigest(),
            "size_bytes": size,
            "algorithm": "SHA-256+SHA-512",
        }
