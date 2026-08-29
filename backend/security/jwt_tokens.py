"""
JWT token creation and validation.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from jose import JWTError, jwt

from backend.security.config import (
    JWT_ALGORITHM,
    JWT_EXPIRE_MINUTES,
    JWT_REFRESH_DAYS,
    ensure_jwt_secret,
)


def create_access_token(
    *,
    user_id: str,
    email: str,
    role: str,
    name: str,
    expires_minutes: Optional[int] = None,
) -> str:
    secret = ensure_jwt_secret()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=expires_minutes or JWT_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "name": name,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": uuid4().hex[:16],
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def create_refresh_token(*, user_id: str) -> str:
    secret = ensure_jwt_secret()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(days=JWT_REFRESH_DAYS)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": uuid4().hex[:16],
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    secret = ensure_jwt_secret()
    return jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])


def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None
