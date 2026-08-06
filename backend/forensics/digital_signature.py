"""
Cryptographic report signing — HMAC-SHA512 over canonical JSON.

Key from FORENSIC_SIGNING_KEY env or auto-generated at data/temp/.signing_key
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Tuple

logger = logging.getLogger("ai_forge.signature")

SIGNING_KEY_PATH = Path("data/temp/.forensic_signing_key")


def _get_signing_key() -> bytes:
    env_key = os.getenv("FORENSIC_SIGNING_KEY")
    if env_key:
        return env_key.encode()

    if SIGNING_KEY_PATH.exists():
        return SIGNING_KEY_PATH.read_bytes()

    SIGNING_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    key = os.urandom(64)
    SIGNING_KEY_PATH.write_bytes(key)
    logger.info("Generated forensic signing key at %s", SIGNING_KEY_PATH)
    return key


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def content_hash_sha256(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode()).hexdigest()


def content_hash_sha512(data: Any) -> str:
    return hashlib.sha512(canonical_json(data).encode()).hexdigest()


def sign_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return signature metadata for a report payload."""
    key = _get_signing_key()
    content_sha256 = content_hash_sha256(payload)
    content_sha512 = content_hash_sha512(payload)
    message = f"{content_sha256}:{content_sha512}".encode()
    signature = hmac.new(key, message, hashlib.sha512).hexdigest()

    return {
        "algorithm": "HMAC-SHA512",
        "content_sha256": content_sha256,
        "content_sha512": content_sha512,
        "signature": signature,
        "signed": True,
    }


def verify_signature(payload: Dict[str, Any], signature_meta: Dict[str, Any]) -> Tuple[bool, str]:
    """Verify report signature and content hashes."""
    expected_sha256 = content_hash_sha256(payload)
    expected_sha512 = content_hash_sha512(payload)

    if signature_meta.get("content_sha256") != expected_sha256:
        return False, "Content SHA-256 mismatch — report may have been tampered with."

    if signature_meta.get("content_sha512") != expected_sha512:
        return False, "Content SHA-512 mismatch — report may have been tampered with."

    key = _get_signing_key()
    message = f"{expected_sha256}:{expected_sha512}".encode()
    expected_sig = hmac.new(key, message, hashlib.sha512).hexdigest()

    if not hmac.compare_digest(expected_sig, signature_meta.get("signature", "")):
        return False, "Digital signature invalid."

    return True, "Report integrity verified."
