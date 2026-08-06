"""
Structured error responses for API endpoints.
"""

from __future__ import annotations

import traceback
from typing import Any, Dict, Optional


class ForensicAnalysisError(Exception):
    """Base exception for forensic pipeline errors."""

    def __init__(
        self,
        message: str,
        module: str = "unknown",
        details: Optional[str] = None,
        status_code: int = 400,
    ):
        super().__init__(message)
        self.message = message
        self.module = module
        self.details = details or message
        self.status_code = status_code


class DocumentAnalysisError(ForensicAnalysisError):
    """Document-specific analysis error."""

    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(message, module="document_analysis", details=details, status_code=400)


def structured_error(
    error: str,
    module: str = "unknown",
    details: Optional[str] = None,
    include_traceback: bool = False,
    exc: Optional[BaseException] = None,
) -> Dict[str, Any]:
    """Build a structured JSON error payload."""
    payload: Dict[str, Any] = {
        "success": False,
        "error": error,
        "module": module,
        "details": details or error,
    }
    if include_traceback and exc is not None:
        payload["traceback"] = traceback.format_exc()
    return payload
