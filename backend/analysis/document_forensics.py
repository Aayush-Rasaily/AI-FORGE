"""
Document forensic analysis — delegates to document_service.
Kept for backward compatibility with existing imports.
"""

from backend.services.document_service import analyze_document

__all__ = ["analyze_document"]
