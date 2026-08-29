"""
Contracts for pluggable localization / segmentation providers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol


@dataclass
class SegmentationOutput:
    """Raw output from a segmentation model provider."""

    provider: str
    confidence_heatmap: Any  # np.ndarray float32 HxW 0-1
    binary_mask: Any  # np.ndarray uint8 HxW 0/255
    score: float = 0.0
    confidence: float = 0.0
    explanation: str = ""
    available: bool = True
    artifact_paths: Dict[str, str] = field(default_factory=dict)


@dataclass
class SmartRegion:
    """Detected manipulated region with forensic metadata."""

    id: str
    label: str
    region_type: str
    bbox: Dict[str, int]
    polygon: List[List[int]]
    score: float
    confidence: float
    verdict: str
    detector_contributions: Dict[str, float] = field(default_factory=dict)
    technical_explanation: str = ""
    plain_english_explanation: str = ""
    evidence: List[str] = field(default_factory=list)


class SegmentationProvider(Protocol):
    """Plugin interface for manipulation segmentation models."""

    name: str

    def is_available(self) -> bool: ...

    def segment(self, image_path: str, output_dir: str) -> SegmentationOutput: ...
