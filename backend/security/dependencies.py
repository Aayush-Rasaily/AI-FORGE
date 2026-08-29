"""
FastAPI auth dependencies — JWT + RBAC enforcement.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.security.config import AUTH_ENABLED
from backend.security.jwt_tokens import verify_access_token
from backend.security.rbac import Role, has_permission, normalize_role

_bearer = HTTPBearer(auto_error=False)


@dataclass
class AuthUser:
    user_id: str
    email: str
    name: str
    role: Role
    client_ip: Optional[str] = None

    def can(self, permission: str) -> bool:
        return has_permission(self.role.value, permission)


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Optional[AuthUser]:
    if credentials and credentials.credentials:
        payload = verify_access_token(credentials.credentials)
        if payload:
            return AuthUser(
                user_id=payload["sub"],
                email=payload.get("email", ""),
                name=payload.get("name", payload["sub"]),
                role=normalize_role(payload.get("role", "investigator")),
                client_ip=request.client.host if request.client else None,
            )
    # Legacy header fallback (dev / service accounts)
    hdr_id = request.headers.get("X-Investigator-ID")
    if hdr_id and hdr_id != "anonymous":
        return AuthUser(
            user_id=hdr_id,
            email="",
            name=request.headers.get("X-Investigator-Name", hdr_id),
            role=normalize_role(request.headers.get("X-Investigator-Role", "investigator")),
            client_ip=request.client.host if request.client else None,
        )
    return None


async def get_current_user(
    request: Request,
    user: Optional[AuthUser] = Depends(get_optional_user),
) -> AuthUser:
    if not AUTH_ENABLED:
        if user:
            return user
        return AuthUser(
            user_id="dev",
            email="dev@local",
            name="Developer",
            role=Role.ADMIN,
            client_ip=request.client.host if request.client else None,
        )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_permission(permission: str) -> Callable:
    async def _guard(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if not user.can(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}",
            )
        return user
    return _guard


def require_roles(*roles: str) -> Callable:
    allowed = {normalize_role(r) for r in roles}

    async def _guard(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if user.role == Role.ADMIN:
            return user
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role.value}' not authorized",
            )
        return user
    return _guard
