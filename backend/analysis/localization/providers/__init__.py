"""Segmentation model providers — TruFor, MVSS-Net, CAT-Net, PSCC-Net, ManTra-Net, heuristic."""

from backend.analysis.localization.providers.heuristic import HeuristicSegmentationProvider
from backend.analysis.localization.providers.registry import get_active_provider, list_providers

__all__ = [
    "HeuristicSegmentationProvider",
    "get_active_provider",
    "list_providers",
]
