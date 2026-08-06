"""
Optional ONNX Runtime inference path for reduced latency.

Delegates provider selection to inference_engine (TensorRT → CUDA → CPU).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from backend.utils.inference_engine import get_onnx_providers, get_onnx_session_for, onnx_embed


def get_onnx_session(model_path: Path, providers: Optional[list] = None):
    """Load ONNX session with optimal providers."""
    if providers is None:
        providers = get_onnx_providers()
    name = model_path.stem
    session = get_onnx_session_for(name)
    if session is not None:
        return session
    try:
        import onnxruntime as ort
        if not model_path.exists():
            return None
        return ort.InferenceSession(str(model_path), providers=providers)
    except Exception:
        return None


def run_onnx_inference(session: Any, input_name: str, input_data: Any) -> Any:
    return onnx_embed(session, input_name, input_data)
