"""
Lazy model warmup on startup — loads models in background thread pool.
"""

from __future__ import annotations

import logging

from backend.utils.worker_pool import get_worker_pool

logger = logging.getLogger("ai_forge.warmup")


def warmup_models_async() -> None:
    """Pre-load heavy models without blocking server startup."""

    def _warmup():
        try:
            from backend.analysis.ml_models import (
                get_clip_bundle,
                get_efficientnet_bundle,
                get_vit_bundle,
                get_xception_bundle,
            )
            from backend.utils.inference_engine import inference_capabilities

            caps = inference_capabilities()
            logger.info("Warming models (fp16=%s, onnx=%s)...", caps.get("fp16_enabled"), caps.get("onnx_enabled"))
            get_efficientnet_bundle()
            get_vit_bundle()
            get_xception_bundle()
            # CLIP is largest — load last
            get_clip_bundle()
            logger.info("Model warmup complete")
        except Exception as exc:
            logger.warning("Model warmup partial failure: %s", exc)

    get_worker_pool().submit(_warmup)
