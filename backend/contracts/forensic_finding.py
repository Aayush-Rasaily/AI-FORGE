"""Runtime-validated canonical forensic finding contract."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "1.0"
SEVERITIES = frozenset({"LOW", "MEDIUM", "HIGH", "CRITICAL"})
_CERTAINTY = re.compile(
    r"\b(proves?|definitely|certainly|conclusively|confirmed|is forged|is fraudulent|fraudulent)\b",
    re.I,
)


def normalize_confidence(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        result = 0.0
    if not math.isfinite(result):
        result = 0.0
    if result > 1.0:
        result /= 100.0
    return round(max(0.0, min(1.0, result)), 4)


def investigative_severity(
    finding_type: Any,
    supplied: Any = None,
    *,
    legal_or_authorization_impact: bool = False,
) -> str:
    """Classify investigative importance without using confidence."""
    value = str(finding_type or "").lower().replace("-", "_")
    supplied_level = str(supplied or "").upper()
    authorization_issue = any(
        token in value for token in ("signature", "stamp_forgery", "official_seal")
    )
    if legal_or_authorization_impact and (
        authorization_issue or supplied_level == "CRITICAL"
    ):
        return "CRITICAL"
    if any(token in value for token in (
        "amount", "financial", "invoice", "transaction", "account_number",
        "date_modification", "signature", "deepfake", "face_swap",
        "page_replacement", "page_insertion",
    )):
        return "HIGH"
    if supplied_level == "HIGH":
        return "HIGH"
    if any(token in value for token in (
        "metadata", "logo", "font", "spacing", "ocr", "text",
        "copy_move", "splicing", "compression", "structure", "layout",
    )):
        return "MEDIUM"
    return supplied_level if supplied_level in {"LOW", "MEDIUM"} else "LOW"


def legal_safe(text: Any) -> str:
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    replacements = {
        "prove": "may indicate",
        "proves": "may indicate",
        "definitely": "potentially",
        "certainly": "potentially",
        "conclusively": "within the limits of this examination",
        "confirmed": "corroborated",
        "is forged": "may be inconsistent with an authentic source",
        "is fraudulent": "may warrant further authenticity review",
        "fraudulent": "potentially misleading",
    }
    return _CERTAINTY.sub(lambda m: replacements.get(m.group(0).lower(), "may indicate"), value)


@dataclass(frozen=True)
class CanonicalBBox:
    x: float
    y: float
    width: float
    height: float
    coordinate_space: str = "pixels"
    source_width: Optional[int] = None
    source_height: Optional[int] = None

    def __post_init__(self) -> None:
        values = (self.x, self.y, self.width, self.height)
        if not all(math.isfinite(float(v)) for v in values):
            raise ValueError("bbox values must be finite")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("placeholder or zero-area bbox is not permitted")
        if self.source_width is not None and self.source_width <= 0:
            raise ValueError("source_width must be positive")
        if self.source_height is not None and self.source_height <= 0:
            raise ValueError("source_height must be positive")


def normalize_bbox(
    raw: Any,
    *,
    bbox_format: Optional[str] = None,
    coordinate_space: str = "pixels",
    source_width: Optional[int] = None,
    source_height: Optional[int] = None,
) -> Optional[CanonicalBBox]:
    """Normalize xywh/dict/polygon bboxes; None means document-wide."""
    if raw is None:
        return None
    if isinstance(raw, dict):
        x = raw.get("x", raw.get("left"))
        y = raw.get("y", raw.get("top"))
        width = raw.get("width", raw.get("w"))
        height = raw.get("height", raw.get("h"))
        coordinate_space = str(raw.get("coordinate_space") or coordinate_space)
        source_width = raw.get("source_width", source_width)
        source_height = raw.get("source_height", source_height)
    elif isinstance(raw, (list, tuple)) and len(raw) >= 4:
        if isinstance(raw[0], (list, tuple)):
            xs = [float(point[0]) for point in raw]
            ys = [float(point[1]) for point in raw]
            x, y = min(xs), min(ys)
            width, height = max(xs) - x, max(ys) - y
        else:
            x, y, third, fourth = raw[:4]
            if str(bbox_format or "").lower() == "xyxy":
                width, height = float(third) - float(x), float(fourth) - float(y)
            else:
                width, height = third, fourth
    else:
        raise ValueError("unsupported bbox representation")
    return CanonicalBBox(
        x=float(x), y=float(y), width=float(width), height=float(height),
        coordinate_space=coordinate_space,
        source_width=int(source_width) if source_width is not None else None,
        source_height=int(source_height) if source_height is not None else None,
    )


@dataclass(frozen=True)
class EvidenceProvenance:
    evidence_id: str
    source_artifact: Optional[str] = None
    source_file: Optional[str] = None
    method: str = "unknown"
    sha256: Optional[str] = None
    observed_at: Optional[str] = None
    generated_at: Optional[str] = None

    def __post_init__(self) -> None:
        if not str(self.evidence_id).strip():
            raise ValueError("provenance evidence_id is required")
        if not str(self.method).strip():
            raise ValueError("provenance method is required")


@dataclass(frozen=True)
class ForensicFinding:
    finding_id: str
    title: str
    type: str
    verdict: str
    severity: str
    confidence: float
    media_type: str
    observed_evidence: List[str]
    short_explanation: str
    detailed_explanation: str
    potential_impact: str
    recommended_review: str
    evidence_chain: List[EvidenceProvenance]
    schema_version: str = SCHEMA_VERSION
    page: Optional[int] = None
    frame: Optional[int] = None
    time_seconds: Optional[float] = None
    bbox: Optional[CanonicalBBox] = None
    location: str = "Document-wide"
    original_comparison: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"unsupported schema_version: {self.schema_version}")
        if self.severity.upper() not in SEVERITIES:
            raise ValueError("severity must be LOW, MEDIUM, HIGH, or CRITICAL")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if not self.observed_evidence or not any(str(v).strip() for v in self.observed_evidence):
            raise ValueError("a finding requires observed evidence")
        if not self.evidence_chain:
            raise ValueError("a finding requires evidence provenance")
        for name in ("finding_id", "title", "type", "verdict", "media_type",
                     "short_explanation", "detailed_explanation", "recommended_review"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} is required")
        if self.bbox is None and not self.location:
            object.__setattr__(self, "location", "Document-wide")

    def to_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        # Explicit alias keeps consumers that call this field "provenance" compatible.
        value["provenance"] = list(value["evidence_chain"])
        return value


def deterministic_finding_id(evidence_id: str, identity: Dict[str, Any]) -> str:
    canonical = json.dumps(
        {"evidence_id": str(evidence_id), **identity},
        sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str,
    )
    return "FF-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20].upper()


def build_finding(
    *,
    evidence_id: str,
    title: Any,
    finding_type: Any,
    verdict: Any,
    severity: Any,
    confidence: Any,
    media_type: Any,
    observed_evidence: Any,
    short_explanation: Any,
    detailed_explanation: Any = "",
    original_comparison: Optional[Dict[str, Any]] = None,
    potential_impact: Any = "",
    recommended_review: Any = "",
    provenance: Any,
    page: Any = None,
    frame: Any = None,
    time_seconds: Any = None,
    bbox: Any = None,
    bbox_format: Optional[str] = None,
    location: Any = None,
    coordinate_space: str = "pixels",
    source_width: Optional[int] = None,
    source_height: Optional[int] = None,
) -> ForensicFinding:
    evidence = observed_evidence if isinstance(observed_evidence, (list, tuple)) else [observed_evidence]
    evidence = [legal_safe(item) for item in evidence if str(item or "").strip()]
    if not evidence:
        raise ValueError("a finding requires observed evidence")
    box = normalize_bbox(
        bbox, bbox_format=bbox_format, coordinate_space=coordinate_space,
        source_width=source_width, source_height=source_height,
    )
    chain_items = provenance if isinstance(provenance, (list, tuple)) else [provenance]
    chain = [
        item if isinstance(item, EvidenceProvenance) else EvidenceProvenance(**item)
        for item in chain_items
    ]
    normalized_severity = str(severity or "MEDIUM").upper()
    normalized_location = str(location or ("Document-wide" if box is None else "Localized region"))
    identity = {
        "type": str(finding_type or "anomaly").lower(),
        "page": int(page) if page is not None else None,
        "frame": int(frame) if frame is not None else None,
        "time_seconds": round(float(time_seconds), 3) if time_seconds is not None else None,
        "bbox": asdict(box) if box else None,
        "location": normalized_location.lower(),
        "observed_evidence": sorted(evidence),
        "method": sorted(p.method for p in chain),
    }
    return ForensicFinding(
        finding_id=deterministic_finding_id(evidence_id, identity),
        title=legal_safe(title),
        type=str(finding_type or "anomaly"),
        verdict=legal_safe(verdict),
        severity=normalized_severity,
        confidence=normalize_confidence(confidence),
        media_type=str(media_type or "unknown"),
        page=int(page) if page is not None else None,
        frame=int(frame) if frame is not None else None,
        time_seconds=float(time_seconds) if time_seconds is not None else None,
        bbox=box,
        location=normalized_location,
        observed_evidence=evidence,
        short_explanation=legal_safe(short_explanation),
        detailed_explanation=legal_safe(detailed_explanation or short_explanation),
        original_comparison=original_comparison,
        potential_impact=legal_safe(potential_impact or "The significance should be assessed in context."),
        recommended_review=legal_safe(recommended_review or "Review against an authenticated source."),
        evidence_chain=chain,
    )
