"""
Security configuration — environment-driven enterprise settings.
"""

from __future__ import annotations

import os
import secrets

# ── Authentication ───────────────────────────────────────────────────────────
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "false").lower() in ("1", "true", "yes")
AUTH_SEED_DEFAULTS = os.getenv("AUTH_SEED_DEFAULTS", "true").lower() in ("1", "true", "yes")
JWT_SECRET = os.getenv("JWT_SECRET") or os.getenv("AI_FORGE_JWT_SECRET") or ""
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))
JWT_REFRESH_DAYS = int(os.getenv("JWT_REFRESH_DAYS", "7"))

# ── Encryption ─────────────────────────────────────────────────────────────────
EVIDENCE_ENCRYPTION_ENABLED = os.getenv("EVIDENCE_ENCRYPTION", "true").lower() in ("1", "true", "yes")
EVIDENCE_ENCRYPTION_KEY = os.getenv("EVIDENCE_ENCRYPTION_KEY", "")

# ── Rate limiting ──────────────────────────────────────────────────────────────
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() in ("1", "true", "yes")
RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "120/minute")
RATE_LIMIT_UPLOAD = os.getenv("RATE_LIMIT_UPLOAD", "20/minute")
RATE_LIMIT_ANALYZE = os.getenv("RATE_LIMIT_ANALYZE", "30/minute")

# ── Virus scanning ─────────────────────────────────────────────────────────────
VIRUS_SCAN_ENABLED = os.getenv("VIRUS_SCAN_ENABLED", "true").lower() in ("1", "true", "yes")
CLAMAV_HOST = os.getenv("CLAMAV_HOST", "localhost")
CLAMAV_PORT = int(os.getenv("CLAMAV_PORT", "3310"))

# ── Temp files ─────────────────────────────────────────────────────────────────
TEMP_MAX_AGE_HOURS = int(os.getenv("TEMP_MAX_AGE_HOURS", "24"))
TEMP_CLEANUP_INTERVAL_SEC = int(os.getenv("TEMP_CLEANUP_INTERVAL_SEC", "3600"))

# ── Static data ────────────────────────────────────────────────────────────────
SERVE_DATA_STATIC = os.getenv("SERVE_DATA_STATIC", "false").lower() in ("1", "true", "yes")

# ── Queue ──────────────────────────────────────────────────────────────────────
QUEUE_ENABLED = os.getenv("QUEUE_ENABLED", "true").lower() in ("1", "true", "yes")
QUEUE_WORKER_CONCURRENCY = int(os.getenv("QUEUE_WORKER_CONCURRENCY", "2"))


def ensure_jwt_secret() -> str:
    global JWT_SECRET
    if JWT_SECRET:
        return JWT_SECRET
    path = os.getenv("JWT_SECRET_FILE", "data/secrets/jwt_secret.txt")
    from pathlib import Path
    p = Path(path)
    if p.is_file():
        JWT_SECRET = p.read_text(encoding="utf-8").strip()
        return JWT_SECRET
    p.parent.mkdir(parents=True, exist_ok=True)
    JWT_SECRET = secrets.token_urlsafe(48)
    p.write_text(JWT_SECRET, encoding="utf-8")
    return JWT_SECRET
