"""
User management — registration, login, seed defaults.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.database.repository import get_session, init_db
from backend.security.config import AUTH_SEED_DEFAULTS
from backend.security.models import AuthUser
from backend.security.passwords import hash_password, verify_password
from backend.security.rbac import Role, normalize_role
from backend.security.validation import validate_email, validate_password

logger = logging.getLogger("ai_forge.security.users")

DEFAULT_USERS = [
    {
        "email": "admin@aiforge.local",
        "password": "Admin123!",
        "name": "System Admin",
        "role": Role.ADMIN.value,
    },
    {
        "email": "supervisor@aiforge.local",
        "password": "Supervisor123!",
        "name": "Case Supervisor",
        "role": Role.SUPERVISOR.value,
    },
    {
        "email": "investigator@aiforge.local",
        "password": "Investigator123!",
        "name": "Lead Investigator",
        "role": Role.INVESTIGATOR.value,
    },
    {
        "email": "auditor@aiforge.local",
        "password": "Auditor123!",
        "name": "Compliance Auditor",
        "role": Role.AUDITOR.value,
    },
]


def init_auth_db() -> None:
    init_db()
    from backend.database.repository import Base, engine
    Base.metadata.create_all(bind=engine, tables=[AuthUser.__table__])
    if AUTH_SEED_DEFAULTS:
        seed_default_users()


def seed_default_users() -> None:
    session = get_session()
    try:
        if session.query(AuthUser).count() > 0:
            return
        for spec in DEFAULT_USERS:
            create_user(
                spec["email"],
                spec["password"],
                name=spec["name"],
                role=spec["role"],
                session=session,
            )
        session.commit()
        logger.info("Seeded %d default auth users", len(DEFAULT_USERS))
    except Exception as exc:
        session.rollback()
        logger.warning("Default user seed failed: %s", exc)
    finally:
        session.close()


def create_user(
    email: str,
    password: str,
    *,
    name: str,
    role: str = "investigator",
    investigator_id: Optional[str] = None,
    session=None,
) -> Dict[str, Any]:
    email = validate_email(email)
    validate_password(password)
    own_session = session is None
    if own_session:
        session = get_session()
    try:
        existing = session.query(AuthUser).filter_by(email=email).first()
        if existing:
            raise ValueError("Email already registered")
        user = AuthUser(
            id=f"USR-{uuid.uuid4().hex[:12]}",
            email=email,
            password_hash=hash_password(password),
            name=name,
            role=normalize_role(role).value,
            investigator_id=investigator_id,
            active="true",
        )
        session.add(user)
        if own_session:
            session.commit()
        return _user_dict(user)
    except Exception:
        if own_session:
            session.rollback()
        raise
    finally:
        if own_session:
            session.close()


def authenticate(email: str, password: str) -> Optional[Dict[str, Any]]:
    session = get_session()
    try:
        user = session.query(AuthUser).filter_by(email=validate_email(email)).first()
        if not user or user.active != "true":
            return None
        if not verify_password(password, user.password_hash):
            return None
        user.last_login_at = datetime.now(timezone.utc)
        session.commit()
        return _user_dict(user)
    finally:
        session.close()


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    session = get_session()
    try:
        user = session.query(AuthUser).filter_by(id=user_id).first()
        return _user_dict(user) if user else None
    finally:
        session.close()


def list_users() -> List[Dict[str, Any]]:
    session = get_session()
    try:
        return [_user_dict(u) for u in session.query(AuthUser).all()]
    finally:
        session.close()


def _user_dict(user: AuthUser) -> Dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "investigator_id": user.investigator_id,
        "active": user.active == "true",
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }
