"""
Auth user model — credentials separate from investigator registry.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String

from backend.database.repository import Base


class AuthUser(Base):
    __tablename__ = "auth_users"

    id = Column(String(64), primary_key=True)
    email = Column(String(256), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    name = Column(String(256), nullable=False)
    role = Column(String(32), nullable=False, default="investigator")
    investigator_id = Column(String(64), nullable=True, index=True)
    active = Column(String(8), default="true")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login_at = Column(DateTime, nullable=True)
