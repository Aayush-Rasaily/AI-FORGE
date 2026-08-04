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

MIN_MATCHES = 8

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

        # ELA suspicion score
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
    """
    Detect possible copy-move manipulation.

    Uses:

        ORB
        ↓
        Feature Matching
        ↓
        RANSAC Homography

    Returns JSON-safe results.
    """

    try:

        image = cv2.imread(
            str(image_path)
        )

        if image is None:

            return {

                "available": False,

                "suspicion_score": 0.0,

                "error":
                    "Unable to read image."

            }

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

        # ORB detector
        orb = cv2.ORB_create(
            nfeatures=3000
        )

        keypoints, descriptors = orb.detectAndCompute(
            gray,
            None
        )

        if descriptors is None:

            return {

                "available": True,

                "keypoints": 0,

                "matches": 0,

                "inliers": 0,

                "suspicion_score": 0.0,

                "message":
                    "Not enough features for copy-move analysis."

            }

        keypoint_count = len(
            keypoints
        )

        if keypoint_count < MIN_ORB_FEATURES:

            return {

                "available": True,

                "keypoints":
                    keypoint_count,

                "matches": 0,

                "inliers": 0,

                "suspicion_score": 0.0,

                "message":
                    "Insufficient ORB features."

            }

        # Brute force matcher
        matcher = cv2.BFMatcher(
            cv2.NORM_HAMMING,
            crossCheck=False
        )

        knn_matches = matcher.knnMatch(
            descriptors,
            descriptors,
            k=2
        )

        good_matches = []

        for pair in knn_matches:

            if len(pair) < 2:

                continue

            m, n = pair

            # Lowe ratio test
            if m.distance < 0.70 * n.distance:

                # Remove self-match
                if m.queryIdx != m.trainIdx:

                    good_matches.append(
                        m
                    )

        match_count = len(
            good_matches
        )

        if match_count < MIN_MATCHES:

            return {

                "available": True,

                "keypoints":
                    keypoint_count,

                "matches":
                    match_count,

                "inliers": 0,

                "suspicion_score": 0.0,

                "copy_move_detected": False,

                "message":
                    "No strong copy-move pattern detected."

            }

        # Extract matched coordinates
        src_points = np.float32(
            [
                keypoints[m.queryIdx].pt
                for m in good_matches
            ]
        ).reshape(
            -1,
            1,
            2
        )

        dst_points = np.float32(
            [
                keypoints[m.trainIdx].pt
                for m in good_matches
            ]
        ).reshape(
            -1,
            1,
            2
        )

        # RANSAC
        homography, mask = cv2.findHomography(
            src_points,
            dst_points,
            cv2.RANSAC,
            RANSAC_REPROJ_THRESHOLD
        )

        if mask is None:

            return {

                "available": True,

                "keypoints":
                    keypoint_count,

                "matches":
                    match_count,

                "inliers": 0,

                "suspicion_score": 0.0,

                "copy_move_detected": False

            }

        inliers = int(
            np.sum(mask)
        )

        inlier_ratio = float(
            inliers / max(
                match_count,
                1
            )
        )

        # Suspicion score
        if inliers >= 30 and inlier_ratio >= 0.50:

            suspicion_score = 0.95

        elif inliers >= 20 and inlier_ratio >= 0.40:

            suspicion_score = 0.80

        elif inliers >= 12 and inlier_ratio >= 0.30:

            suspicion_score = 0.60

        elif inliers >= 8 and inlier_ratio >= 0.25:

            suspicion_score = 0.40

        else:

            suspicion_score = 0.10

        copy_move_detected = (
            suspicion_score >= 0.60
        )

        return {

            "available": True,

            "keypoints":
                keypoint_count,

            "matches":
                match_count,

            "inliers":
                inliers,

            "inlier_ratio":
                round(
                    inlier_ratio,
                    4
                ),

            "copy_move_detected":
                copy_move_detected,

            "suspicion_score":
                round(
                    suspicion_score,
                    4
                ),

            "message":
                (
                    "Potential copy-move manipulation detected."
                    if copy_move_detected
                    else
                    "No strong copy-move manipulation detected."
                )

        }

    except Exception as exc:

        return {

            "available": False,

            "suspicion_score": 0.0,

            "error":
                str(exc)

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
        if variance_std > 5000:

            suspicion_score = 0.70

        elif variance_std > 3000:

            suspicion_score = 0.50

        elif variance_std > 1500:

            suspicion_score = 0.30

        else:

            suspicion_score = 0.10

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

            suspicion_score = 0.05

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

    # --------------------------------------------------------
    # Run individual forensic modules
    # --------------------------------------------------------

    ela_result = perform_ela(
        image_path
    )

    copy_move_result = detect_copy_move(
        image_path
    )

    edge_result = analyze_edge_inconsistency(
        image_path
    )

    metadata_result = analyze_metadata(
        image_path
    )

    # --------------------------------------------------------
    # Collect scores
    # --------------------------------------------------------

    ela_score = float(
        ela_result.get(
            "suspicion_score",
            0.0
        )
    )

    copy_move_score = float(
        copy_move_result.get(
            "suspicion_score",
            0.0
        )
    )

    edge_score = float(
        edge_result.get(
            "suspicion_score",
            0.0
        )
    )

    metadata_score = float(
        metadata_result.get(
            "suspicion_score",
            0.0
        )
    )

    # --------------------------------------------------------
    # Weighted forensic score
    #
    # Copy-move gets highest weight because it is a
    # more direct manipulation signal.
    # --------------------------------------------------------

    tampering_score = (

        0.35
        * ela_score

        +

        0.35
        * copy_move_score

        +

        0.20
        * edge_score

        +

        0.10
        * metadata_score

    )

    tampering_score = max(
        0.0,
        min(
            1.0,
            tampering_score
        )
    )

    # --------------------------------------------------------
    # Determine risk
    # --------------------------------------------------------

    if tampering_score >= 0.75:

        verdict = "HIGHLY_SUSPICIOUS"

        severity = "CRITICAL"

    elif tampering_score >= 0.55:

        verdict = "SUSPICIOUS"

        severity = "HIGH"

    elif tampering_score >= 0.30:

        verdict = "POTENTIALLY_MANIPULATED"

        severity = "MEDIUM"

    else:

        verdict = "NO_STRONG_TAMPERING_SIGNAL"

        severity = "LOW"

    # --------------------------------------------------------
    # Generate forensic signals
    # --------------------------------------------------------

    signals: List[str] = []

    if ela_score >= 0.50:

        signals.append(
            "ELA detected significant compression inconsistencies."
        )

    if copy_move_result.get(
        "copy_move_detected",
        False
    ):

        signals.append(
            "Potential copy-move manipulation detected."
        )

    if edge_score >= 0.50:

        signals.append(
            "Unusual local edge or texture inconsistencies detected."
        )

    if metadata_result.get(
        "suspicious_software"
    ):

        signals.append(
            "Image metadata contains possible editing software indicators."
        )

    if not signals:

        signals.append(
            "No strong independent tampering indicators detected."
        )

    # --------------------------------------------------------
    # Confidence
    #
    # This measures how much forensic evidence was available,
    # not whether the image is definitely fake.
    # --------------------------------------------------------

    available_modules = sum(
        [
            bool(
                ela_result.get(
                    "available",
                    False
                )
            ),

            bool(
                copy_move_result.get(
                    "available",
                    False
                )
            ),

            bool(
                edge_result.get(
                    "available",
                    False
                )
            ),

            bool(
                metadata_result.get(
                    "available",
                    False
                )
            )

        ]
    )

    confidence = (
        available_modules
        / 4.0
    )

    # --------------------------------------------------------
    # Final result
    # --------------------------------------------------------

    result = {

        "success": True,

        "module":
            "tampering_detection",

        "image_path":
            image_path,

        "verdict":
            verdict,

        "severity":
            severity,

        "tampering_score":
            round(
                tampering_score,
                4
            ),

        "tampering_percentage":
            round(
                tampering_score * 100,
                2
            ),

        "confidence":
            round(
                confidence,
                4
            ),

        "signals":
            signals,

        "analysis": {

            "ela":
                ela_result,

            "copy_move":
                copy_move_result,

            "edge_inconsistency":
                edge_result,

            "metadata":
                metadata_result

        }

    }

    return make_json_safe(
        result
    )


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