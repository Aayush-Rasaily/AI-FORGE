"""Learning AI — feedback, benchmark, detector weighting."""

from backend.learning.benchmark import list_datasets, load_benchmark_results, run_benchmark
from backend.learning.dashboard import get_evaluation_dashboard
from backend.learning.metrics import compute_metrics, compute_roc_curve
from backend.learning.weighting import get_detector_reliability, load_detector_weights

__all__ = [
    "run_benchmark",
    "list_datasets",
    "load_benchmark_results",
    "get_evaluation_dashboard",
    "get_detector_reliability",
    "load_detector_weights",
    "compute_metrics",
    "compute_roc_curve",
]
