"""
Detector reliability weighting — updated from benchmark + investigator feedback.

Never retrains models; only adjusts fusion confidence weights.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.engines.contracts import DETECTOR_RELIABILITY

logger = logging.getLogger("ai_forge.learning.weighting")

LEARNING_DIR = Path("data/learning")
WEIGHTS_FILE = LEARNING_DIR / "detector_weights.json"
WEIGHT_HISTORY_FILE = LEARNING_DIR / "weight_history.jsonl"

ALPHA = 0.08  # EMA learning rate for feedback
MIN_RELIABILITY = 0.50
MAX_RELIABILITY = 0.99


def _ensure() -> None:
    LEARNING_DIR.mkdir(parents=True, exist_ok=True)
    if not WEIGHTS_FILE.exists():
        normalized = {
            k.lower(): round(max(MIN_RELIABILITY, min(MAX_RELIABILITY, float(v))), 4)
            for k, v in DETECTOR_RELIABILITY.items()
        }
        payload = {
            "weights": normalized,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "source": "default",
        }
        WEIGHTS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_detector_weights() -> Dict[str, float]:
    _ensure()
    try:
        data = json.loads(WEIGHTS_FILE.read_text(encoding="utf-8"))
        weights = data.get("weights") or data
        if isinstance(weights, dict):
            merged = dict(DETECTOR_RELIABILITY)
            for k, v in weights.items():
                merged[str(k).lower()] = round(max(MIN_RELIABILITY, min(MAX_RELIABILITY, float(v))), 4)
            return merged
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        pass
    return dict(DETECTOR_RELIABILITY)


def save_detector_weights(weights: Dict[str, float], *, source: str = "manual") -> Dict[str, float]:
    LEARNING_DIR.mkdir(parents=True, exist_ok=True)
    normalized = {
        k.lower(): round(max(MIN_RELIABILITY, min(MAX_RELIABILITY, float(v))), 4)
        for k, v in weights.items()
    }
    payload = {
        "weights": normalized,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
    }
    WEIGHTS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with open(WEIGHT_HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": payload["updated_at"], "source": source, "weights": normalized}) + "\n")
    return normalized


def get_detector_reliability(detector_name: str) -> float:
    name = str(detector_name).strip().lower().replace(" ", "_")
    weights = load_detector_weights()
    return weights.get(name, DETECTOR_RELIABILITY.get(name, 0.65))


def apply_reliability_to_detectors(detectors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Attach learned reliability to detector output dicts."""
    out = []
    for d in detectors:
        name = str(d.get("detector_name", "")).lower()
        out.append({**d, "reliability": get_detector_reliability(name)})
    return out


def update_from_feedback(
    detector_name: str,
    *,
    correct: bool,
    evidence_id: Optional[str] = None,
) -> float:
    """
    EMA update for one detector after investigator feedback.
    correct=True nudges reliability up; False nudges down.
    """
    name = str(detector_name).strip().lower().replace(" ", "_")
    weights = load_detector_weights()
    old = weights.get(name, DETECTOR_RELIABILITY.get(name, 0.65))
    target = 0.98 if correct else 0.55
    new = old * (1 - ALPHA) + target * ALPHA
    weights[name] = round(max(MIN_RELIABILITY, min(MAX_RELIABILITY, new)), 4)
    save_detector_weights(weights, source=f"feedback:{evidence_id or 'unknown'}")
    logger.info(
        "detector_weight_updated | %s | %.4f -> %.4f | correct=%s",
        name, old, weights[name], correct,
    )
    return weights[name]


def update_from_case_feedback(
    elevated_detectors: List[str],
    *,
    correct: bool,
    evidence_id: Optional[str] = None,
) -> Dict[str, float]:
    """Update all elevated detectors that contributed to a case verdict."""
    updated = {}
    for name in elevated_detectors:
        updated[name] = update_from_feedback(name, correct=correct, evidence_id=evidence_id)
    return updated


def merge_benchmark_metrics(
    per_detector_metrics: Dict[str, Dict[str, float]],
) -> Dict[str, float]:
    """
    Blend benchmark accuracy into weights (small influence — no model retrain).
    reliability = 0.85 * current + 0.15 * benchmark_accuracy
    """
    weights = load_detector_weights()
    for name, metrics in per_detector_metrics.items():
        acc = float(metrics.get("accuracy") or metrics.get("f1_score") or 0.5)
        old = weights.get(name, DETECTOR_RELIABILITY.get(name, 0.65))
        blended = old * 0.85 + acc * 0.15
        weights[name] = round(max(MIN_RELIABILITY, min(MAX_RELIABILITY, blended)), 4)
    save_detector_weights(weights, source="benchmark")
    return weights


def weight_summary() -> Dict[str, Any]:
    weights = load_detector_weights()
    if not weights:
        return {"most_reliable": None, "weakest": None, "weights": {}}
    ranked = sorted(weights.items(), key=lambda x: x[1], reverse=True)
    return {
        "weights": weights,
        "most_reliable": {"detector": ranked[0][0], "reliability": ranked[0][1]},
        "weakest": {"detector": ranked[-1][0], "reliability": ranked[-1][1]},
        "count": len(weights),
    }
