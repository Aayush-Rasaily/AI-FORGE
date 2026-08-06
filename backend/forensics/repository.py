"""
Forensic integrity persistence — investigations, custody, audit, immutable reports.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.database.repository import engine, get_session, init_db
from backend.forensics.digital_signature import canonical_json, sign_payload, verify_signature
from backend.forensics.models import (
    AuditLogEntry,
    CustodyEvent,
    EvidenceRegistry,
    Investigation,
    ReportSnapshot,
)

logger = logging.getLogger("ai_forge.forensics.db")

REPORTS_DIR = Path("data/forensics/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def init_forensic_db() -> None:
    init_db()
    from backend.forensics import models as _  # noqa: F401 — register tables
    from backend.database.repository import Base
    Base.metadata.create_all(bind=engine)
    logger.info("Forensic integrity tables initialized")


def create_investigation(
    title: str,
    *,
    description: Optional[str] = None,
    lead_investigator_id: str = "anonymous",
    lead_investigator_name: str = "Anonymous",
) -> Dict[str, Any]:
    init_forensic_db()
    inv_id = f"INV-{uuid.uuid4().hex[:12].upper()}"
    session = get_session()
    try:
        inv = Investigation(
            id=inv_id,
            title=title,
            description=description,
            lead_investigator_id=lead_investigator_id,
            lead_investigator_name=lead_investigator_name,
        )
        session.add(inv)
        session.commit()
        return _investigation_dict(inv)
    except Exception as exc:
        session.rollback()
        raise exc
    finally:
        session.close()


def get_investigation(investigation_id: str) -> Optional[Dict[str, Any]]:
    init_forensic_db()
    session = get_session()
    try:
        inv = session.query(Investigation).filter_by(id=investigation_id).first()
        if not inv:
            return None
        evidence = session.query(EvidenceRegistry).filter_by(investigation_id=investigation_id).all()
        custody_count = session.query(CustodyEvent).filter_by(investigation_id=investigation_id).count()
        result = _investigation_dict(inv)
        result["evidence_count"] = len(evidence)
        result["custody_events"] = custody_count
        result["evidence_ids"] = [e.evidence_id for e in evidence]
        return result
    finally:
        session.close()


def list_investigations(limit: int = 50) -> List[Dict[str, Any]]:
    init_forensic_db()
    session = get_session()
    try:
        rows = session.query(Investigation).order_by(Investigation.created_at.desc()).limit(limit).all()
        return [_investigation_dict(r) for r in rows]
    finally:
        session.close()


def register_evidence(
    evidence_id: str,
    *,
    original_filename: str,
    stored_path: str,
    media_type: str,
    sha256: str,
    sha512: str,
    size_bytes: int,
    investigation_id: Optional[str] = None,
    intake_user_id: str = "anonymous",
    intake_user_name: str = "Anonymous",
) -> Dict[str, Any]:
    init_forensic_db()
    session = get_session()
    try:
        existing = session.query(EvidenceRegistry).filter_by(evidence_id=evidence_id).first()
        if existing:
            return _evidence_dict(existing)

        rec = EvidenceRegistry(
            evidence_id=evidence_id,
            investigation_id=investigation_id,
            original_filename=original_filename,
            stored_path=stored_path,
            media_type=media_type,
            size_bytes=size_bytes,
            sha256=sha256,
            sha512=sha512,
            intake_user_id=intake_user_id,
            intake_user_name=intake_user_name,
        )
        session.add(rec)
        session.commit()
        return _evidence_dict(rec)
    except Exception as exc:
        session.rollback()
        raise exc
    finally:
        session.close()


def get_evidence_record(evidence_id: str) -> Optional[Dict[str, Any]]:
    init_forensic_db()
    session = get_session()
    try:
        rec = session.query(EvidenceRegistry).filter_by(evidence_id=evidence_id).first()
        return _evidence_dict(rec) if rec else None
    finally:
        session.close()


def list_recent_evidence(limit: int = 50) -> List[Dict[str, Any]]:
    """Shared evidence inventory used by Dashboard, Investigation, Timeline, Reports."""
    init_forensic_db()
    session = get_session()
    try:
        rows = (
            session.query(EvidenceRegistry)
            .order_by(EvidenceRegistry.intake_timestamp.desc())
            .limit(max(1, min(limit, 200)))
            .all()
        )
        return [_evidence_dict(r) for r in rows]
    finally:
        session.close()


def _iso_ts(dt: datetime) -> str:
    """Normalize timestamps so DB round-trips match hash computation."""
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _compute_event_hash(event_data: Dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(event_data).encode()).hexdigest()


def append_custody_event(
    evidence_id: str,
    event_type: str,
    action_description: str,
    *,
    sha256: str,
    sha512: str,
    actor_id: str = "system",
    actor_name: str = "System",
    investigation_id: Optional[str] = None,
    location: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    init_forensic_db()
    session = get_session()
    try:
        prev = (
            session.query(CustodyEvent)
            .filter_by(evidence_id=evidence_id)
            .order_by(CustodyEvent.event_timestamp.desc())
            .first()
        )
        prev_hash = prev.event_hash if prev else "GENESIS"

        event_id = str(uuid.uuid4())
        ts = datetime.now(timezone.utc)

        event_core = {
            "id": event_id,
            "evidence_id": evidence_id,
            "event_type": event_type,
            "event_timestamp": _iso_ts(ts),
            "actor_id": actor_id,
            "action_description": action_description,
            "sha256_at_event": sha256,
            "sha512_at_event": sha512,
            "previous_event_hash": prev_hash,
        }
        event_hash = _compute_event_hash(event_core)

        event = CustodyEvent(
            id=event_id,
            evidence_id=evidence_id,
            investigation_id=investigation_id,
            event_type=event_type,
            event_timestamp=ts,
            actor_id=actor_id,
            actor_name=actor_name,
            action_description=action_description,
            location=location,
            sha256_at_event=sha256,
            sha512_at_event=sha512,
            previous_event_hash=prev_hash,
            event_hash=event_hash,
            metadata_json=json.dumps(metadata or {}, default=str),
        )
        session.add(event)
        session.commit()
        return _custody_dict(event)
    except Exception as exc:
        session.rollback()
        raise exc
    finally:
        session.close()


def get_custody_chain(evidence_id: str) -> List[Dict[str, Any]]:
    init_forensic_db()
    session = get_session()
    try:
        events = (
            session.query(CustodyEvent)
            .filter_by(evidence_id=evidence_id)
            .order_by(CustodyEvent.event_timestamp.asc())
            .all()
        )
        return [_custody_dict(e) for e in events]
    finally:
        session.close()


def verify_custody_chain(evidence_id: str) -> Dict[str, Any]:
    from backend.evidence.storage import verify_original_integrity

    integrity = verify_original_integrity(evidence_id)
    chain = get_custody_chain(evidence_id)

    if not chain:
        return {
            "valid": integrity.get("valid", True),
            "events": 0,
            "issues": [],
            "integrity": integrity,
            "sha256_match": integrity.get("sha256_match", True),
            "sha512_match": integrity.get("sha512_match", True),
            "evidence_untouched": integrity.get("evidence_untouched", True),
            "message": integrity.get("message", "No custody events — file integrity checked."),
        }

    valid = True
    issues = []
    for i, event in enumerate(chain):
        expected_prev = "GENESIS" if i == 0 else chain[i - 1]["event_hash"]
        if event["previous_event_hash"] != expected_prev:
            valid = False
            issues.append(f"Event {i + 1}: broken hash chain link.")

        core = {
            "id": event["id"],
            "evidence_id": event["evidence_id"],
            "event_type": event["event_type"],
            "event_timestamp": event["event_timestamp"],
            "actor_id": event["actor_id"],
            "action_description": event["action_description"],
            "sha256_at_event": event["sha256_at_event"],
            "sha512_at_event": event["sha512_at_event"],
            "previous_event_hash": event["previous_event_hash"],
        }
        computed = _compute_event_hash(core)
        if computed != event["event_hash"]:
            # Retry with normalized timestamp (fixes legacy DB microsecond drift)
            core["event_timestamp"] = _iso_ts(
                datetime.fromisoformat(str(event["event_timestamp"]).replace("Z", "+00:00"))
            ) if event["event_timestamp"] else ""
            computed = _compute_event_hash(core)
        if computed != event["event_hash"]:
            valid = False
            issues.append(f"Event {i + 1}: event hash mismatch.")

    file_ok = integrity.get("valid", True)
    overall = valid and file_ok

    return {
        "valid": overall,
        "events": len(chain),
        "issues": issues,
        "integrity": integrity,
        "sha256_match": integrity.get("sha256_match", file_ok),
        "sha512_match": integrity.get("sha512_match", file_ok),
        "evidence_untouched": integrity.get("evidence_untouched", file_ok),
        "message": (
            "Integrity verified."
            if overall
            else ("Chain integrity compromised." if not valid else integrity.get("message", "Hash mismatch."))
        ),
    }


def append_audit_log(
    action: str,
    *,
    user_id: str = "system",
    user_name: str = "System",
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    evidence_id: Optional[str] = None,
    investigation_id: Optional[str] = None,
    client_ip: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    success: bool = True,
) -> Dict[str, Any]:
    init_forensic_db()
    session = get_session()
    try:
        entry = AuditLogEntry(
            id=str(uuid.uuid4()),
            user_id=user_id,
            user_name=user_name,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            evidence_id=evidence_id,
            investigation_id=investigation_id,
            client_ip=client_ip,
            details_json=json.dumps(details or {}, default=str),
            success="true" if success else "false",
        )
        session.add(entry)
        session.commit()
        return _audit_dict(entry)
    except Exception as exc:
        session.rollback()
        raise exc
    finally:
        session.close()


def get_audit_log(
    *,
    evidence_id: Optional[str] = None,
    investigation_id: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    init_forensic_db()
    session = get_session()
    try:
        q = session.query(AuditLogEntry)
        if evidence_id:
            q = q.filter_by(evidence_id=evidence_id)
        if investigation_id:
            q = q.filter_by(investigation_id=investigation_id)
        if user_id:
            q = q.filter_by(user_id=user_id)
        rows = q.order_by(AuditLogEntry.timestamp.desc()).limit(limit).all()
        return [_audit_dict(r) for r in rows]
    finally:
        session.close()


def seal_immutable_report(
    evidence_id: str,
    report_type: str,
    report_payload: Dict[str, Any],
    *,
    manifest: Optional[Dict[str, Any]] = None,
    investigation_id: Optional[str] = None,
    sealed_by_id: str = "system",
    sealed_by_name: str = "System",
) -> Dict[str, Any]:
    """Write-once immutable report with digital signature."""
    init_forensic_db()
    session = get_session()

    existing_count = session.query(ReportSnapshot).filter_by(
        evidence_id=evidence_id, report_type=report_type
    ).count()
    version = existing_count + 1
    snapshot_id = f"RPT-{evidence_id}-{report_type}-v{version}"

    full_report = {
        "snapshot_id": snapshot_id,
        "evidence_id": evidence_id,
        "report_type": report_type,
        "version": version,
        "sealed_at": datetime.now(timezone.utc).isoformat(),
        "report": report_payload,
        "reproducibility_manifest": manifest,
    }

    sig = sign_payload(full_report)
    full_report["integrity"] = sig

    file_path = REPORTS_DIR / f"{snapshot_id}.json"
    if file_path.exists():
        session.close()
        raise ValueError(f"Report snapshot already exists: {snapshot_id}")

    file_path.write_text(json.dumps(full_report, indent=2, default=str), encoding="utf-8")

    try:
        rec = ReportSnapshot(
            id=snapshot_id,
            evidence_id=evidence_id,
            investigation_id=investigation_id,
            report_type=report_type,
            version=version,
            content_sha256=sig["content_sha256"],
            content_sha512=sig["content_sha512"],
            signature=sig["signature"],
            manifest_hash=manifest.get("manifest_hash") if manifest else None,
            file_path=str(file_path),
            sealed_by_id=sealed_by_id,
            sealed_by_name=sealed_by_name,
        )
        session.add(rec)
        session.commit()
        return {
            "snapshot_id": snapshot_id,
            "evidence_id": evidence_id,
            "report_type": report_type,
            "version": version,
            "integrity": sig,
            "file_path": str(file_path),
            "immutable": True,
        }
    except Exception as exc:
        session.rollback()
        file_path.unlink(missing_ok=True)
        raise exc
    finally:
        session.close()


def get_report_snapshots(evidence_id: str) -> List[Dict[str, Any]]:
    init_forensic_db()
    session = get_session()
    try:
        rows = (
            session.query(ReportSnapshot)
            .filter_by(evidence_id=evidence_id)
            .order_by(ReportSnapshot.sealed_at.desc())
            .all()
        )
        return [_snapshot_dict(r) for r in rows]
    finally:
        session.close()


def verify_report_snapshot(snapshot_id: str) -> Dict[str, Any]:
    init_forensic_db()
    session = get_session()
    try:
        rec = session.query(ReportSnapshot).filter_by(id=snapshot_id).first()
        if not rec:
            return {"valid": False, "message": "Snapshot not found."}

        file_path = Path(rec.file_path)
        if not file_path.exists():
            return {"valid": False, "message": "Report file missing."}

        full_report = json.loads(file_path.read_text(encoding="utf-8"))
        integrity = full_report.get("integrity", {})
        report_body = {k: v for k, v in full_report.items() if k != "integrity"}
        valid, message = verify_signature(report_body, integrity)

        return {
            "valid": valid,
            "message": message,
            "snapshot_id": snapshot_id,
            "content_sha256": integrity.get("content_sha256"),
            "content_sha512": integrity.get("content_sha512"),
            "sealed_at": rec.sealed_at.isoformat() if rec.sealed_at else None,
        }
    finally:
        session.close()


def _investigation_dict(inv: Investigation) -> Dict[str, Any]:
    return {
        "id": inv.id,
        "title": inv.title,
        "description": inv.description,
        "status": inv.status,
        "lead_investigator_id": inv.lead_investigator_id,
        "lead_investigator_name": inv.lead_investigator_name,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
        "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
    }


def _evidence_dict(rec: EvidenceRegistry) -> Dict[str, Any]:
    return {
        "evidence_id": rec.evidence_id,
        "investigation_id": rec.investigation_id,
        "original_filename": rec.original_filename,
        "stored_path": rec.stored_path,
        "media_type": rec.media_type,
        "size_bytes": rec.size_bytes,
        "sha256": rec.sha256,
        "sha512": rec.sha512,
        "intake_timestamp": rec.intake_timestamp.isoformat() if rec.intake_timestamp else None,
        "intake_user_id": rec.intake_user_id,
        "intake_user_name": rec.intake_user_name,
        "status": rec.status,
    }


def _custody_dict(event: CustodyEvent) -> Dict[str, Any]:
    return {
        "id": event.id,
        "evidence_id": event.evidence_id,
        "investigation_id": event.investigation_id,
        "event_type": event.event_type,
        "event_timestamp": _iso_ts(event.event_timestamp) if event.event_timestamp else None,
        "actor_id": event.actor_id,
        "actor_name": event.actor_name,
        "action_description": event.action_description,
        "location": event.location,
        "sha256_at_event": event.sha256_at_event,
        "sha512_at_event": event.sha512_at_event,
        "previous_event_hash": event.previous_event_hash,
        "event_hash": event.event_hash,
        "metadata": json.loads(event.metadata_json or "{}"),
    }


def _audit_dict(entry: AuditLogEntry) -> Dict[str, Any]:
    return {
        "id": entry.id,
        "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
        "user_id": entry.user_id,
        "user_name": entry.user_name,
        "action": entry.action,
        "resource_type": entry.resource_type,
        "resource_id": entry.resource_id,
        "evidence_id": entry.evidence_id,
        "investigation_id": entry.investigation_id,
        "client_ip": entry.client_ip,
        "details": json.loads(entry.details_json or "{}"),
        "success": entry.success == "true",
    }


def _snapshot_dict(rec: ReportSnapshot) -> Dict[str, Any]:
    return {
        "snapshot_id": rec.id,
        "evidence_id": rec.evidence_id,
        "investigation_id": rec.investigation_id,
        "report_type": rec.report_type,
        "version": rec.version,
        "content_sha256": rec.content_sha256,
        "content_sha512": rec.content_sha512,
        "signature": rec.signature,
        "signature_algorithm": rec.signature_algorithm,
        "manifest_hash": rec.manifest_hash,
        "sealed_by_id": rec.sealed_by_id,
        "sealed_by_name": rec.sealed_by_name,
        "sealed_at": rec.sealed_at.isoformat() if rec.sealed_at else None,
        "immutable": rec.immutable == "true",
    }
