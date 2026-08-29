"""
Lightweight investigator attribution — JWT auth with header fallback.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from fastapi import Request

if TYPE_CHECKING:
    from backend.security.dependencies import AuthUser


@dataclass
class InvestigatorContext:
    user_id: str
    display_name: str
    role: str = "investigator"
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None


def get_investigator(
    request: Optional[Request] = None,
    auth_user: Optional["AuthUser"] = None,
) -> InvestigatorContext:
    if auth_user is not None:
        return InvestigatorContext(
            user_id=auth_user.user_id,
            display_name=auth_user.name,
            role=auth_user.role.value,
            client_ip=request.client.host if request and request.client else auth_user.client_ip,
            user_agent=request.headers.get("User-Agent") if request else None,
        )

    if request is not None:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            from backend.security.jwt_tokens import verify_access_token
            payload = verify_access_token(auth_header[7:])
            if payload:
                return InvestigatorContext(
                    user_id=payload["sub"],
                    display_name=payload.get("name", payload["sub"]),
                    role=payload.get("role", "investigator"),
                    client_ip=request.client.host if request.client else None,
                    user_agent=request.headers.get("User-Agent"),
                )

        user_id = request.headers.get("X-Investigator-ID", "anonymous")
        display_name = request.headers.get("X-Investigator-Name", user_id)
        return InvestigatorContext(
            user_id=user_id,
            display_name=display_name,
            role=request.headers.get("X-Investigator-Role", "investigator"),
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
        )

    return InvestigatorContext(user_id="system", display_name="System")
