"""
Reproducibility manifest — pipeline version, config hash, model fingerprints.

Attached to every analysis result so runs can be verified and re-executed.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.utils.performance_config import (
    CACHE_VERSION,
    DEFER_EXPLAINABILITY,
    IMAGE_PARALLEL_WORKERS,
    USE_FP16,
    USE_ONNX,
)

PIPELINE_VERSION = "2.0.0"


def _config_snapshot() -> Dict[str, Any]:
    return {
        "pipeline_version": PIPELINE_VERSION,
        "cache_version": CACHE_VERSION,
        "use_fp16": USE_FP16,
        "use_onnx": USE_ONNX,
        "defer_explainability": DEFER_EXPLAINABILITY,
        "image_parallel_workers": IMAGE_PARALLEL_WORKERS,
        "python": sys.version,
        "platform": platform.platform(),
    }


def build_reproducibility_manifest(
    *,
    evidence_id: str,
    file_hashes: Dict[str, str],
    media_type: str,
    analysis_result: Optional[Dict[str, Any]] = None,
    execution_times: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    config = _config_snapshot()
    config_hash = hashlib.sha256(
        json.dumps(config, sort_keys=True).encode()
    ).hexdigest()

    manifest = {
        "manifest_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_id": evidence_id,
        "media_type": media_type,
        "evidence_hashes": file_hashes,
        "config": config,
        "config_hash": config_hash,
        "execution_times": execution_times or {},
    }

    if analysis_result:
        result_digest = hashlib.sha256(
            json.dumps(analysis_result, sort_keys=True, default=str).encode()
        ).hexdigest()
        manifest["analysis_digest_sha256"] = result_digest
        manifest["verdict"] = analysis_result.get("verdict")
        manifest["risk_score"] = analysis_result.get("risk_score")

    manifest["manifest_hash"] = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, default=str).encode()
    ).hexdigest()

    return manifest
