"""Turn supported analysis outputs into investigator-readable findings.

This module does not invent evidence. It only rephrases existing fields
into language that answers: what is suspicious, where, what appears to
have changed, why, and what observation supports the conclusion.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

_TITLE_BY_TYPE = (
    ("signature_insert", "Signature appears digitally inserted."),
    ("signature_pasted", "Signature appears digitally inserted."),
    ("signature_forg", "Signature region shows characteristics inconsistent with surrounding content."),
    ("signature", "Signature region shows characteristics inconsistent with surrounding content."),
    ("logo_replac", "Company logo appears to have been replaced."),
    ("logo_insert", "Company logo appears to have been inserted after document creation."),
    ("logo", "Company logo appears inconsistent with surrounding document content."),
    ("amount", "Financial value appears to have been modified."),
    ("invoice", "Invoice amount appears to have been modified."),
    ("price", "Price or amount appears to have been modified."),
    ("transaction", "Transaction amount appears to have been modified."),
    ("character_insertion", "A financial or numeric value appears to have been modified."),
    ("numeric_anomaly", "A numeric value shows characteristics inconsistent with surrounding content."),
    ("date_mod", "The date field shows characteristics inconsistent with the surrounding text."),
    ("date", "The date field shows characteristics inconsistent with the surrounding text."),
    ("font", "Highlighted text has rendering characteristics that differ from surrounding content."),
    ("baseline", "Text alignment or baseline appears inconsistent with surrounding content."),
    ("kerning", "Character spacing differs from surrounding text."),
    ("spacing", "Text spacing differs from surrounding document content."),
    ("copy_move", "A region appears to have been copied and repositioned."),
    ("splic", "A region appears inconsistent with surrounding image content."),
    ("object_insert", "An object appears to have been inserted into the scene."),
    ("face_swap", "A face region shows characteristics consistent with replacement."),
    ("deepfake", "A face region shows characteristics consistent with digital manipulation."),
    ("metadata", "File history contains a timestamp or authorship inconsistency."),
    ("ocr_engine_mismatch", "Text recognition engines recorded different readings of this region."),
    ("duplicate_frame", "Repeated or discontinuous frames were recorded at this time."),
    ("frame", "Visual characteristics change at this time in a manner inconsistent with surrounding motion."),
)

_FIELD_TITLES = {
    "total amount": "The total amount appears to have been modified.",
    "total": "The total amount appears to have been modified.",
    "amount due": "The amount due appears to have been modified.",
    "invoice amount": "Invoice amount appears to have been modified.",
    "unit price": "The unit price appears to have been modified.",
    "price": "The price appears to have been modified.",
    "tax": "A tax amount appears to have been modified.",
    "quantity": "A quantity value appears to have been modified.",
    "signature": "Signature region shows characteristics inconsistent with surrounding content.",
    "company name": "Company identity information appears inconsistent with surrounding content.",
    "date": "The date field shows characteristics inconsistent with the surrounding text.",
}

_EVIDENCE_REWRITE = (
    (re.compile(r"(?i)phase\s*1 region\s+\S+"), "Independent localization examination also highlighted this area"),
    (re.compile(r"(?i)\(IoU=[^)]+\)"), ""),
    (re.compile(r"(?i)region confidence=[0-9.]+"), ""),
    (re.compile(r"(?i)confirmed by pixel-level forensic analysis\s*[—\-–]?\s*"), ""),
    (re.compile(r"(?i)possible digit insertion"), "digit pattern is consistent with an added numeral"),
    (re.compile(r"(?i)OCR engine disagreement on this region"), "Text recognition engines recorded different readings of this region"),
    (re.compile(r"(?i)font inconsistency flagged on value token"), "Font rendering of this value differs from surrounding text"),
    (re.compile(r"(?i)low OCR confidence on value token"), "Text recognition confidence is lower on this value than surrounding content"),
)


def is_blank(value: Any) -> bool:
    if value is None:
        return True
    return str(value).strip().lower() in {"", "—", "-", "n/a", "na", "none", "unknown"}


def format_timestamp(seconds: Any) -> Optional[str]:
    try:
        value = float(seconds)
    except (TypeError, ValueError):
        return None
    if value < 0:
        return None
    minutes = int(value // 60)
    remainder = value - minutes * 60
    return f"{minutes:02d}:{remainder:06.3f}"


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def hedge_evidence(text: Any) -> str:
    value = _text(text)
    if not value:
        return ""
    for pattern, replacement in _EVIDENCE_REWRITE:
        value = pattern.sub(replacement, value)
    value = re.sub(r"\s{2,}", " ", value).strip(" -—,")
    return value


def investigator_title(
    *,
    finding_type: Any = "",
    field: Any = "",
    media_type: Any = "document",
    time_seconds: Any = None,
    supplied_title: Any = "",
) -> str:
    supplied = _text(supplied_title)
    field_name = _text(field)
    kind = str(finding_type or "").lower().replace("-", "_")
    media = str(media_type or "document").lower()

    if field_name:
        mapped = _FIELD_TITLES.get(field_name.lower())
        if mapped:
            return mapped
        if any(token in kind for token in ("amount", "price", "currency", "numeric", "character_insertion")):
            return f"The {field_name.lower()} appears to have been modified."
        if "signature" in field_name.lower() or "signature" in kind:
            if any(token in kind for token in ("insert", "paste", "overlay", "copied")):
                return "Signature appears digitally inserted."
            return "Signature region shows characteristics inconsistent with surrounding content."
        if "date" in field_name.lower() or "date" in kind:
            return "The date field shows characteristics inconsistent with the surrounding text."

    timestamp = format_timestamp(time_seconds)
    if media == "video" and timestamp:
        return f"Potential visual manipulation identified at {timestamp}."

    if supplied and supplied.lower() not in {field_name.lower(), kind.replace("_", " "), "anomaly", "localization"}:
        return supplied if supplied.endswith(".") else f"{supplied}."

    for token, title in _TITLE_BY_TYPE:
        if token in kind:
            return title
    if field_name:
        return f"{field_name} shows characteristics inconsistent with surrounding content."
    if media == "image":
        return "The highlighted region contains characteristics that differ from the surrounding image."
    if media == "video":
        return "A visual discontinuity was recorded in the highlighted region."
    return "A localized region shows characteristics inconsistent with surrounding content."


def investigator_location(
    *,
    page: Any = None,
    frame: Any = None,
    time_seconds: Any = None,
    field: Any = "",
    location: Any = "",
    finding_type: Any = "",
) -> str:
    supplied = _text(location)
    if supplied and supplied.lower() not in {"document-wide", "localized region", "location not specified"}:
        return supplied
    parts: List[str] = []
    if page not in (None, "", 0, "0"):
        parts.append(f"Page {page}")
    timestamp = format_timestamp(time_seconds)
    if timestamp:
        parts.append(timestamp)
    if frame not in (None, "", 0, "0"):
        parts.append(f"Frame {frame}")
    field_name = _text(field)
    kind = str(finding_type or "").lower()
    if field_name:
        parts.append(field_name)
    elif "signature" in kind:
        parts.append("Signature region")
    elif "logo" in kind:
        parts.append("Logo region")
    elif any(token in kind for token in ("amount", "price", "invoice", "financial")):
        parts.append("Financial details")
    return " · ".join(parts) if parts else "Document-wide"


def investigator_type(finding_type: Any, field: Any = "", field_category: Any = "") -> str:
    kind = str(finding_type or "anomaly")
    category = str(field_category or "").lower()
    field_name = str(field or "").lower()
    if category in {"currency", "numeric", "percentage"} or any(
        token in field_name for token in ("amount", "price", "total", "tax")
    ):
        if "amount" not in kind.lower() and "financial" not in kind.lower():
            return f"financial_{kind}"
    if "signature" in field_name and "signature" not in kind.lower():
        return f"signature_{kind}"
    return kind


def reference_comparison(raw: Dict[str, Any], source: str) -> Optional[Dict[str, Any]]:
    """Use original/current only when they represent a real comparison, not a heuristic guess."""
    reference = raw.get("reference_value") or raw.get("reference_or_expected")
    examined = raw.get("examined_value") or raw.get("examined") or raw.get("current")
    correspondence = str(raw.get("correspondence") or "")
    is_reference = "reference" in str(source).lower() or bool(correspondence) or raw.get("original_comparison")
    if is_reference and not is_blank(reference) and not is_blank(examined):
        return {
            "reference_or_expected": reference,
            "examined": examined,
            "explanation": (
                f"The examined value differs from the corresponding value in the supplied reference. "
                f"Reference: {reference}. Examined: {examined}."
            ),
            "authenticity_status": raw.get("authenticity_status") or "unknown",
        }
    if str(raw.get("type") or "").lower() == "ocr_engine_mismatch":
        original = raw.get("original")
        current = raw.get("current")
        if not is_blank(original) and not is_blank(current) and str(original) != str(current):
            return {
                "reference_or_expected": original,
                "examined": current,
                "explanation": (
                    "Text recognition engines recorded different readings of the same region. "
                    "This is an observation of recognition disagreement, not a verified original."
                ),
            }
    return None


def what_changed_text(comparison: Optional[Dict[str, Any]], observed: List[str], title: str) -> str:
    if comparison:
        original = comparison.get("reference_or_expected") or comparison.get("original")
        examined = comparison.get("examined")
        if not is_blank(original) and not is_blank(examined):
            return f"Reference shows {original}. Examined copy shows {examined}."
        if comparison.get("explanation"):
            return str(comparison["explanation"])
    if observed:
        return observed[0]
    return title


def metadata_date_finding(raw: Dict[str, Any]) -> Optional[Tuple[str, List[str], str]]:
    created = (
        raw.get("creation_date") or raw.get("CreationDate") or raw.get("created_at")
        or (raw.get("exif") or {}).get("DateTimeOriginal")
    )
    modified = (
        raw.get("modification_date") or raw.get("ModDate") or raw.get("modified_at")
        or (raw.get("exif") or {}).get("DateTime")
    )
    if is_blank(created) or is_blank(modified) or str(created) == str(modified):
        return None
    evidence = [
        f"Recorded creation timestamp: {created}.",
        f"Recorded modification timestamp: {modified}.",
        "Metadata therefore indicates the file was modified after the recorded creation time. "
        "Metadata alone does not establish that visible content was altered.",
    ]
    title = "Document metadata indicates that the file was modified after the stated creation date."
    explanation = " ".join(evidence)
    return title, evidence, explanation
