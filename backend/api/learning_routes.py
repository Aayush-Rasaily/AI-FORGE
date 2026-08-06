"""Learning AI API — feedback, thresholds, model versioning."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from backend.forensics.user_context import get_investigator
from backend.learning.engine import (
    get_active_model,
    get_adaptive_thresholds,
    get_learning_stats,
    list_model_versions,
    register_model_version,
    submit_feedback,
)

router = APIRouter(prefix="/api/learning", tags=["Learning AI"])


class FeedbackBody(BaseModel):
    evidence_id: str
    actual_verdict: str
    predicted_verdict: Optional[str] = None
    predicted_risk: Optional[float] = None
    actual_risk: Optional[float] = None
    investigation_id: Optional[str] = None
    notes: Optional[str] = None
    feedback_type: str = "correction"


class ModelVersionBody(BaseModel):
    model_name: str
    version: str
    path: Optional[str] = None
    metrics: Optional[dict] = None
    set_active: bool = False


@router.get("/stats")
async def learning_stats():
    return {"success": True, **get_learning_stats()}


@router.get("/thresholds")
async def adaptive_thresholds():
    return {"success": True, "thresholds": get_adaptive_thresholds()}


@router.post("/feedback")
async def post_feedback(request: Request, body: FeedbackBody):
    inv = get_investigator(request)
    result = submit_feedback(
        body.evidence_id,
        body.actual_verdict,
        analyst_id=inv.user_id,
        predicted_verdict=body.predicted_verdict,
        predicted_risk=body.predicted_risk,
        actual_risk=body.actual_risk,
        investigation_id=body.investigation_id,
        notes=body.notes,
        feedback_type=body.feedback_type,
    )
    return {"success": True, "feedback": result, "thresholds": get_adaptive_thresholds()}


@router.get("/models")
async def list_models(model_name: Optional[str] = None):
    return {"success": True, "models": list_model_versions(model_name)}


@router.get("/models/{model_name}/active")
async def active_model(model_name: str):
    model = get_active_model(model_name)
    return {"success": True, "model": model}


@router.post("/models")
async def post_model_version(body: ModelVersionBody):
    result = register_model_version(
        body.model_name, body.version,
        path=body.path, metrics=body.metrics, set_active=body.set_active,
    )
    return {"success": True, "model": result}
