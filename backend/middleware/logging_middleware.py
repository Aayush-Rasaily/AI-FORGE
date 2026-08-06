"""
Pure ASGI request logging — does not wrap responses via BaseHTTPMiddleware
(which can strip CORS headers from FileResponse / error paths).
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Callable

logger = logging.getLogger("ai_forge.request")


class StructuredLoggingMiddleware:
    """ASGI middleware compatible with CORSMiddleware + FileResponse."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = None
        for name, value in scope.get("headers") or []:
            if name == b"x-request-id":
                request_id = value.decode("latin-1")
                break
        if not request_id:
            request_id = str(uuid.uuid4())

        method = scope.get("method", "?")
        path = scope.get("path", "?")
        client = "-"
        if scope.get("client"):
            client = scope["client"][0]

        start = time.perf_counter()
        status_code = 500

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 500)
                headers = list(message.get("headers") or [])
                headers.append((b"x-request-id", request_id.encode("latin-1")))
                message = {**message, "headers": headers}
            await send(message)

        logger.info(
            "request_start | id=%s | method=%s | path=%s | client=%s",
            request_id,
            method,
            path,
            client,
        )
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "request_error | id=%s | method=%s | path=%s | duration_ms=%.1f | error=%s",
                request_id,
                method,
                path,
                elapsed_ms,
                exc,
            )
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000
        level = logging.WARNING if status_code >= 400 else logging.INFO
        logger.log(
            level,
            "request_end | id=%s | method=%s | path=%s | status=%s | duration_ms=%.1f",
            request_id,
            method,
            path,
            status_code,
            elapsed_ms,
        )
