"""
Input validation — sanitize IDs, filenames, and request fields.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_SAFE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_FILENAME_BAD = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

MAX_FILENAME_LEN = 255
MAX_STRING_LEN = 4096


def validate_id(value: str, field: str = "id") -> str:
    v = str(value or "").strip()
    if not v or not _SAFE_ID.match(v):
        raise ValueError(f"Invalid {field}: must be alphanumeric with _ or -")
    return v


def validate_email(value: str) -> str:
    v = str(value or "").strip().lower()
    if not v or not _SAFE_EMAIL.match(v) or len(v) > 254:
        raise ValueError("Invalid email address")
    return v


def sanitize_filename(name: str) -> str:
    base = Path(name or "upload").name
    base = _FILENAME_BAD.sub("_", base)
    base = base.strip(". ")
    if not base:
        base = "upload"
    return base[:MAX_FILENAME_LEN]


def sanitize_string(value: Optional[str], *, max_len: int = MAX_STRING_LEN) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    if len(s) > max_len:
        s = s[:max_len]
    return s


def validate_password(password: str) -> str:
    p = str(password or "")
    if len(p) < 8:
        raise ValueError("Password must be at least 8 characters")
    if len(p) > 128:
        raise ValueError("Password too long")
    return p
