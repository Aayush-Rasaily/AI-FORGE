"""
Hardware detection — CUDA/GPU availability for inference routing.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Dict

logger = logging.getLogger("ai_forge.hardware")


@lru_cache(maxsize=1)
def get_device_info() -> Dict[str, Any]:
    info: Dict[str, Any] = {
        "device": "cpu",
        "cuda_available": False,
        "cuda_device_name": None,
        "onnx_available": False,
    }
    try:
        import torch
        info["cuda_available"] = torch.cuda.is_available()
        if info["cuda_available"]:
            info["device"] = "cuda"
            info["cuda_device_name"] = torch.cuda.get_device_name(0)
            logger.info("GPU detected: %s", info["cuda_device_name"])
    except ImportError:
        pass

    try:
        import onnxruntime  # noqa: F401
        info["onnx_available"] = True
    except ImportError:
        pass

    return info


def get_torch_device():
    """Return torch device string for model inference."""
    info = get_device_info()
    return info["device"] if info["cuda_available"] else "cpu"
