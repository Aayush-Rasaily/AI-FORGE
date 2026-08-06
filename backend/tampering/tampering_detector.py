"""
AI-FORGE Tampering Detection Engine
====================================

Detects potential image manipulation using multiple forensic signals:

1. Error Level Analysis (ELA)
2. Copy-Move Detection using ORB + BFMatcher + RANSAC
3. Edge Inconsistency Analysis
4. Metadata Analysis

The module is intentionally independent from:

    evidence.py
    evidence_fusion.py
    risk_intelligence.py

This prevents circular imports.

Main function:

    analyze_tampering(image_path)

Returns a JSON-serializable dictionary.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageEnhance, ExifTags


# ============================================================
# CONFIGURATION
# ============================================================

ELA_QUALITY = 90

# Thresholds
ELA_LOW_THRESHOLD = 10
ELA_HIGH_THRESHOLD = 25

MIN_ORB_FEATURES = 50

MIN_MATCHES = 4

RANSAC_REPROJ_THRESHOLD = 5.0

EDGE_KERNEL_SIZE = 5


# ============================================================
# JSON SERIALIZATION
# ============================================================

def make_json_safe(value: Any) -> Any:
    """
    Convert NumPy/OpenCV values into standard Python types.

    Prevents FastAPI errors such as:

        TypeError: 'numpy.int32' object is not iterable
    """

    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, np.floating):
        return float(value)

    if isinstance(value, np.bool_):
        return bool(value)

    if isinstance(value, np.ndarray):
        return value.tolist()

    if isinstance(value, dict):
        return {
            str(k): make_json_safe(v)
            for k, v in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [
            make_json_safe(v)
            for v in value
        ]

    return str(value)


# ============================================================
# ELA — ERROR LEVEL ANALYSIS
# ============================================================

def perform_ela(
    image_path: str,
    quality: int = ELA_QUALITY
) -> Dict[str, Any]:
    """
    Perform Error Level Analysis.

    The image is re-saved at a controlled JPEG quality.
    Differences between the original and recompressed image
    are amplified.

    Higher inconsistency may indicate image manipulation.

    Returns:
        Dictionary containing ELA statistics.
    """

    try:

        original = Image.open(
            image_path
        ).convert("RGB")

        # Temporary in-memory JPEG
        import io

        buffer = io.BytesIO()

        original.save(
            buffer,
            format="JPEG",
            quality=quality
        )

        buffer.seek(0)

        recompressed = Image.open(
            buffer
        ).convert("RGB")

        # Calculate pixel difference
        diff = ImageChops.difference(
            original,
            recompressed
        )

        # Find maximum difference
        extrema = diff.getextrema()

        max_difference = max(
            channel_max
            for _, channel_max in extrema
        )

        # Amplify difference
        scale = (
            255.0 / max_difference
            if max_difference > 0
            else 1.0
        )

        enhanced = ImageEnhance.Brightness(
            diff
        ).enhance(scale)

        # Convert to NumPy
        ela_array = np.array(
            enhanced
        )

        gray = cv2.cvtColor(
            ela_array,
            cv2.COLOR_RGB2GRAY
        )

        mean_error = float(
            np.mean(gray)
        )

        max_error = int(
            np.max(gray)
        )

        high_error_ratio = float(
            np.mean(
                gray > ELA_HIGH_THRESHOLD
            )
        )

        #ELA suspicion score
        if high_error_ratio > 0.20:
            suspicion_score = 0.90
        elif high_error_ratio > 0.10:
            suspicion_score = 0.70
        elif high_error_ratio > 0.05:
            suspicion_score = 0.50
        elif high_error_ratio > 0.02:
            suspicion_score = 0.30
        else:
            suspicion_score = 0.10

        return {

            "available": True,

            "mean_error":
                round(
                    mean_error,
                    4
                ),

            "max_error":
                max_error,

            "high_error_ratio":
                round(
                    high_error_ratio,
                    6
                ),

            "suspicion_score":
                round(
                    suspicion_score,
                    4
                ),

            "message":
                "ELA analysis completed successfully."

        }

    except Exception as exc:

        return {

            "available": False,

            "suspicion_score": 0.0,

            "error":
                str(exc)

        }


# ============================================================
# COPY-MOVE DETECTION
# ============================================================

def detect_copy_move(
    image_path: str
) -> Dict[str, Any]:
    """Delegate to optimized copy-move detector."""
    try:
        from backend.analysis.copy_move import detect_copy_move as _detect

        result = _detect(image_path)
        score = float(result.get("copy_move_score", 0.0))
        detected = bool(result.get("copy_move_detected", False))
        if detected:
            score = max(score, 0.75)

        return make_json_safe({
            "available": True,
            "suspicion_score": score,
            "copy_move_detected": detected,
            "matches": result.get("matched_points", 0),
            "inliers": result.get("inliers", 0),
            "keypoints": result.get("matched_points", 0),
            "message": result.get("verdict", ""),
        })
    except Exception as exc:
        return {
            "available": False,
            "suspicion_score": 0.0,
            "error": str(exc),
        }


# ============================================================
# EDGE INCONSISTENCY ANALYSIS
# ============================================================

def analyze_edge_inconsistency(
    image_path: str
) -> Dict[str, Any]:
    """
    Analyze edge distribution for unusual local inconsistencies.

    This is a supporting signal only.
    It should NOT independently determine whether an image is fake.
    """

    try:

        image = cv2.imread(
            str(image_path)
        )

        if image is None:

            return {

                "available": False,

                "suspicion_score": 0.0

            }

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

        # Blur to reduce noise
        blurred = cv2.GaussianBlur(
            gray,
            (
                EDGE_KERNEL_SIZE,
                EDGE_KERNEL_SIZE
            ),
            0
        )

        edges = cv2.Canny(
            blurred,
            50,
            150
        )

        edge_density = float(
            np.mean(
                edges > 0
            )
        )

        # Calculate local variance
        local_mean = cv2.blur(
            gray.astype(
                np.float32
            ),
            (
                15,
                15
            )
        )

        local_sq_mean = cv2.blur(
            np.square(
                gray.astype(
                    np.float32
                )
            ),
            (
                15,
                15
            )
        )

        local_variance = (
            local_sq_mean
            -
            np.square(
                local_mean
            )
        )

        variance_std = float(
            np.std(
                local_variance
            )
        )

        # Conservative suspicion score
        if variance_std > 2500:
            suspicion_score = 0.80

        elif variance_std > 1800:
            suspicion_score = 0.60

        elif variance_std > 1200:
            suspicion_score = 0.40

        else:
            suspicion_score = 0.15

        return {

            "available": True,

            "edge_density":
                round(
                    edge_density,
                    6
                ),

            "local_variance_std":
                round(
                    variance_std,
                    4
                ),

            "suspicion_score":
                round(
                    suspicion_score,
                    4
                ),

            "message":
                "Edge inconsistency analysis completed."

        }

    except Exception as exc:

        return {

            "available": False,

            "suspicion_score": 0.0,

            "error":
                str(exc)

        }


# ============================================================
# METADATA ANALYSIS
# ============================================================

def analyze_metadata(
    image_path: str
) -> Dict[str, Any]:
    """
    Inspect image metadata for potential editing software
    and suspicious metadata indicators.
    """

    try:

        image = Image.open(
            image_path
        )

        exif_data = image.getexif()

        metadata = {}

        if exif_data:

            for tag_id, value in exif_data.items():

                tag_name = ExifTags.TAGS.get(
                    tag_id,
                    str(tag_id)
                )

                # Convert metadata values to strings
                metadata[
                    str(tag_name)
                ] = str(
                    value
                )

        suspicious_keywords = [

            "photoshop",

            "gimp",

            "paint.net",

            "adobe",

            "lightroom",

            "affinity",

            "canva",

            "pixlr"

        ]

        suspicious_software = []

        metadata_text = str(
            metadata
        ).lower()

        for keyword in suspicious_keywords:

            if keyword in metadata_text:

                suspicious_software.append(
                    keyword
                )

        if suspicious_software:

            suspicion_score = 0.70

        elif metadata:

            suspicion_score = 0.10

        else:

            suspicion_score = 0.10

        return {

            "available": True,

            "metadata_found":
                bool(metadata),

            "metadata_count":
                len(metadata),

            "suspicious_software":
                suspicious_software,

            "suspicion_score":
                round(
                    suspicion_score,
                    4
                ),

            "metadata":
                metadata

        }

    except Exception as exc:

        return {

            "available": False,

            "suspicion_score": 0.0,

            "error":
                str(exc)

        }


# ============================================================
# MAIN TAMPERING ANALYSIS
# ============================================================

def analyze_tampering(
    image_path: str
) -> Dict[str, Any]:
    """
    Run complete tampering analysis.

    Parameters
    ----------
    image_path:
        Path to image.

    Returns
    -------
    dict
        Fully JSON-serializable forensic analysis result.
    """

    image_path = str(
        image_path
    )

    if not os.path.exists(
        image_path
    ):

        return {

            "success": False,

            "error":
                "Image file does not exist.",

            "image_path":
                image_path

        }

    from backend.analysis.parallel_runner import run_parallel_modules
    from backend.analysis.wavelet_analysis import analyze_wavelet
    from backend.fusion.hybrid_fusion import fuse_hybrid_tampering
    from backend.models.tampering_classifier import predict_tampering_score
    from backend.utils.timing import ModuleTimer
    import tempfile

    timer = ModuleTimer("Tampering Analysis")

    def _wavelet_signal():
        with tempfile.TemporaryDirectory() as tmp:
            out = str(Path(tmp) / "wavelet.jpg")
            result = analyze_wavelet(image_path, out)
            return {"suspicion_score": result.get("wavelet_score", 0.0), "available": True}

    def _cnn_signal():
        result = predict_tampering_score(image_path)
        return {"suspicion_score": result.get("score", 0.0), "available": True, **result}

    with timer.track("parallel_modules"):
        parallel = run_parallel_modules(
            {
                "ela": lambda: perform_ela(image_path),
                "copy_move": lambda: detect_copy_move(image_path),
                "edge": lambda: analyze_edge_inconsistency(image_path),
                "metadata": lambda: analyze_metadata(image_path),
                "wavelet": _wavelet_signal,
                "cnn": _cnn_signal,
            },
            max_workers=6,
            timer=timer,
        )

    ela_result = parallel.get("ela") or {}
    copy_move_result = parallel.get("copy_move") or {}
    edge_result = parallel.get("edge") or {}
    metadata_result = parallel.get("metadata") or {}
    wavelet_result = parallel.get("wavelet") or {}
    cnn_result = parallel.get("cnn") or {}

    fusion = fuse_hybrid_tampering({
        "cnn": float(cnn_result.get("suspicion_score", 0.0)),
        "ela": float(ela_result.get("suspicion_score", 0.0)),
        "copy_move": float(copy_move_result.get("suspicion_score", 0.0)),
        "wavelet": float(wavelet_result.get("suspicion_score", 0.0)),
        "edge": float(edge_result.get("suspicion_score", 0.0)),
        "metadata": float(metadata_result.get("suspicion_score", 0.0)),
    })

    tampering_score = fusion["tampering_score"]
    verdict = fusion["verdict"]
    severity = fusion["severity"]
    confidence = fusion["confidence"] / 100.0

    signals: List[str] = []
    if ela_result.get("suspicion_score", 0) >= 0.50:
        signals.append("ELA detected significant compression inconsistencies.")
    if copy_move_result.get("copy_move_detected", False):
        signals.append("Potential copy-move manipulation detected.")
    if edge_result.get("suspicion_score", 0) >= 0.50:
        signals.append("Unusual local edge or texture inconsistencies detected.")
    if metadata_result.get("suspicious_software"):
        signals.append("Image metadata contains possible editing software indicators.")
    if cnn_result.get("score", 0) >= 0.45:
        signals.append(f"CNN tampering classifier flagged anomaly ({cnn_result.get('method', 'cnn')}).")
    if not signals:
        signals.append("No strong independent tampering indicators detected.")

    timing = timer.log_summary()

    result = {
        "success": True,
        "module": "tampering_detection",
        "image_path": image_path,
        "verdict": verdict,
        "severity": severity,
        "tampering_score": tampering_score,
        "tampering_percentage": fusion["tampering_percentage"],
        "confidence": confidence,
        "signals": signals,
        "fusion": fusion,
        "timing": timing,
        "analysis": {
            "ela": ela_result,
            "copy_move": copy_move_result,
            "edge_inconsistency": edge_result,
            "metadata": metadata_result,
            "wavelet": wavelet_result,
            "cnn": cnn_result,
        },
    }

    return make_json_safe(result)


# ============================================================
# OPTIONAL EVIDENCE CONVERSION
# ============================================================

def tampering_to_evidence(
    result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Convert tampering analysis into the same general
    structure expected by AI-FORGE evidence fusion.

    This function returns a dictionary instead of importing
    Evidence directly, keeping this module decoupled.
    """

    score = float(
        result.get(
            "tampering_score",
            0.0
        )
    )

    confidence = float(
        result.get(
            "confidence",
            0.0
        )
    )

    severity = result.get(
        "severity",
        "LOW"
    )

    signals = result.get(
        "signals",
        []
    )

    reason = " ".join(
        str(signal)
        for signal in signals
    )

    return make_json_safe({

        "module":
            "tampering_detection",

        "score":
            score,

        "confidence":
            confidence,

        "severity":
            severity,

        "reason":
            reason,

        "location":
            None

    })


# ============================================================
# EXPORTS
# ============================================================

__all__ = [

    "perform_ela",

    "detect_copy_move",

    "analyze_edge_inconsistency",

    "analyze_metadata",

    "analyze_tampering",

    "tampering_to_evidence",

    "make_json_safe"

]