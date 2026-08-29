"""Registry for localization segmentation providers."""

from __future__ import annotations

import os
from typing import Dict, List

from backend.analysis.localization.contracts import SegmentationProvider
from backend.analysis.localization.providers.dl_providers import (
    CATNetProvider,
    ManTraNetProvider,
    MVSSProvider,
    PSCCProvider,
    TruForProvider,
)
from backend.analysis.localization.providers.heuristic import HeuristicSegmentationProvider

_PROVIDERS: Dict[str, SegmentationProvider] = {
    "trufor": TruForProvider(),
    "mvss": MVSSProvider(),
    "mvss_net": MVSSProvider(),
    "catnet": CATNetProvider(),
    "cat-net": CATNetProvider(),
    "pscc": PSCCProvider(),
    "pscc-net": PSCCProvider(),
    "mantranet": ManTraNetProvider(),
    "mantra-net": ManTraNetProvider(),
    "heuristic": HeuristicSegmentationProvider(),
}


def list_providers() -> List[str]:
    return list(_PROVIDERS.keys())


def get_active_provider() -> SegmentationProvider:
    """
    Select provider from LOCALIZATION_MODEL env var.
    Falls back to first available DL provider, then heuristic.
    """
    preferred = os.getenv("LOCALIZATION_MODEL", "trufor").lower().strip()
    if preferred in _PROVIDERS:
        provider = _PROVIDERS[preferred]
        if provider.is_available() or preferred == "heuristic":
            return provider

    for key in ("trufor", "mvss", "catnet", "pscc", "mantranet"):
        provider = _PROVIDERS[key]
        if provider.is_available():
            return provider

    return _PROVIDERS["heuristic"]
