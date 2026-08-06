"""
Unified inference — FP16, ONNX Runtime, TensorRT provider, lazy model optimization.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from backend.utils.hardware import get_device_info, get_torch_device
from backend.utils.performance_config import USE_FP16, USE_ONNX

logger = logging.getLogger("ai_forge.inference")

MODELS_DIR = Path("data/models/onnx")
_ONNX_SESSIONS: Dict[str, Any] = {}


def get_onnx_providers() -> list:
    """Prefer TensorRT → CUDA → CPU for ONNX Runtime."""
    try:
        import onnxruntime as ort
        available = ort.get_available_providers()
    except ImportError:
        return ["CPUExecutionProvider"]

    providers = []
    for name in ("TensorrtExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"):
        if name in available:
            providers.append(name)
    return providers or ["CPUExecutionProvider"]


def optimize_torch_model(model: Any, device: Any) -> Any:
    """Apply FP16 on GPU — same weights, faster inference, maintained accuracy."""
    import torch

    model.eval()
    if str(device) != "cpu":
        model = model.to(device)
    if USE_FP16 and str(device).startswith("cuda"):
        try:
            model = model.half()
            logger.debug("Model optimized with FP16 on %s", device)
        except Exception as exc:
            logger.debug("FP16 optimization skipped: %s", exc)
    return model


def torch_infer(model: Any, tensor: Any, device: Any) -> Any:
    """Run inference with optional autocast FP16."""
    import torch

    use_fp16 = USE_FP16 and str(device).startswith("cuda")
    with torch.no_grad():
        if use_fp16:
            with torch.cuda.amp.autocast(dtype=torch.float16):
                if tensor.dtype != torch.float16:
                    tensor = tensor.half()
                return model(tensor)
        return model(tensor)


def get_onnx_session_for(model_name: str) -> Optional[Any]:
    """Load cached ONNX session if exported model exists."""
    if not USE_ONNX:
        return None
    if model_name in _ONNX_SESSIONS:
        return _ONNX_SESSIONS[model_name]

    path = MODELS_DIR / f"{model_name}.onnx"
    if not path.exists():
        return None

    try:
        import onnxruntime as ort
        sess = ort.InferenceSession(str(path), providers=get_onnx_providers())
        _ONNX_SESSIONS[model_name] = sess
        logger.info("ONNX session loaded: %s (%s)", model_name, sess.get_providers())
        return sess
    except Exception as exc:
        logger.debug("ONNX load failed for %s: %s", model_name, exc)
        return None


def onnx_embed(session: Any, input_name: str, tensor_np: np.ndarray) -> Optional[np.ndarray]:
    """ONNX inference — numpy in/out."""
    try:
        if tensor_np.dtype != np.float32:
            tensor_np = tensor_np.astype(np.float32)
        outputs = session.run(None, {input_name: tensor_np})
        return outputs[0].flatten()
    except Exception as exc:
        logger.warning("ONNX inference failed: %s", exc)
        return None


@lru_cache(maxsize=1)
def inference_capabilities() -> Dict[str, Any]:
    info = get_device_info()
    return {
        **info,
        "fp16_enabled": USE_FP16 and info.get("cuda_available"),
        "onnx_enabled": USE_ONNX and info.get("onnx_available"),
        "onnx_providers": get_onnx_providers() if info.get("onnx_available") else [],
        "tensorrt_available": "TensorrtExecutionProvider" in get_onnx_providers(),
    }
