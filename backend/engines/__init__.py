"""
AI-FORGE production forensic engines.

Pipeline: Detectors → Evidence Fusion → Localization → Cite-only Explain → Jury/Reports
"""

from backend.engines.contracts import (
    DETECTOR_RELIABILITY,
    DetectorOutput,
    FusionResult,
    make_detector_output,
)
from backend.engines.fusion_engine import fuse_detector_outputs
from backend.engines.reasoning_engine import run_forensic_reasoning, build_reasoning_narrative, save_forensic_reasoning
from backend.engines.explain_engine import (
    build_cited_explanation,
    build_explainable_ai,
    build_reasoning_explanation,
    load_explainable_ai,
    save_explainable_ai,
)
from backend.engines.orchestrator import enrich_analysis_with_engines
from backend.engines.adapters import collect_detector_outputs

__all__ = [
    "DETECTOR_RELIABILITY",
    "DetectorOutput",
    "FusionResult",
    "make_detector_output",
    "fuse_detector_outputs",
    "build_cited_explanation",
    "build_reasoning_explanation",
    "build_explainable_ai",
    "load_explainable_ai",
    "save_explainable_ai",
    "run_forensic_reasoning",
    "build_reasoning_narrative",
    "enrich_analysis_with_engines",
    "collect_detector_outputs",
]
