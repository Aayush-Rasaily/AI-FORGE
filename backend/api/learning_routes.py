"""Learning AI API — feedback, benchmark, thresholds, model versioning."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from backend.forensics.user_context import get_investigator
from backend.learning.benchmark import list_datasets, load_benchmark_results, run_benchmark
from backend.learning.dashboard import get_evaluation_dashboard
from backend.learning.engine import (
    get_active_model,
    get_adaptive_thresholds,
    get_learning_stats,
    list_model_versions,
    register_model_version,
    submit_detector_feedback,
    submit_feedback,
)
from backend.learning.weighting import load_detector_weights, weight_summary

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


class DetectorFeedbackBody(BaseModel):
    evidence_id: str
    correct: bool = Field(..., description="True = Correct, False = Wrong")
    predicted_verdict: Optional[str] = None
    predicted_risk: Optional[float] = None
    notes: Optional[str] = None


class ModelVersionBody(BaseModel):
    model_name: str
    version: str
    path: Optional[str] = None
    metrics: Optional[dict] = None
    set_active: bool = False


@router.get("/stats")
async def learning_stats():
    return {"success": True, **get_learning_stats()}


@router.get("/evaluation")
async def evaluation_dashboard():
    """Benchmark + continuous learning dashboard metrics."""
    return {"success": True, **get_evaluation_dashboard()}


@router.get("/weights")
async def detector_weights():
    return {"success": True, **weight_summary()}


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


@router.post("/detector-feedback")
async def post_detector_feedback(request: Request, body: DetectorFeedbackBody):
    """Investigator ✓ Correct / ✗ Wrong — updates fusion weights only."""
    inv = get_investigator(request)
    result = submit_detector_feedback(
        body.evidence_id,
        correct=body.correct,
        analyst_id=inv.user_id,
        predicted_verdict=body.predicted_verdict,
        predicted_risk=body.predicted_risk,
        notes=body.notes,
    )
    return {
        "success": True,
        "feedback": result,
        "weights": load_detector_weights(),
        "message": "Detector fusion weights updated. Models were not retrained.",
    }


@router.get("/benchmark/datasets")
async def benchmark_datasets():
    return {"success": True, "datasets": list_datasets()}


@router.get("/benchmark/results")
async def benchmark_results():
    return {"success": True, "results": load_benchmark_results()}


@router.post("/benchmark/run")
async def benchmark_run(dataset_type: Optional[str] = None):
    results = run_benchmark(dataset_type)
    return {"success": True, "results": results}


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
