"""Stable contracts shared by forensic producers and consumers."""

from .forensic_finding import (
    CanonicalBBox,
    EvidenceProvenance,
    ForensicFinding,
    build_finding,
    deterministic_finding_id,
    normalize_bbox,
    normalize_confidence,
)

__all__ = [
    "CanonicalBBox", "EvidenceProvenance", "ForensicFinding", "build_finding",
    "deterministic_finding_id", "normalize_bbox", "normalize_confidence",
]
