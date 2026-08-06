"""
Dual-hash evidence fingerprinting — SHA-256 + SHA-512.

Computed at intake and verified on every custody event.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict

CHUNK_SIZE = 1024 * 1024


def compute_evidence_hashes(file_path: Path) -> Dict[str, str | int]:
    """Stream file once, return SHA-256, SHA-512, and byte size."""
    path = Path(file_path)
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
