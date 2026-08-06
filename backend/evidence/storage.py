"""
Preserve original evidence — never modify uploaded files.

Original  → data/evidence/original/{evidence_id}{ext}  (immutable)
Working   → data/evidence/working/{evidence_id}{ext}  (forensic modules)
Legacy    → data/temp/uploads/{evidence_id}{ext}     (backward compat)
Metadata  → analysis/{evidence_id}/metadata.json
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from backend.evidence.paths import (
    LEGACY_UPLOAD_DIR,
    ORIGINAL_DIR,
    WORKING_DIR,
    get_analysis_dir,
    get_metadata_path,
)
from backend.forensics.evidence_hash import compute_evidence_hashes

logger = logging.getLogger("ai_forge.evidence.storage")


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    if path.exists():
        path.unlink(missing_ok=True)
    tmp.replace(path)


def _set_readonly(path: Path) -> None:
    try:
        os.chmod(path, stat.S_IREAD)
    except OSError:
        pass


def archive_upload(
    evidence_id: str,
    legacy_path: Path,
    *,
    original_filename: str,
    media_type: str,
) -> Dict[str, Any]:
    """
    Copy upload into evidence vault. Hashes computed from ORIGINAL only.
    Legacy path is kept for backward compatibility.
    """
    legacy_path = Path(legacy_path)
    ext = legacy_path.suffix.lower()
    original_dest = ORIGINAL_DIR / f"{evidence_id}{ext}"
    working_dest = WORKING_DIR / f"{evidence_id}{ext}"

    if not original_dest.exists():
        shutil.copy2(legacy_path, original_dest)
        _set_readonly(original_dest)

    if not working_dest.exists() or working_dest.stat().st_size == 0:
        shutil.copy2(original_dest, working_dest)

    hashes = compute_evidence_hashes(original_dest)

    metadata = {
        "evidence_id": evidence_id,
        "original_filename": original_filename,
        "media_type": media_type,
        "archived_at": datetime.now(timezone.utc).isoformat(),
        "sha256": hashes["sha256"],
        "sha512": hashes["sha512"],
        "size_bytes": hashes["size_bytes"],
        "original_path": str(original_dest.resolve()),
        "working_path": str(working_dest.resolve()),
        "legacy_path": str(legacy_path.resolve()),
        "integrity": {
            "original_untouched": True,
            "hash_source": "original",
        },
    }
    _write_json(get_metadata_path(evidence_id), metadata)
    logger.info("Archived evidence %s — SHA256 %s…", evidence_id, hashes["sha256"][:12])
    return metadata


def load_metadata(evidence_id: str) -> Dict[str, Any]:
    path = get_metadata_path(evidence_id)
    if not path.is_file():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def verify_original_integrity(evidence_id: str) -> Dict[str, Any]:
    """Compare current original file hashes against metadata.json."""
    meta = load_metadata(evidence_id)
    original = ORIGINAL_DIR / Path(meta.get("original_path", "")).name if meta.get("original_path") else None
    if not original or not original.exists():
        from backend.evidence.paths import find_original_evidence
        original = find_original_evidence(evidence_id)

    if not original or not original.exists():
        return {"valid": False, "message": "Original evidence not found.", "sha256_match": False, "sha512_match": False}

    if not meta.get("sha256"):
        return {"valid": True, "message": "No baseline hashes — intake pending.", "sha256_match": True, "sha512_match": True}

    current = compute_evidence_hashes(original)
    sha256_ok = current["sha256"] == meta["sha256"]
    sha512_ok = current["sha512"] == meta["sha512"]
    return {
        "valid": sha256_ok and sha512_ok,
        "sha256_match": sha256_ok,
        "sha512_match": sha512_ok,
        "evidence_untouched": sha256_ok and sha512_ok,
        "message": "Integrity verified." if sha256_ok and sha512_ok else "Hash mismatch — evidence may have been modified.",
        "stored_sha256": meta["sha256"],
        "current_sha256": current["sha256"],
    }
