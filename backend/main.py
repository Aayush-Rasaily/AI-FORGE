"""
AI-FORGE FastAPI Application Entry Point.

Single FastAPI() instance. All routers share the same CORS + logging middleware.
"""

from __future__ import annotations

import logging
import os
import sys

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.api.video_routes import router as video_router
from backend.api.routes import router as evidence_router
from backend.api.signature_routes import (
    compare_alias_router,
    router as signature_router,
)
from backend.api.jury_routes import router as jury_router
from backend.api.forensics_routes import router as forensics_router
from backend.api.custody_routes import router as custody_router
from backend.api.report_routes import router as report_router
from backend.api.case_routes import router as case_router
from backend.api.learning_routes import router as learning_router
from backend.api.progress_routes import router as progress_router
from backend.api.ws_routes import router as ws_router
from backend.api.pipeline_routes import router as pipeline_router
from backend.api.metrics_routes import router as metrics_router
from backend.api.copilot_routes import router as copilot_router
from backend.api.investigate_routes import router as investigate_router
from backend.api.auth_routes import router as auth_router
from backend.api.tasks_routes import router as tasks_router
from backend.api.forensic_findings_routes import router as forensic_findings_router
from backend.middleware.logging_middleware import StructuredLoggingMiddleware
from backend.middleware.security_middleware import SecurityMiddleware
from backend.utils.hardware import get_device_info
from backend.utils.performance_config import (
    ARTIFACT_POLL_INTERVAL_MS,
    ARTIFACT_POLL_MAX_ATTEMPTS,
    REPORT_POLL_INTERVAL_MS,
    REPORT_POLL_MAX_ATTEMPTS,
    SLA_IMAGE_SEC,
    SLA_PDF_SEC,
    SLA_VIDEO_SEC,
)
from backend.utils.inference_engine import inference_capabilities
from backend.utils.worker_pool import shutdown_pool
from backend.utils.model_warmup import warmup_models_async
from backend.security.config import SERVE_DATA_STATIC

# ============================================================
# SINGLE FastAPI APPLICATION INSTANCE
# ============================================================

app = FastAPI(
    title="AI-FORGE API",
    description="AI-Powered Multimodal Fraud Detection and Digital Forensics Platform",
    version="1.0.0",
)

# ============================================================
# CORS — explicit local Vite ports + optional production origins
# Added LAST among middleware so it is the OUTERMOST wrapper.
# ============================================================

_DEFAULT_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5175",
    "http://localhost:5176",
    "http://127.0.0.1:5176",
    "http://localhost:5177",
    "http://127.0.0.1:5177",
]

_env_origins = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "").split(",")
    if o.strip()
]
_cors_origins = list(dict.fromkeys(_DEFAULT_ORIGINS + _env_origins))

