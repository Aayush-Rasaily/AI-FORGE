"""
Performance SLA targets and worker tuning.
"""

from __future__ import annotations

import os

# SLA targets (seconds)
SLA_IMAGE_SEC = float(os.getenv("SLA_IMAGE_SEC", "8"))
SLA_PDF_SEC = float(os.getenv("SLA_PDF_SEC", "15"))
SLA_VIDEO_SEC = float(os.getenv("SLA_VIDEO_SEC", "20"))

# Parallelism
IMAGE_PARALLEL_WORKERS = int(os.getenv("IMAGE_PARALLEL_WORKERS", "12"))
PDF_PARALLEL_PAGES = int(os.getenv("PDF_PARALLEL_PAGES", "6"))
VIDEO_FRAME_WORKERS = int(os.getenv("VIDEO_FRAME_WORKERS", "6"))
OCR_PARALLEL_ENGINES = 4

# Inference
USE_FP16 = os.getenv("USE_FP16", "true").lower() in ("1", "true", "yes")
USE_ONNX = os.getenv("USE_ONNX", "true").lower() in ("1", "true", "yes")
DEFER_EXPLAINABILITY = os.getenv("DEFER_EXPLAINABILITY", "true").lower() in ("1", "true", "yes")

# Cache
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_TTL_SEC = int(os.getenv("REDIS_TTL_SEC", "86400"))
CACHE_VERSION = os.getenv("CACHE_VERSION", "v2")
