"""
Report integrity — digital signing, verification hash, QR code generation.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from backend.forensics.digital_signature import content_hash_sha256, sign_payload

logger = logging.getLogger("ai_forge.reports.integrity")

REGISTRY_FILE = Path("data/forensics/exports/verification_registry.jsonl")
QR_DIR = Path("data/forensics/exports/qr")


def _signable_payload(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Canonical subset signed for verification (exclude binary paths)."""
    return {
        "meta": bundle.get("meta"),
        "executive_summary": bundle.get("executive_summary"),
        "evidence_summary": bundle.get("evidence_summary"),
        "technical_findings": (bundle.get("legal") or {}).get("technical_findings"),
        "detector_votes": (bundle.get("legal") or {}).get("detector_votes"),
        "recommendations": (bundle.get("legal") or {}).get("recommendations"),
        "custody_chain": bundle.get("custody_chain"),
        "verdict": (bundle.get("executive_summary") or {}).get("verdict"),
    }


def _verification_url(verification_id: str, base_url: Optional[str] = None) -> str:
    base = (base_url or os.getenv("AI_FORGE_PUBLIC_URL") or "http://localhost:8000").rstrip("/")
    return f"{base}/api/reports/verify/{verification_id}"


def generate_qr_image(data: str, output_path: Path) -> Optional[str]:
    """Generate QR PNG; returns path or None if library unavailable."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import qrcode

        qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=6, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(output_path)
        return str(output_path)
    except ImportError:
        logger.warning("qrcode not installed — QR verification image skipped")
        return None
    except Exception as exc:
        logger.warning("QR generation failed: %s", exc)
        return None


def attach_legal_integrity(bundle: Dict[str, Any], *, base_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Sign report bundle and attach verification metadata + QR artifact path.
    """
    signable = _signable_payload(bundle)
    signature_meta = sign_payload(signable)
    verification_id = signature_meta["content_sha256"][:16]
    verify_url = _verification_url(verification_id, base_url)

    evidence_id = (bundle.get("meta") or {}).get("evidence_id", "unknown")
    template = (bundle.get("meta") or {}).get("template", "full")
    qr_path = QR_DIR / evidence_id / f"{verification_id}.png"
    qr_file = generate_qr_image(verify_url, qr_path)

    integrity = {
        **signature_meta,
        "verification_id": verification_id,
        "verification_url": verify_url,
        "verification_hash": signature_meta["content_sha256"],
        "signed_at": datetime.now(timezone.utc).isoformat(),
        "qr_image_path": qr_file,
        "algorithm": signature_meta.get("algorithm", "HMAC-SHA512"),
    }
    bundle["legal_integrity"] = integrity

    _append_registry({
        "verification_id": verification_id,
        "report_id": (bundle.get("meta") or {}).get("report_id"),
        "evidence_id": evidence_id,
        "template": template,
        "content_sha256": signature_meta["content_sha256"],
        "content_sha512": signature_meta.get("content_sha512"),
        "signature": signature_meta["signature"],
        "signed_at": integrity["signed_at"],
        "signable": signable,
    })
    return integrity


def _append_registry(record: Dict[str, Any]) -> None:
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")


def latest_verification_for(evidence_id: str, template: str = "full") -> Dict[str, Any]:
    """Return most recent verification record for evidence + template."""
    if not REGISTRY_FILE.is_file():
        return {}
    match = None
    for line in REGISTRY_FILE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("evidence_id") == evidence_id and rec.get("template") == template:
            match = rec
    if not match:
        return {}
    vid = match.get("verification_id") or str(match.get("content_sha256", ""))[:16]
    return {
        "verification_id": vid,
        "verification_hash": match.get("content_sha256"),
        "verification_url": _verification_url(vid),
    }


def verify_exported_report(verification_id: str) -> Dict[str, Any]:
    """Verify a report by verification_id (first 16 chars of content SHA-256)."""
    if not REGISTRY_FILE.is_file():
        return {"valid": False, "message": "Verification registry empty."}

    match = None
    for line in REGISTRY_FILE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("verification_id") == verification_id or rec.get("content_sha256", "").startswith(verification_id):
            match = rec
            break

    if not match:
        return {"valid": False, "message": "Verification ID not found."}

    from backend.forensics.digital_signature import verify_signature

    signable = match.get("signable") or {}
    sig_meta = {
        "content_sha256": match.get("content_sha256"),
        "content_sha512": match.get("content_sha512", ""),
        "signature": match.get("signature"),
    }
    valid, message = verify_signature(signable, sig_meta)
    return {
        "valid": valid,
        "message": message,
        "verification_id": verification_id,
        "report_id": match.get("report_id"),
        "evidence_id": match.get("evidence_id"),
        "template": match.get("template"),
        "content_sha256": match.get("content_sha256"),
        "signed_at": match.get("signed_at"),
    }
