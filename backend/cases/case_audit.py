"""
Case audit trail — append-only timeline + audit log integration.
Investigation history is never deleted.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, Optional

from backend.database.repository import get_session, init_db
from backend.forensics.models import CaseTimelineEvent
from backend.forensics.repository import append_audit_log

logger = logging.getLogger("ai_forge.cases.audit")

CASE_STATUSES = frozenset({
    "open", "investigating", "pending", "closed", "court_submitted",
})
CASE_PRIORITIES = frozenset({"low", "normal", "high", "critical"})


def _ensure_tables() -> None:
    init_db()
    from backend.database.repository import Base, engine
    from backend.forensics import models as _  # noqa
    Base.metadata.create_all(bind=engine)
    _migrate_columns()


def _migrate_columns() -> None:
    """Add priority/verdict columns to existing SQLite databases."""
    from sqlalchemy import text

    session = get_session()
    try:
        for stmt in (
            "ALTER TABLE investigations ADD COLUMN priority VARCHAR(16) DEFAULT 'normal'",
            "ALTER TABLE investigations ADD COLUMN verdict VARCHAR(64)",
            "ALTER TABLE investigations ADD COLUMN organization VARCHAR(256)",
            "ALTER TABLE investigations ADD COLUMN department VARCHAR(256)",
        ):
            try:
                session.execute(text(stmt))
                session.commit()
            except Exception:
                session.rollback()
    finally:
        session.close()


def record_case_event(
    investigation_id: str,
    event_type: str,
    summary: str,
    *,
    actor_id: str = "system",
    actor_name: str = "System",
    evidence_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    client_ip: Optional[str] = None,
) -> Dict[str, Any]:
    """Append timeline event + audit log entry (immutable history)."""
    _ensure_tables()
    session = get_session()
    try:
        event = CaseTimelineEvent(
            id=str(uuid.uuid4()),
            investigation_id=investigation_id,
            event_type=event_type,
            actor_id=actor_id,
            actor_name=actor_name,
            summary=summary,
            details_json=json.dumps(details or {}, default=str),
            evidence_id=evidence_id,
        )
        session.add(event)
        session.commit()
        timeline_entry = _timeline_dict(event)
    except Exception as exc:
        session.rollback()
        logger.error("timeline_write_failed | %s", exc)
        raise
    finally:
        session.close()

    try:
        append_audit_log(
            f"case.{event_type}",
            user_id=actor_id,
            user_name=actor_name,
            resource_type="case",
            resource_id=investigation_id,
            evidence_id=evidence_id,
            investigation_id=investigation_id,
            client_ip=client_ip,
            details={"summary": summary, **(details or {})},
        )
    except Exception as exc:
        logger.warning("audit_log_skipped | %s", exc)

    return timeline_entry


def get_case_timeline(investigation_id: str, *, limit: int = 200) -> list:
    _ensure_tables()
    session = get_session()
    try:
        rows = (
            session.query(CaseTimelineEvent)
            .filter_by(investigation_id=investigation_id)
            .order_by(CaseTimelineEvent.created_at.desc())
            .limit(limit)
            .all()
        )
        return [_timeline_dict(r) for r in rows]
    finally:
        session.close()


def _timeline_dict(event: CaseTimelineEvent) -> Dict[str, Any]:
    details = {}
    if event.details_json:
        try:
            details = json.loads(event.details_json)
        except json.JSONDecodeError:
            details = {}
    return {
        "id": event.id,
        "investigation_id": event.investigation_id,
        "event_type": event.event_type,
        "actor_id": event.actor_id,
        "actor_name": event.actor_name,
        "summary": event.summary,
        "details": details,
        "evidence_id": event.evidence_id,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }
