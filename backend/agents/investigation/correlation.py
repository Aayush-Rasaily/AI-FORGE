"""
Evidence Correlation Engine — cross-modal inconsistency detection.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


_AMOUNT_RE = re.compile(
    r"(?:₹|rs\.?|inr|usd|\$|€|£)\s*([\d,]+(?:\.\d+)?)",
    re.IGNORECASE,
)
_AMOUNT_PLAIN = re.compile(r"\b(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d{2})\b")


def _extract_amounts(text: str) -> List[float]:
    if not text:
        return []
    vals: List[float] = []
    for m in _AMOUNT_RE.finditer(text):
        try:
            vals.append(float(m.group(1).replace(",", "")))
        except ValueError:
            pass
    if not vals:
        for m in _AMOUNT_PLAIN.finditer(text):
            try:
                vals.append(float(m.group(1).replace(",", "")))
            except ValueError:
                pass
    return vals


def _text_blob(payload: Any, _depth: int = 0) -> str:
    if payload is None or _depth > 6:
        return ""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        parts = []
        for k in ("text", "ocr_text", "full_text", "summary", "content", "extracted_text"):
            if payload.get(k):
                parts.append(str(payload[k]))
        ocr = payload.get("ocr") or payload.get("ocr_result")
        if isinstance(ocr, dict) and ocr is not payload:
            parts.append(_text_blob(ocr, _depth + 1))
        return " ".join(parts)
    return str(payload)


def correlate_evidence(
    *,
    image_data: Optional[Dict[str, Any]] = None,
    document_data: Optional[Dict[str, Any]] = None,
    metadata_data: Optional[Dict[str, Any]] = None,
    video_data: Optional[Dict[str, Any]] = None,
    signature_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Cross-validate multimodal outputs and surface inconsistencies.
    """
    inconsistencies: List[Dict[str, Any]] = []
    correlations: List[Dict[str, Any]] = []
    risk_boost = 0.0

    image_text = _text_blob((image_data or {}).get("ocr") or (image_data or {}).get("analysis"))
    doc_text = _text_blob(document_data)
    img_amounts = _extract_amounts(image_text)
    doc_amounts = _extract_amounts(doc_text)

    if img_amounts and doc_amounts:
        a, b = img_amounts[0], doc_amounts[0]
        if abs(a - b) / max(a, b, 1.0) > 0.05:
            inconsistencies.append({
                "type": "amount_mismatch",
                "severity": "critical",
                "image_amount": a,
                "document_amount": b,
                "explanation": (
                    f"Cross-modal inconsistency: image OCR reports {a} while "
                    f"document OCR reports {b}."
                ),
            })
            risk_boost += 0.18
        else:
            correlations.append({
                "type": "amount_consistent",
                "value": a,
                "explanation": "Image and document amounts agree within tolerance.",
            })

    meta = metadata_data or {}
    meta_inner = meta.get("metadata") or meta.get("exif") or meta
    edited = False
    software = ""
    if isinstance(meta_inner, dict):
        software = str(
            meta_inner.get("Software")
            or meta_inner.get("software")
            or (meta_inner.get("exif_summary") or {}).get("software")
            or ""
        )
        editing_flags = meta.get("editing_software") or meta_inner.get("editing_detected")
        if software and any(s in software.lower() for s in ("photoshop", "gimp", "snapseed", "picsart")):
            edited = True
        if editing_flags:
            edited = True

    if edited and (img_amounts or doc_amounts):
        inconsistencies.append({
            "type": "metadata_edit_with_financial_content",
            "severity": "high",
            "software": software or "unknown editor",
            "explanation": (
                "Financial amounts present while metadata indicates recent editing software."
            ),
        })
        risk_boost += 0.12

    # Hash / custody hints from metadata agent
    if meta.get("hash_mismatch"):
        inconsistencies.append({
            "type": "hash_mismatch",
            "severity": "critical",
            "explanation": "Evidence hash mismatch detected across custody records.",
        })
        risk_boost += 0.25

    sig = signature_data or {}
    if sig.get("forgery_score") is not None and float(sig.get("forgery_score", 0)) > 0.7:
        inconsistencies.append({
            "type": "signature_forgery_signal",
            "severity": "high",
            "score": sig.get("forgery_score"),
            "explanation": "Signature agent reports high forgery likelihood.",
        })
        risk_boost += 0.15

    video = video_data or {}
    if video.get("deepfake_score") is not None and float(video.get("deepfake_score", 0)) > 0.65:
        inconsistencies.append({
            "type": "video_deepfake_signal",
            "severity": "high",
            "explanation": "Video deepfake score exceeds investigation threshold.",
        })
        risk_boost += 0.14

    severity = "none"
    if any(i.get("severity") == "critical" for i in inconsistencies):
        severity = "critical"
    elif inconsistencies:
        severity = "elevated"

    return {
        "inconsistencies": inconsistencies,
        "correlations": correlations,
        "risk_boost": round(min(0.45, risk_boost), 4),
        "severity": severity,
        "cross_modal_summary": (
            f"{len(inconsistencies)} inconsistency(ies), {len(correlations)} correlation(s)."
            if inconsistencies or correlations
            else "No cross-modal conflicts detected."
        ),
    }
