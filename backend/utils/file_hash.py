"""
Content-hash utilities for deduplication and cache lookup.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

logger = logging.getLogger("ai_forge.hash")

CHUNK_SIZE = 1024 * 1024


def compute_file_hash(file_path: Path) -> str:
    """SHA-256 hash of file contents."""
    from backend.forensics.evidence_hash import compute_evidence_hashes
    return compute_evidence_hashes(file_path)["sha256"]


def compute_dual_hash(file_path: Path) -> dict:
    """SHA-256 + SHA-512 hashes for forensic evidence fingerprinting."""
    from backend.forensics.evidence_hash import compute_evidence_hashes
    return compute_evidence_hashes(file_path)


def hash_short(file_hash: str, length: int = 16) -> str:
    return file_hash[:length]