# Inner middleware first (logging), security, then CORS last → CORS outermost
app.add_middleware(StructuredLoggingMiddleware)
app.add_middleware(SecurityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Ensure JSON errors still go through CORS (never bare 500 without headers)."""
    logging.getLogger("ai_forge").exception("Unhandled error on %s: %s", request.url.path, exc)
    origin = request.headers.get("origin")
    response = JSONResponse(
        status_code=500,
        content={
            "status": "failed",
            "success": False,
            "detail": "Internal server error",
            "reason": str(exc)[:500],
        },
    )
    if origin and (
        origin in _cors_origins
        or origin.startswith("http://localhost:")
        or origin.startswith("http://127.0.0.1:")
    ):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Vary"] = "Origin"
    return response


# ============================================================
# API ROUTERS — all share the same app + middleware
# ============================================================

app.include_router(auth_router)
app.include_router(tasks_router)
app.include_router(video_router)
app.include_router(evidence_router)
app.include_router(forensic_findings_router)
app.include_router(pipeline_router)
app.include_router(investigate_router)
app.include_router(copilot_router)
app.include_router(signature_router)
app.include_router(compare_alias_router)
app.include_router(jury_router)
app.include_router(forensics_router)
app.include_router(custody_router)
app.include_router(report_router)
app.include_router(case_router)
app.include_router(learning_router)
app.include_router(progress_router)
app.include_router(ws_router)
app.include_router(metrics_router)


@app.on_event("startup")
def on_startup():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        stream=sys.stdout,
    )
    from backend.database import init_db
    from backend.forensics.repository import init_forensic_db
    from backend.learning.engine import init_learning_db

    init_db()
    init_forensic_db()
    init_learning_db()
    try:
        from backend.cases.case_audit import _ensure_tables
        _ensure_tables()
    except Exception:
        pass
    try:
        from backend.security.user_service import init_auth_db
        init_auth_db()
    except Exception as exc:
        logging.getLogger("ai_forge").warning("Auth init failed: %s", exc)
    try:
        from backend.security.temp_files import ensure_secure_dirs, run_scheduled_cleanup
        ensure_secure_dirs()
        run_scheduled_cleanup()
        import threading
        from backend.security.config import TEMP_CLEANUP_INTERVAL_SEC

        def _cleanup_loop():
            import time
            while True:
                time.sleep(TEMP_CLEANUP_INTERVAL_SEC)
                try:
                    run_scheduled_cleanup()
                except Exception:
                    pass

        threading.Thread(target=_cleanup_loop, daemon=True, name="temp_cleanup").start()
    except Exception:
        pass
    try:
        from backend.learning.benchmark import _ensure_datasets
        _ensure_datasets()
    except Exception:
        pass
    try:
        from backend.learning.engine import register_model_version

        for name, ver in [
            ("efficientnet_b0", "1.0"),
            ("vit_b_16", "1.0"),
            ("xception", "1.0"),
            ("clip_vit_base_patch32", "1.0"),
        ]:
            register_model_version(name, ver, set_active=True)
    except Exception:
        pass
    caps = inference_capabilities()
    logging.getLogger("ai_forge").info(
        "AI-FORGE backend started | device=%s fp16=%s onnx=%s tensorrt=%s | cors_origins=%s",
        caps.get("device"),
        caps.get("fp16_enabled"),
        caps.get("onnx_enabled"),
        caps.get("tensorrt_available"),
        len(_cors_origins),
    )
    warmup_models_async()


@app.on_event("shutdown")
def on_shutdown():
    shutdown_pool()


if SERVE_DATA_STATIC:
    app.mount(
        "/data",
        StaticFiles(directory="data"),
        name="data",
    )


@app.get("/")
def root():
    return {
        "message": "Welcome to AI-FORGE API",
        "status": "success",
    }


@app.get("/api/health")
def health_check():
    from backend.security.config import AUTH_ENABLED, EVIDENCE_ENCRYPTION_ENABLED, QUEUE_ENABLED, VIRUS_SCAN_ENABLED
    from backend.tasks.queue import queue_depth

    caps = inference_capabilities()
    redis_ok = False
    try:
        from backend.utils.redis_cache import _get_redis
        redis_ok = _get_redis() is not None
    except Exception:
        pass

    return {
        "status": "healthy",
        "service": "AI-FORGE Backend",
        "hardware": get_device_info(),
        "inference": caps,
        "security": {
            "auth_enabled": AUTH_ENABLED,
            "encryption_enabled": EVIDENCE_ENCRYPTION_ENABLED,
            "virus_scan_enabled": VIRUS_SCAN_ENABLED,
            "queue_enabled": QUEUE_ENABLED,
            "redis_connected": redis_ok,
            "queue_depth": queue_depth(),
        },
        "sla_targets": {
            "image_sec": SLA_IMAGE_SEC,
            "pdf_sec": SLA_PDF_SEC,
            "video_sec": SLA_VIDEO_SEC,
        },
        "polling": {
            "report_poll_interval_ms": REPORT_POLL_INTERVAL_MS,
            "report_poll_max_attempts": REPORT_POLL_MAX_ATTEMPTS,
            "artifact_poll_interval_ms": ARTIFACT_POLL_INTERVAL_MS,
            "artifact_poll_max_attempts": ARTIFACT_POLL_MAX_ATTEMPTS,
        },
    }
