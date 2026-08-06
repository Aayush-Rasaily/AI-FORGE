"""
Learning AI — feedback loop, threshold adaptation, model versioning, active learning.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, DateTime, Float, String, Text

from backend.database.repository import Base, engine, get_session, init_db

logger = logging.getLogger("ai_forge.learning")

LEARNING_DIR = Path("data/learning")
THRESHOLDS_FILE = LEARNING_DIR / "adaptive_thresholds.json"
MODEL_REGISTRY_FILE = LEARNING_DIR / "model_registry.json"

DEFAULT_THRESHOLDS = {
    "risk_high": 61.0,
    "risk_medium": 31.0,
    "tampering_alert": 0.55,
    "gan_detection": 0.65,
    "deepfake_alert": 0.70,
    "signature_match": 0.85,
}


class InvestigationFeedback(Base):
    __tablename__ = "investigation_feedback"

    id = Column(String(64), primary_key=True)
    evidence_id = Column(String(64), index=True, nullable=False)
    investigation_id = Column(String(64), index=True, nullable=True)
    analyst_id = Column(String(128), nullable=False)
    predicted_verdict = Column(String(128), nullable=True)
    actual_verdict = Column(String(128), nullable=False)
    predicted_risk = Column(Float, nullable=True)
    actual_risk = Column(Float, nullable=True)
    feedback_type = Column(String(32), default="correction")
    notes = Column(Text, nullable=True)
    used_for_training = Column(String(8), default="false")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(String(64), primary_key=True)
    model_name = Column(String(128), index=True, nullable=False)
    version = Column(String(32), nullable=False)
    path = Column(String(1024), nullable=True)
    metrics_json = Column(Text, nullable=True)
    active = Column(String(8), default="false")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def init_learning_db() -> None:
    init_db()
    LEARNING_DIR.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    if not THRESHOLDS_FILE.exists():
        THRESHOLDS_FILE.write_text(json.dumps(DEFAULT_THRESHOLDS, indent=2))


def get_adaptive_thresholds() -> Dict[str, float]:
    init_learning_db()
    if THRESHOLDS_FILE.exists():
        return {**DEFAULT_THRESHOLDS, **json.loads(THRESHOLDS_FILE.read_text())}
    return dict(DEFAULT_THRESHOLDS)


def submit_feedback(
    evidence_id: str,
    actual_verdict: str,
    *,
    analyst_id: str = "anonymous",
    predicted_verdict: Optional[str] = None,
    predicted_risk: Optional[float] = None,
    actual_risk: Optional[float] = None,
    investigation_id: Optional[str] = None,
    notes: Optional[str] = None,
    feedback_type: str = "correction",
) -> Dict[str, Any]:
    init_learning_db()
    session = get_session()
    try:
        fb = InvestigationFeedback(
            id=str(uuid.uuid4()),
            evidence_id=evidence_id,
            investigation_id=investigation_id,
            analyst_id=analyst_id,
            predicted_verdict=predicted_verdict,
            actual_verdict=actual_verdict,
            predicted_risk=predicted_risk,
            actual_risk=actual_risk,
            feedback_type=feedback_type,
            notes=notes,
        )
        session.add(fb)
        session.commit()
        _maybe_adjust_thresholds(session)
        return _feedback_dict(fb)
    finally:
        session.close()


def _maybe_adjust_thresholds(session) -> None:
    """Active learning — nudge thresholds based on recent feedback accuracy."""
    recent = (
        session.query(InvestigationFeedback)
        .order_by(InvestigationFeedback.created_at.desc())
        .limit(50)
        .all()
    )
    if len(recent) < 5:
        return

    false_positives = sum(
        1 for f in recent
        if f.predicted_risk and f.actual_risk is not None
        and f.predicted_risk >= 61 and f.actual_risk < 31
    )
    false_negatives = sum(
        1 for f in recent
        if f.predicted_risk and f.actual_risk is not None
        and f.predicted_risk < 31 and f.actual_risk >= 61
    )

    thresholds = get_adaptive_thresholds()
    adjusted = False

    if false_positives > false_negatives + 2:
        thresholds["risk_high"] = min(75.0, thresholds["risk_high"] + 1.0)
        adjusted = True
    elif false_negatives > false_positives + 2:
        thresholds["risk_high"] = max(50.0, thresholds["risk_high"] - 1.0)
        adjusted = True

    if adjusted:
        THRESHOLDS_FILE.write_text(json.dumps(thresholds, indent=2))
        logger.info("Adaptive thresholds updated: risk_high=%.1f", thresholds["risk_high"])


def register_model_version(
    model_name: str,
    version: str,
    *,
    path: Optional[str] = None,
    metrics: Optional[Dict] = None,
    set_active: bool = False,
) -> Dict[str, Any]:
    init_learning_db()
    session = get_session()
    try:
        if set_active:
            session.query(ModelVersion).filter_by(model_name=model_name).update({"active": "false"})

        rec = ModelVersion(
            id=str(uuid.uuid4()),
            model_name=model_name,
            version=version,
            path=path,
            metrics_json=json.dumps(metrics or {}),
            active="true" if set_active else "false",
        )
        session.add(rec)
        session.commit()
        return _model_dict(rec)
    finally:
        session.close()


def get_active_model(model_name: str) -> Optional[Dict[str, Any]]:
    init_learning_db()
    session = get_session()
    try:
        rec = session.query(ModelVersion).filter_by(model_name=model_name, active="true").first()
        return _model_dict(rec) if rec else None
    finally:
        session.close()


def list_model_versions(model_name: Optional[str] = None) -> List[Dict[str, Any]]:
    init_learning_db()
    session = get_session()
    try:
        q = session.query(ModelVersion)
        if model_name:
            q = q.filter_by(model_name=model_name)
        return [_model_dict(r) for r in q.order_by(ModelVersion.created_at.desc()).limit(50).all()]
    finally:
        session.close()


def get_learning_stats() -> Dict[str, Any]:
    init_learning_db()
    session = get_session()
    try:
        total_fb = session.query(InvestigationFeedback).count()
        pending = session.query(InvestigationFeedback).filter_by(used_for_training="false").count()
        models = session.query(ModelVersion).count()
        return {
            "total_feedback": total_fb,
            "pending_training": pending,
            "registered_models": models,
            "thresholds": get_adaptive_thresholds(),
        }
    finally:
        session.close()


def _feedback_dict(fb: InvestigationFeedback) -> Dict[str, Any]:
    return {
        "id": fb.id, "evidence_id": fb.evidence_id,
        "investigation_id": fb.investigation_id,
        "analyst_id": fb.analyst_id,
        "predicted_verdict": fb.predicted_verdict,
        "actual_verdict": fb.actual_verdict,
        "predicted_risk": fb.predicted_risk,
        "actual_risk": fb.actual_risk,
        "feedback_type": fb.feedback_type,
        "notes": fb.notes,
        "created_at": fb.created_at.isoformat() if fb.created_at else None,
    }


def _model_dict(rec: ModelVersion) -> Dict[str, Any]:
    return {
        "id": rec.id, "model_name": rec.model_name,
        "version": rec.version, "path": rec.path,
        "metrics": json.loads(rec.metrics_json or "{}"),
        "active": rec.active == "true",
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
    }
