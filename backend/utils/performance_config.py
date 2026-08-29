"""
Performance SLA targets and worker tuning — all values from environment.
"""

from __future__ import annotations

import os

# SLA targets (seconds) — production defaults match enterprise targets
SLA_IMAGE_SEC = float(os.getenv("SLA_IMAGE_SEC", "10"))
SLA_PDF_SEC = float(os.getenv("SLA_PDF_SEC", "15"))
SLA_REPORT_SEC = float(os.getenv("SLA_REPORT_SEC", "3"))
SLA_VIDEO_SEC = float(os.getenv("SLA_VIDEO_SEC", "20"))

# Parallelism
_CPU = os.cpu_count() or 4
IMAGE_PARALLEL_WORKERS = int(os.getenv("IMAGE_PARALLEL_WORKERS", str(min(8, max(4, _CPU)))))
PDF_PARALLEL_PAGES = int(os.getenv("PDF_PARALLEL_PAGES", "5"))
VIDEO_FRAME_WORKERS = int(os.getenv("VIDEO_FRAME_WORKERS", str(min(6, _CPU))))
OCR_PARALLEL_ENGINES = int(os.getenv("OCR_PARALLEL_ENGINES", "4"))

# Pipeline modes
FAST_PIPELINE_COMPLETION = os.getenv("FAST_PIPELINE_COMPLETION", "true").lower() in ("1", "true", "yes")
DEFER_EXPLAINABILITY = os.getenv("DEFER_EXPLAINABILITY", "true").lower() in ("1", "true", "yes")
DOC_FAST_FORENSICS = os.getenv("DOC_FAST_FORENSICS", "true").lower() in ("1", "true", "yes")
DOC_SLA_PAGE_CAP = int(os.getenv("DOC_SLA_PAGE_CAP", "0"))  # 0 = no cap

# Quick scan thresholds
QUICK_SCAN_AUTHENTIC_THRESHOLD = float(os.getenv("QUICK_SCAN_AUTHENTIC_THRESHOLD", "0.22"))
QUICK_SCAN_SUSPICIOUS_THRESHOLD = float(os.getenv("QUICK_SCAN_SUSPICIOUS_THRESHOLD", "0.38"))
QUICK_SCAN_FORCE_BORDERLINE_DEEP = os.getenv("QUICK_SCAN_FORCE_BORDERLINE_DEEP", "false").lower() in ("1", "true", "yes")

# Inference
USE_FP16 = os.getenv("USE_FP16", "true").lower() in ("1", "true", "yes")
USE_ONNX = os.getenv("USE_ONNX", "true").lower() in ("1", "true", "yes")

# Cache
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_TTL_SEC = int(os.getenv("REDIS_TTL_SEC", "86400"))
CACHE_VERSION = os.getenv("CACHE_VERSION", "v2")

# Frontend-aligned timeouts (seconds)
REPORT_POLL_INTERVAL_MS = int(os.getenv("REPORT_POLL_INTERVAL_MS", "500"))
REPORT_POLL_MAX_ATTEMPTS = int(os.getenv("REPORT_POLL_MAX_ATTEMPTS", "12"))
ARTIFACT_POLL_INTERVAL_MS = int(os.getenv("ARTIFACT_POLL_INTERVAL_MS", "1500"))
ARTIFACT_POLL_MAX_ATTEMPTS = int(os.getenv("ARTIFACT_POLL_MAX_ATTEMPTS", "20"))
