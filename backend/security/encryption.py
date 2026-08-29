"""
Evidence encryption at rest — Fernet (AES-128-CBC + HMAC).
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from backend.security.config import EVIDENCE_ENCRYPTION_ENABLED, EVIDENCE_ENCRYPTION_KEY

logger = logging.getLogger("ai_forge.security.encryption")

_fernet: Optional[Fernet] = None


def _derive_fernet_key(raw: str) -> bytes:
    """Derive a valid 32-byte url-safe Fernet key from arbitrary secret."""
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def get_fernet() -> Optional[Fernet]:
    global _fernet
    if not EVIDENCE_ENCRYPTION_ENABLED:
        return None
    if _fernet is not None:
        return _fernet
    key_material = EVIDENCE_ENCRYPTION_KEY
    if not key_material:
        path = os.getenv("EVIDENCE_ENCRYPTION_KEY_FILE", "data/secrets/evidence_key.txt")
        p = Path(path)
        if p.is_file():
            key_material = p.read_text(encoding="utf-8").strip()
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            key_material = Fernet.generate_key().decode("ascii")
            p.write_text(key_material, encoding="utf-8")
            logger.warning("Generated new evidence encryption key at %s", p)
    try:
        if len(key_material) == 44 and key_material.endswith("="):
            _fernet = Fernet(key_material.encode("ascii"))
        else:
            _fernet = Fernet(_derive_fernet_key(key_material))
    except Exception as exc:
        logger.error("Invalid encryption key: %s", exc)
        return None
    return _fernet


def encrypt_file(src: Path, dest: Path) -> bool:
    """Encrypt file contents to dest. Returns True if encrypted."""
    f = get_fernet()
    if f is None:
        return False
    data = Path(src).read_bytes()
    encrypted = f.encrypt(data)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(encrypted)
    return True


def decrypt_file(src: Path, dest: Path) -> bool:
    """Decrypt encrypted file to dest."""
    f = get_fernet()
    if f is None:
        import shutil
        shutil.copy2(src, dest)
        return False
    try:
        decrypted = f.decrypt(Path(src).read_bytes())
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(decrypted)
        return True
    except InvalidToken:
        # File may be plaintext (legacy)
        import shutil
        shutil.copy2(src, dest)
        return False


def encrypt_bytes(data: bytes) -> bytes:
    f = get_fernet()
    if f is None:
        return data
    return f.encrypt(data)


def decrypt_bytes(data: bytes) -> bytes:
    f = get_fernet()
    if f is None:
        return data
    try:
        return f.decrypt(data)
    except InvalidToken:
        return data
