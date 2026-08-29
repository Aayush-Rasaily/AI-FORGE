"""Reference/query signature comparison using the existing inference model."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import cv2

from backend.evidence.paths import get_analysis_dir
from backend.models.signature.inference import verify_signature
from backend.services.signature_service import update_forensic_dossier

logger = logging.getLogger("ai_forge.signature_comparison")


def _image_bbox(path: str | Path) -> List[int]:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Unable to read signature image: {path}")
    height, width = image.shape[:2]
    return [0, 0, int(width), int(height)]


def _verdict(similarity: float, forgery_probability: float) -> str:
    if forgery_probability >= 0.75 and similarity < 0.45:
        return "Different Writer"
    if forgery_probability >= 0.65:
        return "Forgery Suspected"
    if forgery_probability >= 0.45:
        return "Suspicious"
    if similarity >= 0.85:
        return "Genuine Match"
    if similarity >= 0.70:
        return "Highly Similar"
    if similarity >= 0.50:
        return "Possible Match"
    return "Different Writer"


def _reason(
    similarity: float,
    forgery_probability: float,
    raw: Dict[str, Any],
) -> str:
    stroke = float(raw.get("stroke_difference") or 0.0)
    shape = float(raw.get("shape_difference") or 0.0)
    curvature = float(raw.get("curvature_difference") or 0.0)
    if forgery_probability >= 0.65:
        return (
            "Stroke structure differs significantly although the overall appearance "
            f"is {similarity:.1%} similar (stroke difference {stroke:.2f}, "
            f"shape difference {shape:.2f}, curvature difference {curvature:.2f})."
        )
    if similarity >= 0.70:
        return (
            "The compared signatures share substantial visual and embedding "
            f"similarity ({similarity:.1%}); the measured stroke and contour "
            "differences should be reviewed against an authenticated specimen."
        )
    return (
        "The compared signatures have limited measured similarity based on their "
        f"contours, stroke overlap, curvature, and embedding score ({similarity:.1%})."
    )


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary.replace(path)


def compare_signatures(
    reference_path: str | Path,
    questioned_path: str | Path,
    *,
    evidence_id: str | None = None,
    analysis_dir: str | Path | None = None,
) -> Dict[str, Any]:
    """Run the existing Siamese/OpenCV comparison and persist its evidence."""
    result = verify_signature(
        str(reference_path),
        str(questioned_path),
        output_dir=analysis_dir,
    )
    similarity = float(result.get("siamese_similarity", result.get("similarity", 0.0)))
    forgery_probability = float(result.get("forgery_probability", 0.0))
    confidence = float(result.get("confidence", 0.0))
    questioned_bbox = _image_bbox(questioned_path)
    reference_bbox = _image_bbox(reference_path)
    verdict = _verdict(similarity, forgery_probability)
    raw_forensics = {
        "stroke_difference": result.get("stroke_difference"),
        "shape_difference": result.get("shape_difference"),
        "curvature_difference": result.get("curvature_difference"),
    }

    comparison: Dict[str, Any] = {
        "id": f"SIG-V-{evidence_id or 'comparison'}",
        "type": "signature_verification",
        "similarity_score": round(similarity * 100.0, 1),
        "confidence": round(max(0.0, min(1.0, confidence)), 4),
        "verdict": verdict,
        "reason": _reason(similarity, forgery_probability, raw_forensics),
        "matched_regions": result.get("matched_regions") or [],
        "different_regions": result.get("different_regions") or [],
        "reference_bbox": reference_bbox,
        "questioned_bbox": questioned_bbox,
        "forgery_probability": round(forgery_probability, 4),
        "stroke_difference": result.get("stroke_difference"),
        "pressure_difference": result.get("pressure_difference"),
        "shape_difference": result.get("shape_difference"),
        "curvature_difference": result.get("curvature_difference"),
        "visualizations": result.get("visualizations") or {},
        "signature_present": True,
        "signature_count": 1,
        "signature_type": verdict,
    }

    if evidence_id:
        output_dir = Path(analysis_dir or get_analysis_dir(evidence_id))
        _write_json(output_dir / "signature_verification.json", comparison)
        update_forensic_dossier(
            output_dir,
            comparison,
            section="signature_verification",
        )
    return comparison


__all__ = ["compare_signatures"]
