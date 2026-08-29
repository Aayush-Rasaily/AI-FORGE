"""
Learning dashboard aggregates — system accuracy, monthly performance, detector ranks.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from backend.learning.benchmark import load_benchmark_results
from backend.learning.weighting import load_detector_weights, weight_summary

FEEDBACK_LOG = Path("data/learning/detector_feedback.jsonl")


def _monthly_feedback_stats() -> List[Dict[str, Any]]:
    if not FEEDBACK_LOG.is_file():
        return []
    by_month: Dict[str, Dict[str, int]] = defaultdict(lambda: {"correct": 0, "wrong": 0, "total": 0})
    try:
        for line in FEEDBACK_LOG.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            ts = str(rec.get("created_at", ""))[:7]  # YYYY-MM
            if not ts:
                continue
            by_month[ts]["total"] += 1
            if rec.get("correct"):
                by_month[ts]["correct"] += 1
            else:
                by_month[ts]["wrong"] += 1
    except (json.JSONDecodeError, OSError):
        pass
    months = sorted(by_month.keys())[-12:]
    return [
        {
            "month": m,
            "total": by_month[m]["total"],
            "correct": by_month[m]["correct"],
            "wrong": by_month[m]["wrong"],
            "accuracy": round(
                by_month[m]["correct"] / by_month[m]["total"], 4,
            ) if by_month[m]["total"] else 0.0,
        }
        for m in months
    ]


def get_evaluation_dashboard() -> Dict[str, Any]:
    """Dashboard payload for benchmark + continuous learning UI."""
    bench = load_benchmark_results()
    weights_info = weight_summary()
    system = bench.get("system") or {}
    metrics = system.get("metrics") or {}

    total_feedback = 0
    if FEEDBACK_LOG.is_file():
        try:
            total_feedback = sum(
                1 for line in FEEDBACK_LOG.read_text(encoding="utf-8").splitlines() if line.strip()
            )
        except OSError:
            pass

    thresholds: Dict[str, Any] = {}
    try:
        from backend.learning.engine import get_adaptive_thresholds
        thresholds = get_adaptive_thresholds()
    except Exception:
        pass

    avg_conf = 0.0
    conf_n = 0
    for ds in (bench.get("datasets") or {}).values():
        for s in ds.get("samples") or []:
            if s.get("risk_score") is not None:
                avg_conf += float(s["risk_score"])
                conf_n += 1
    if conf_n:
        avg_conf = round(avg_conf / conf_n, 2)

    return {
        "overall_system_accuracy": metrics.get("accuracy", 0.0),
        "average_confidence": avg_conf,
        "precision": metrics.get("precision", 0.0),
        "recall": metrics.get("recall", 0.0),
        "f1_score": metrics.get("f1_score", 0.0),
        "false_positive_rate": metrics.get("false_positive_rate", 0.0),
        "false_negative_rate": metrics.get("false_negative_rate", 0.0),
        "roc_auc": (system.get("roc") or {}).get("auc", 0.0),
        "roc_curve": (system.get("roc") or {}).get("points", []),
        "most_reliable_detector": weights_info.get("most_reliable"),
        "weakest_detector": weights_info.get("weakest"),
        "detector_weights": weights_info.get("weights") or load_detector_weights(),
        "per_detector_metrics": bench.get("per_detector") or {},
        "monthly_performance": _monthly_feedback_stats(),
        "benchmark_last_run": bench.get("run_at"),
        "benchmark_datasets": bench.get("datasets") or {},
        "total_feedback": total_feedback,
        "learning_thresholds": thresholds,
    }
