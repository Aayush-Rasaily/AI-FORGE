"""
Security middleware — headers, rate limiting, request audit.
"""

from __future__ import annotations

import logging
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.security.config import RATE_LIMIT_DEFAULT, RATE_LIMIT_UPLOAD, RATE_LIMIT_ANALYZE
from backend.security.rate_limit import check_rate_limit, rate_limit_key

logger = logging.getLogger("ai_forge.security.middleware")

PUBLIC_PATHS = {
    "/",
    "/api/health",
    "/api/auth/login",
    "/api/auth/refresh",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/metrics",
}

UPLOAD_PATHS = {"/api/evidence/upload"}
ANALYZE_PREFIXES = ("/api/evidence/analyze", "/api/investigate", "/api/pipeline")


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # Rate limiting
        if path not in PUBLIC_PATHS and request.method != "OPTIONS":
            limit = RATE_LIMIT_DEFAULT
            if path in UPLOAD_PATHS:
                limit = RATE_LIMIT_UPLOAD
            elif any(path.startswith(p) for p in ANALYZE_PREFIXES):
                limit = RATE_LIMIT_ANALYZE

            allowed, retry = check_rate_limit(rate_limit_key(request), limit)
            if not allowed:
                return Response(
                    content='{"detail":"Rate limit exceeded"}',
                    status_code=429,
                    media_type="application/json",
                    headers={"Retry-After": str(retry)},
                )

        response = await call_next(request)

        # Security headers
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )
        if request.url.scheme == "https":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )

        return response
