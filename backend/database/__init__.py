"""AI-FORGE database layer."""

from backend.database.repository import (
    get_analysis_by_evidence_id,
    get_analysis_by_hash,
    init_db,
    save_analysis_record,
)

__all__ = [
    "init_db",
    "save_analysis_record",
    "get_analysis_by_hash",
    "get_analysis_by_evidence_id",
]
