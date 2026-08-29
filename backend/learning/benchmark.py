"""
Benchmark datasets and continuous evaluation for forensic detectors.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.learning.metrics import compute_metrics, compute_roc_curve, scores_to_binary
from backend.learning.weighting import merge_benchmark_metrics

logger = logging.getLogger("ai_forge.learning.benchmark")

BENCHMARK_ROOT = Path("data/benchmark")
RESULTS_FILE = Path("data/learning/benchmark_results.json")

DATASET_TYPES = ("image", "document", "video", "signature")


def _ensure_datasets() -> None:
    BENCHMARK_ROOT.mkdir(parents=True, exist_ok=True)
    for dtype in DATASET_TYPES:
        ddir = BENCHMARK_ROOT / dtype
        ddir.mkdir(parents=True, exist_ok=True)
        manifest = ddir / "manifest.json"
        if not manifest.is_file():
            manifest.write_text(
                json.dumps(_default_manifest(dtype), indent=2),
                encoding="utf-8",
            )


def _default_manifest(dataset_type: str) -> Dict[str, Any]:
    """Seed benchmark manifests — modular; extend with real labeled files."""
    common = {
        "dataset": dataset_type,
        "version": "1.0",
        "description": f"AI-FORGE {dataset_type} forensic benchmark dataset",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if dataset_type == "image":
        samples = [
            {"id": "bench-img-001", "label": "tampered", "ground_truth": 1, "evidence_id": "EVID-0149", "note": "ELA+copy-move elevated"},
            {"id": "bench-img-002", "label": "authentic", "ground_truth": 0, "evidence_id": None, "note": "Clean reference — link evidence_id when available"},
            {"id": "bench-img-003", "label": "tampered", "ground_truth": 1, "evidence_id": "EVID-0163", "note": "Localized manipulation"},
        ]
    elif dataset_type == "document":
        samples = [
            {"id": "bench-doc-001", "label": "tampered", "ground_truth": 1, "evidence_id": None, "note": "Invoice amount edit"},
            {"id": "bench-doc-002", "label": "authentic", "ground_truth": 0, "evidence_id": None, "note": "Unmodified PDF"},
        ]
    elif dataset_type == "video":
        samples = [
            {"id": "bench-vid-001", "label": "tampered", "ground_truth": 1, "evidence_id": None, "note": "Frame splice"},
            {"id": "bench-vid-002", "label": "authentic", "ground_truth": 0, "evidence_id": None, "note": "Camera original"},
        ]
    else:  # signature
        samples = [
            {"id": "bench-sig-001", "label": "forged", "ground_truth": 1, "evidence_id": None, "note": "Forged signature"},
            {"id": "bench-sig-002", "label": "authentic", "ground_truth": 0, "evidence_id": None, "note": "Genuine signature"},
        ]
    return {**common, "samples": samples}


def list_datasets() -> List[Dict[str, Any]]:
    _ensure_datasets()
    out = []
    for dtype in DATASET_TYPES:
        manifest = load_manifest(dtype)
        out.append({
            "type": dtype,
            "version": manifest.get("version"),
            "sample_count": len(manifest.get("samples") or []),
            "path": str(BENCHMARK_ROOT / dtype / "manifest.json"),
        })
    return out


def load_manifest(dataset_type: str) -> Dict[str, Any]:
    _ensure_datasets()
    path = BENCHMARK_ROOT / dataset_type / "manifest.json"
    if not path.is_file():
        return _default_manifest(dataset_type)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _default_manifest(dataset_type)


def _load_analysis(evidence_id: str) -> Dict[str, Any]:
    from backend.evidence.paths import get_analysis_dir

    for adir in (get_analysis_dir(evidence_id, create=False), Path("data/temp/uploads/analysis") / evidence_id):
        for fname in ("analysis.json", "document_analysis.json", "video_analysis.json"):
            p = adir / fname
            if p.is_file():
                try:
                    return json.loads(p.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    pass
    return {}


def _evaluate_sample(sample: Dict[str, Any], dataset_type: str) -> Optional[Dict[str, Any]]:
    """Evaluate one benchmark sample using live analysis when evidence_id exists."""
    eid = sample.get("evidence_id")
    gt = int(sample.get("ground_truth", 1 if sample.get("label") in ("tampered", "forged", "fake") else 0))

    if not eid:
        return {
            "sample_id": sample.get("id"),
            "ground_truth": gt,
            "skipped": True,
            "reason": "No evidence_id linked — add evidence_id to manifest sample",
        }

    analysis = _load_analysis(eid)
    if not analysis:
        return {
            "sample_id": sample.get("id"),
            "evidence_id": eid,
            "ground_truth": gt,
            "skipped": True,
            "reason": "Analysis not found for evidence_id",
        }

    try:
        from backend.engines.adapters import collect_detector_outputs
        from backend.engines.fusion_engine import fuse_detector_outputs
        from backend.learning.weighting import apply_reliability_to_detectors

        detectors = apply_reliability_to_detectors(collect_detector_outputs(analysis))
        fusion = fuse_detector_outputs(detectors)
    except Exception as exc:
        return {
            "sample_id": sample.get("id"),
            "evidence_id": eid,
            "ground_truth": gt,
            "skipped": True,
            "reason": str(exc)[:200],
        }

    risk = float(fusion.get("overall_score") or analysis.get("risk_score") or 0)
    if risk <= 1:
        risk *= 100
    pred = 1 if risk >= 50 else 0
    score01 = risk / 100.0

    det_scores: Dict[str, float] = {}
    for d in detectors:
        if d.get("status") == "ok":
            det_scores[str(d.get("detector_name", "")).lower()] = float(d.get("score") or 0)

    return {
        "sample_id": sample.get("id"),
        "evidence_id": eid,
        "dataset_type": dataset_type,
        "ground_truth": gt,
        "predicted": pred,
        "risk_score": round(risk, 2),
        "score": round(score01, 4),
        "verdict": fusion.get("verdict"),
        "detector_scores": det_scores,
        "skipped": False,
    }


def run_benchmark(
    dataset_type: Optional[str] = None,
    *,
    threshold: float = 0.5,
) -> Dict[str, Any]:
    """Run benchmark evaluation on one or all dataset types."""
    _ensure_datasets()
    types = [dataset_type] if dataset_type else list(DATASET_TYPES)
    all_results: Dict[str, Any] = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "datasets": {},
        "system": {},
        "per_detector": {},
    }

    y_true: List[int] = []
    y_scores: List[float] = []
    per_det: Dict[str, Dict[str, List]] = {}

    for dtype in types:
        manifest = load_manifest(dtype)
        samples = manifest.get("samples") or []
        evaluated = []
        for sample in samples:
            ev = _evaluate_sample(sample, dtype)
            if ev and not ev.get("skipped"):
                evaluated.append(ev)
                y_true.append(int(ev["ground_truth"]))
                y_scores.append(float(ev["score"]))
                pred_det = 1 if ev["score"] >= threshold else 0
                for name, sc in (ev.get("detector_scores") or {}).items():
                    bucket = per_det.setdefault(name, {"y_true": [], "y_pred": [], "y_scores": []})
                    bucket["y_true"].append(int(ev["ground_truth"]))
                    bucket["y_pred"].append(1 if sc >= threshold else 0)
                    bucket["y_scores"].append(float(sc))

        ds_metrics = compute_metrics(
            [e["ground_truth"] for e in evaluated],
            [e["predicted"] for e in evaluated],
            threshold=threshold,
        ) if evaluated else {}
        ds_roc = compute_roc_curve(
            [e["ground_truth"] for e in evaluated],
            [e["score"] for e in evaluated],
        ) if evaluated else {"points": [], "auc": 0.0}

        all_results["datasets"][dtype] = {
            "sample_count": len(samples),
            "evaluated_count": len(evaluated),
            "metrics": ds_metrics,
            "roc": ds_roc,
            "samples": evaluated,
        }

    system_metrics = compute_metrics(y_true, scores_to_binary(y_scores, threshold), threshold=threshold)
    system_roc = compute_roc_curve(y_true, y_scores)
    all_results["system"] = {
        "metrics": system_metrics,
        "roc": system_roc,
        "evaluated_samples": len(y_true),
    }

    per_detector_metrics: Dict[str, Dict[str, float]] = {}
    for name, bucket in per_det.items():
        if bucket["y_true"]:
            per_detector_metrics[name] = compute_metrics(
                bucket["y_true"], bucket["y_pred"], threshold=threshold,
            )

    all_results["per_detector"] = per_detector_metrics
    if per_detector_metrics:
        merge_benchmark_metrics(per_detector_metrics)

    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_FILE.write_text(json.dumps(all_results, indent=2, default=str), encoding="utf-8")
    logger.info("benchmark_complete | evaluated=%s datasets=%s", len(y_true), types)
    return all_results


def load_benchmark_results() -> Dict[str, Any]:
    if not RESULTS_FILE.is_file():
        return {}
    try:
        return json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
