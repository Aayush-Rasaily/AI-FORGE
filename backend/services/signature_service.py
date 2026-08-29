"""Production adapter for the existing signature forensic detector.

This module does not implement another detector.  It connects the existing
``analysis.signature_forensics.analyze_signatures`` detector to the normal
image pipeline and gives its output a stable contract for the dossier,
canonical findings, and API consumers.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from backend.analysis.signature_forensics import analyze_signatures

logger = logging.getLogger("ai_forge.signature_service")


def _label_for_classification(classification: str) -> str:
    value = classification.lower().strip()
    labels = {
        "genuine": "Original handwritten signature",
        "pasted": "Pasted signature",
        "copied": "Copied signature",
        "transparent png": "Digitally inserted signature",
        "overwritten": "Overwritten signature",
        "blended": "Blended signature",
        "rescaled": "Rescaled signature",
        "rotated": "Rotated signature",
        "edge inconsistency": "Suspicious signature",
        "pressure inconsistency": "Suspicious signature",
    }
    return labels.get(value, "Suspicious signature")


def _severity(classification: str, confidence: float) -> str:
    if classification.lower().strip() == "genuine":
        return "low"
    if confidence >= 0.9:
        return "high"
    return "medium"


def _bbox(raw_bbox: Any) -> List[int]:
    if not isinstance(raw_bbox, (list, tuple)) or len(raw_bbox) < 4:
        return [0, 0, 0, 0]
    return [max(0, int(float(value))) for value in raw_bbox[:4]]


def _finding(raw: Dict[str, Any], index: int) -> Dict[str, Any]:
    classification = str(raw.get("classification") or "suspicious").strip()
    try:
        confidence = max(0.0, min(1.0, float(raw.get("confidence", 0.0))))
    except (TypeError, ValueError):
        confidence = 0.0
    x, y, width, height = _bbox(raw.get("bbox"))
    label = _label_for_classification(classification)
    explanation = str(raw.get("reason") or "Signature-region analysis completed.")
    if classification.lower() == "genuine":
        human_summary = (
            "An original handwritten signature was detected. "
            "The available stroke and background checks did not flag an alteration."
        )
    else:
        human_summary = (
            f"{label} detected. The existing signature detector observed "
            f"{explanation.rstrip('.') }."
        )
    polygon = [[x, y], [x + width, y], [x + width, y + height], [x, y + height]]
    return {
        "id": f"SIG-{index:03d}",
        "type": "signature",
        "label": label,
        "confidence": round(confidence, 4),
        "bbox": [x, y, width, height],
        "polygon": polygon,
        "severity": _severity(classification, confidence),
        "explanation": explanation,
        "human_summary": human_summary,
        "classification": classification,
        "detector": "existing_signature_forensics",
    }


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary.replace(path)


def update_forensic_dossier(
    analysis_dir: Path,
    result: Dict[str, Any],
    *,
    section: str = "signature_analysis",
) -> None:
    """Merge signature output into the existing dossier without discarding it."""
    dossier_path = Path(analysis_dir) / "forensic_dossier.json"
    dossier: Dict[str, Any] = {}
    if dossier_path.is_file():
        try:
            existing = json.loads(dossier_path.read_text(encoding="utf-8"))
            dossier = {"findings": existing} if isinstance(existing, list) else (
                existing if isinstance(existing, dict) else {}
            )
        except (OSError, json.JSONDecodeError):
            logger.warning("Could not read existing forensic dossier: %s", dossier_path)
    dossier["schema_version"] = dossier.get("schema_version", "1.0")
    dossier[section] = result
    _write_json(dossier_path, dossier)


def run_signature_analysis(
    image_path: str | Path,
    analysis_dir: str | Path,
) -> Dict[str, Any]:
    """Run the existing detector and persist its structured result."""
    analysis_dir = Path(analysis_dir)
    try:
        raw_findings = analyze_signatures(str(image_path), str(analysis_dir))
        raw_findings = raw_findings if isinstance(raw_findings, list) else []
        findings = [
            _finding(raw, index)
            for index, raw in enumerate(raw_findings, start=1)
            if isinstance(raw, dict)
        ]
        confidence = max((item["confidence"] for item in findings), default=0.0)
        labels = list(dict.fromkeys(item["label"] for item in findings))
        result: Dict[str, Any] = {
            "status": "completed",
            "available": True,
            "detector": "existing_signature_forensics",
            "signature_present": bool(findings),
            "signature_count": len(findings),
            "signature_regions": findings,
            "signature_confidence": round(confidence, 4),
            "signature_type": labels[0] if len(labels) == 1 else (
                "Multiple signature types" if labels else None
            ),
            "findings": findings,
            "raw_findings": raw_findings,
        }
    except Exception as exc:
        logger.exception("Signature detector failed for %s", image_path)
        result = {
            "status": "failed",
            "available": False,
            "detector": "existing_signature_forensics",
            "signature_present": False,
            "signature_count": 0,
            "signature_regions": [],
            "signature_confidence": 0.0,
            "signature_type": None,
            "findings": [],
            "error": str(exc),
        }

    _write_json(analysis_dir / "signature_analysis.json", result)
    update_forensic_dossier(analysis_dir, result)
    return result


__all__ = ["run_signature_analysis", "update_forensic_dossier"]
