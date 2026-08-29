"""
Security audit logging — wraps forensic audit with security events.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

logger = logging.getLogger("ai_forge.security.audit")

SECURITY_AUDIT_LOG = Path("data/forensics/security_audit.jsonl")


def log_security_event(
    event_type: str,
    *,
    user_id: str = "system",
    user_name: str = "System",
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    client_ip: Optional[str] = None,
    success: bool = True,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    record = {
        "id": f"SEC-{uuid4().hex[:12]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "user_id": user_id,
        "user_name": user_name,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "client_ip": client_ip,
        "success": success,
        "details": details or {},
    }
    SECURITY_AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(SECURITY_AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")

    try:
        from backend.forensics.repository import append_audit_log
        append_audit_log(
            user_id=user_id,
            user_name=user_name,
            action=f"security.{event_type}",
            resource_type=resource_type,
            resource_id=resource_id,
            client_ip=client_ip,
            details_json=json.dumps(details or {}, default=str),
            success="true" if success else "false",
        )
    except Exception as exc:
        logger.debug("Forensic audit mirror failed: %s", exc)

    level = logging.INFO if success else logging.WARNING
    logger.log(level, "SECURITY %s | user=%s | %s", event_type, user_id, details)
