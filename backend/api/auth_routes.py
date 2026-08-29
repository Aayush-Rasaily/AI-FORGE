"""
Authentication API — login, token refresh, current user.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from backend.security.audit import log_security_event
from backend.security.config import RATE_LIMIT_DEFAULT
from backend.security.dependencies import AuthUser, get_current_user, require_permission
from backend.security.jwt_tokens import create_access_token, create_refresh_token, decode_token
from backend.security.rate_limit import check_rate_limit, rate_limit_key
from backend.security.rbac import PERM_USER_MANAGE
from backend.security.user_service import authenticate, create_user, get_user_by_id, list_users
from backend.security.validation import validate_email, validate_password

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str = Field(..., min_length=1, max_length=256)
    role: str = "investigator"


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request):
    allowed, retry = check_rate_limit(
        rate_limit_key(request, body.email),
        "10/minute",
    )
    if not allowed:
        raise HTTPException(status_code=429, detail=f"Too many login attempts. Retry in {retry}s")

    user = authenticate(body.email, body.password)
    if not user:
        log_security_event(
            "login_failed",
            user_id=body.email,
            client_ip=request.client.host if request.client else None,
            success=False,
            details={"email": body.email},
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access = create_access_token(
        user_id=user["id"],
        email=user["email"],
        role=user["role"],
        name=user["name"],
    )
    refresh = create_refresh_token(user_id=user["id"])

    log_security_event(
        "login_success",
        user_id=user["id"],
        user_name=user["name"],
        client_ip=request.client.host if request.client else None,
        details={"role": user["role"]},
    )

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user=user,
    )


@router.post("/refresh")
async def refresh_token(request: Request, refresh_token: Optional[str] = None):
    token = refresh_token or request.headers.get("X-Refresh-Token", "")
    if not token:
        raise HTTPException(status_code=400, detail="Refresh token required")
    try:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        user = get_user_by_id(payload["sub"])
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        access = create_access_token(
            user_id=user["id"],
            email=user["email"],
            role=user["role"],
            name=user["name"],
        )
        return {"access_token": access, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.get("/me")
async def me(user: AuthUser = Depends(get_current_user)):
    profile = get_user_by_id(user.user_id)
    return {
        "success": True,
        "user": profile or {
            "id": user.user_id,
            "email": user.email,
            "name": user.name,
            "role": user.role.value,
        },
    }


@router.post("/register")
async def register(
    body: RegisterRequest,
    request: Request,
    admin: AuthUser = Depends(require_permission(PERM_USER_MANAGE)),
):
    allowed, _ = check_rate_limit(rate_limit_key(request, admin.user_id), RATE_LIMIT_DEFAULT)
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    try:
        validate_password(body.password)
        user = create_user(
            validate_email(body.email),
            body.password,
            name=body.name,
            role=body.role,
        )
        log_security_event(
            "user_registered",
            user_id=admin.user_id,
            user_name=admin.name,
            resource_id=user["id"],
            client_ip=request.client.host if request.client else None,
            details={"email": user["email"], "role": user["role"]},
        )
        return {"success": True, "user": user}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/users")
async def users(admin: AuthUser = Depends(require_permission(PERM_USER_MANAGE))):
    return {"success": True, "users": list_users()}
