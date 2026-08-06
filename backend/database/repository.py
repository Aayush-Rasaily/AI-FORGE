"""
SQLite persistence for analysis results — instant report reopening.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker

logger = logging.getLogger("ai_forge.db")

DB_PATH = Path("data/temp/aiforge.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    f"sqlite:///{DB_PATH.as_posix()}",
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


class AnalysisRecord(Base):
    __tablename__ = "analysis_records"

    id = Column(String(64), primary_key=True)
    file_hash = Column(String(64), index=True, nullable=False)
    evidence_id = Column(String(64), index=True, nullable=True)
    media_type = Column(String(32), nullable=False)
    filename = Column(String(512), nullable=True)
    risk_score = Column(Float, default=0.0)
    verdict = Column(String(256), nullable=True)
    analysis_json = Column(Text, nullable=False)
    tampering_json = Column(Text, nullable=True)
    jury_json = Column(Text, nullable=True)
    artifact_paths_json = Column(Text, nullable=True)
    execution_times_json = Column(Text, nullable=True)
    deep_scan = Column(String(8), default="true")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized at %s", DB_PATH)


def get_session() -> Session:
    return SessionLocal()


def save_analysis_record(
    record_id: str,
    file_hash: str,
    media_type: str,
    analysis: Dict[str, Any],
    *,
    evidence_id: Optional[str] = None,
    filename: Optional[str] = None,
    tampering: Optional[Dict[str, Any]] = None,
    jury: Optional[Dict[str, Any]] = None,
    artifact_paths: Optional[Dict[str, str]] = None,
    execution_times: Optional[Dict[str, float]] = None,
    deep_scan: bool = True,
) -> None:
    init_db()
    session = get_session()
    try:
        risk = float(analysis.get("risk_score") or analysis.get("forensic_score", 0) * 100 or 0)
        verdict = analysis.get("verdict") or analysis.get("overall_verdict")

        existing = session.query(AnalysisRecord).filter_by(file_hash=file_hash, media_type=media_type).first()
        payload = {
            "id": record_id,
            "file_hash": file_hash,
            "evidence_id": evidence_id,
            "media_type": media_type,
            "filename": filename,
            "risk_score": risk,
            "verdict": str(verdict) if verdict else None,
            "analysis_json": json.dumps(analysis, default=str),
            "tampering_json": json.dumps(tampering or {}, default=str),
            "jury_json": json.dumps(jury or {}, default=str),
            "artifact_paths_json": json.dumps(artifact_paths or {}, default=str),
            "execution_times_json": json.dumps(execution_times or {}, default=str),
            "deep_scan": "true" if deep_scan else "false",
            "updated_at": datetime.now(timezone.utc),
        }
        if existing:
            for k, v in payload.items():
                setattr(existing, k, v)
        else:
            session.add(AnalysisRecord(**payload))
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.warning("Failed to save analysis record: %s", exc)
    finally:
        session.close()


def get_analysis_by_hash(file_hash: str, media_type: str) -> Optional[Dict[str, Any]]:
    init_db()
    session = get_session()
    try:
        rec = (
            session.query(AnalysisRecord)
            .filter_by(file_hash=file_hash, media_type=media_type)
            .order_by(AnalysisRecord.updated_at.desc())
            .first()
        )
        if not rec:
            return None
        return {
            "analysis": json.loads(rec.analysis_json),
            "tampering": json.loads(rec.tampering_json or "{}"),
            "jury": json.loads(rec.jury_json or "{}"),
            "artifact_paths": json.loads(rec.artifact_paths_json or "{}"),
            "execution_times": json.loads(rec.execution_times_json or "{}"),
            "risk_score": rec.risk_score,
            "verdict": rec.verdict,
            "evidence_id": rec.evidence_id,
            "deep_scan": rec.deep_scan == "true",
            "cached": True,
            "cache_source": "database",
        }
    finally:
        session.close()


def get_analysis_by_evidence_id(evidence_id: str) -> Optional[Dict[str, Any]]:
    init_db()
    session = get_session()
    try:
        rec = session.query(AnalysisRecord).filter_by(evidence_id=evidence_id).first()
        if not rec:
            return None
        return {
            "analysis": json.loads(rec.analysis_json),
            "tampering": json.loads(rec.tampering_json or "{}"),
            "jury": json.loads(rec.jury_json or "{}"),
            "artifact_paths": json.loads(rec.artifact_paths_json or "{}"),
            "execution_times": json.loads(rec.execution_times_json or "{}"),
            "risk_score": rec.risk_score,
            "verdict": rec.verdict,
            "file_hash": rec.file_hash,
            "cached": True,
            "cache_source": "database",
        }
    finally:
        session.close()
