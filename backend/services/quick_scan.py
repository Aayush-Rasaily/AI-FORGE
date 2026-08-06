"""
Stage 1 Quick Scan — target <2 seconds.

Runs lightweight checks before expensive deep forensic modules:
  - Metadata
  - Resolution / file stats
  - Content hash
  - Basic texture (edge density on thumbnail)
  - Text presence heuristic
  - Rule-based risk signals
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

import cv2
import numpy as np

from backend.analysis.metadata_analysis import analyze_metadata
from backend.utils.file_hash import compute_file_hash
from backend.utils.module_registry import likely_contains_text
from backend.utils.timing import ModuleTimer

logger = logging.getLogger("ai_forge.quick_scan")

# Below this risk → skip deep scan (high confidence authentic)
AUTHENTIC_THRESHOLD = 0.22
# Above this → always deep scan
SUSPICIOUS_THRESHOLD = 0.38


def run_quick_scan(image_path: Path) -> Dict[str, Any]:
    """Execute quick scan and decide if deep scan is required."""
    timer = ModuleTimer("Quick Scan")
    image_path = Path(image_path)

    with timer.track("hash"):
        file_hash = compute_file_hash(image_path)

    with timer.track("metadata"):
        metadata = analyze_metadata(str(image_path)) or {}

    with timer.track("texture"):
        texture = _basic_texture_analysis(str(image_path))

    with timer.track("text_detect"):
        has_text = likely_contains_text(str(image_path))

    signals: Dict[str, Any] = {
        "file_hash": file_hash,
        "resolution": texture.get("resolution"),
        "metadata_suspicious": bool(metadata.get("suspicious")),
        "software_detected": bool(metadata.get("software_detected")),
        "edge_density": texture.get("edge_density", 0),
        "brightness": texture.get("brightness", 0),
        "text_detected": has_text,
    }

    risk_score = _compute_quick_risk(signals, metadata)
    confidence = _compute_confidence(signals)

    authentic_likely = risk_score < AUTHENTIC_THRESHOLD
    needs_deep_scan = risk_score >= SUSPICIOUS_THRESHOLD or signals.get("metadata_suspicious")

    # Borderline zone — run deep scan for safety
    if not authentic_likely and not needs_deep_scan:
        needs_deep_scan = True

    timing = timer.log_summary()

    return {
        "stage": "quick_scan",
        "risk_score": round(risk_score, 4),
        "confidence": round(confidence, 4),
        "authentic_likely": authentic_likely,
        "needs_deep_scan": needs_deep_scan,
        "signals": signals,
        "metadata": metadata,
        "timing": timing,
    }


def _basic_texture_analysis(image_path: str) -> Dict[str, Any]:
    """Fast texture stats on 320px thumbnail — no disk writes."""
    img = cv2.imread(image_path)
    if img is None:
        return {"edge_density": 0, "brightness": 0, "resolution": [0, 0]}

    h, w = img.shape[:2]
    scale = 320 / max(h, w)
    if scale < 1:
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    edge_density = float(np.count_nonzero(edges)) / edges.size
    brightness = float(np.mean(gray))

    return {
        "edge_density": round(edge_density, 4),
        "brightness": round(brightness, 2),
        "resolution": [w, h],
    }


def _compute_quick_risk(signals: Dict[str, Any], metadata: Dict[str, Any]) -> float:
    risk = 0.0
    if signals.get("metadata_suspicious"):
        risk += 0.35
    if signals.get("software_detected"):
        risk += 0.25
    if signals.get("edge_density", 0) > 0.15:
        risk += 0.15
    if metadata.get("suspicion_score"):
        risk += float(metadata.get("suspicion_score", 0)) * 0.3
    return min(1.0, risk)


def _compute_confidence(signals: Dict[str, Any]) -> float:
    factors = sum([
        1 if signals.get("resolution", [0, 0])[0] > 0 else 0,
        1 if "edge_density" in signals else 0,
        1 if signals.get("file_hash") else 0,
    ])
    return min(0.95, 0.5 + factors * 0.15)


def build_quick_verdict(quick: Dict[str, Any]) -> Dict[str, Any]:
    """Build API-compatible analysis payload from quick scan only."""
    risk = quick["risk_score"] * 100
    if risk >= 45:
        verdict = "MEDIUM RISK - SUSPICIOUS"
    elif risk >= 20:
        verdict = "LOW RISK - MINOR ANOMALIES"
    else:
        verdict = "NO SIGNIFICANT ANOMALY DETECTED"

    return {
        "verdict": verdict,
        "forensic_score": round(quick["risk_score"], 4),
        "risk_score": round(risk, 2),
        "confidence": round(quick["confidence"] * 100, 2),
        "recommendation": (
            "Quick scan found no strong manipulation indicators. "
            "Deep forensic modules were skipped for performance."
            if quick["authentic_likely"]
            else "Quick scan flagged anomalies. Run deep scan for full report."
        ),
        "signals": quick["signals"],
        "findings": [],
        "scan_mode": "quick",
        "deep_scan_available": True,
        "artifacts_pending": True,
    }
