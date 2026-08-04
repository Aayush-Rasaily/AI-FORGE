from typing import Dict, Any


# ============================================================
# RISK SCORING ENGINE
# ============================================================
#
# Purpose:
# Convert multiple forensic signals into:
#
#   - risk_score
#   - risk_level
#   - confidence
#   - verdict
#   - detected_signals
#   - explanations
#
# IMPORTANT:
# This is a heuristic forensic risk engine.
# It does NOT mathematically prove that an image is fake.
# It combines multiple independent indicators.
#
# ============================================================


def calculate_risk_score(
    ela_score: float = 0.0,
    edge_density: float = 0.0,
    wavelet_score: float = 0.0,
    copy_move_score: float = 0.0,
    copy_move_detected: bool = False,
    noise_score: float = 0.0,
    noise_inconsistency: float = 0.0,
    metadata_suspicious: bool = False,
    jpeg_suspicious: bool = False,
) -> Dict[str, Any]:

    # ========================================================
    # SAFE VALUE CONVERSION
    # ========================================================

    try:
        ela_score = float(ela_score)
    except (TypeError, ValueError):
        ela_score = 0.0

    try:
        edge_density = float(edge_density)
    except (TypeError, ValueError):
        edge_density = 0.0

    try:
        wavelet_score = float(wavelet_score)
    except (TypeError, ValueError):
        wavelet_score = 0.0

    try:
        copy_move_score = float(copy_move_score)
    except (TypeError, ValueError):
        copy_move_score = 0.0

    try:
        noise_score = float(noise_score)
    except (TypeError, ValueError):
        noise_score = 0.0

    try:
        noise_inconsistency = float(
            noise_inconsistency
        )
    except (TypeError, ValueError):
        noise_inconsistency = 0.0

    copy_move_detected = bool(
        copy_move_detected
    )

    metadata_suspicious = bool(
        metadata_suspicious
    )

    jpeg_suspicious = bool(
        jpeg_suspicious
    )


    # ========================================================
    # NORMALIZATION
    # ========================================================
    #
    # Different detectors produce values on different scales.
    #
    # We normalize them into approximately 0 - 1.
    #
    # These thresholds are heuristic and should eventually
    # be calibrated using a real labeled dataset.
    #
    # ========================================================

    ela_normalized = min(

        max(

            ela_score / 0.20,

            0.0

        ),

        1.0

    )


    wavelet_normalized = min(

        max(

            wavelet_score / 0.50,

            0.0

        ),

        1.0

    )


    copy_move_normalized = min(

        max(

            copy_move_score,

            0.0

        ),

        1.0

    )


    noise_normalized = min(

        max(

            noise_inconsistency / 1.0,

            0.0

        ),

        1.0

    )


    # ========================================================
    # SIGNAL CONTRIBUTIONS
    # ========================================================
    #
    # Copy-move is weighted strongly because your detector
    # provides direct spatial duplication evidence.
    #
    # ELA / Wavelet / Noise are supporting evidence.
    #
    # Metadata / JPEG are binary supporting indicators.
    #
    # ========================================================

    score = 0.0


    # ELA contribution
    score += (

        ela_normalized

        *

        25.0

    )


    # Wavelet contribution
    score += (

        wavelet_normalized

        *

        15.0

    )


    # Copy-move contribution
    score += (

        copy_move_normalized

        *

        30.0

    )


    # Noise inconsistency contribution
    score += (

        noise_normalized

        *

        15.0

    )


    # Metadata anomaly
    if metadata_suspicious:

        score += 7.5


    # JPEG anomaly
    if jpeg_suspicious:

        score += 7.5


    # ========================================================
    # DIRECT COPY-MOVE BONUS
    # ========================================================
    #
    # If the copy-move detector explicitly detected
    # manipulation, add additional risk.
    #
    # This ensures:
    #
    # copy_move_detected = True
    #
    # cannot accidentally produce a low-risk result.
    #
    # ========================================================

    if copy_move_detected:

        score += 15.0


    # ========================================================
    # CLAMP SCORE
    # ========================================================

    score = max(

        0.0,

        min(

            100.0,

            score

        )

    )


    score = round(

        score,

        2

    )


    # ========================================================
    # DETECTED SIGNALS
    # ========================================================

    detected_signals = []


    explanations = []


    # --------------------------------------------------------
    # COPY-MOVE
    # --------------------------------------------------------

    if copy_move_detected:

        detected_signals.append(

            "Copy-Move Manipulation"

        )

        explanations.append(

            "Repeated visual regions were detected "
            "with geometrically consistent feature matches."

        )


    elif copy_move_score >= 0.15:

        detected_signals.append(

            "Possible Copy-Move Pattern"

        )

        explanations.append(

            "The image contains a moderate level of "
            "repeated feature matches that may require review."

        )


    # --------------------------------------------------------
    # ELA
    # --------------------------------------------------------

    if ela_normalized >= 0.60:

        detected_signals.append(

            "ELA Compression Anomaly"

        )

        explanations.append(

            "Error Level Analysis indicates inconsistent "
            "JPEG compression behavior across the image."

        )


    # --------------------------------------------------------
    # WAVELET
    # --------------------------------------------------------

    if wavelet_normalized >= 0.60:

        detected_signals.append(

            "Frequency-Domain Anomaly"

        )

        explanations.append(

            "Wavelet analysis detected unusual frequency "
            "patterns that may indicate image manipulation."

        )


    # --------------------------------------------------------
    # NOISE
    # --------------------------------------------------------

    if noise_normalized >= 0.60:

        detected_signals.append(

            "Noise Inconsistency"

        )

        explanations.append(

            "Different image regions exhibit inconsistent "
            "noise characteristics."

        )


    # --------------------------------------------------------
    # METADATA
    # --------------------------------------------------------

    if metadata_suspicious:

        detected_signals.append(

            "Suspicious Metadata"

        )

        explanations.append(

            "Image metadata contains indicators associated "
            "with image editing or processing software."

        )


    # --------------------------------------------------------
    # JPEG
    # --------------------------------------------------------

    if jpeg_suspicious:

        detected_signals.append(

            "JPEG Compression Anomaly"

        )

        explanations.append(

            "JPEG compression characteristics may indicate "
            "recompression or editing."

        )


    # ========================================================
    # RISK LEVEL
    # ========================================================

    if score >= 75:

        risk_level = "CRITICAL"

        verdict = (

            "High Risk - Potential Forgery"

        )


    elif score >= 50:

        risk_level = "HIGH"

        verdict = (

            "Suspicious - Possible Forgery"

        )


    elif score >= 25:

        risk_level = "MEDIUM"

        verdict = (

            "Moderate Risk - Manual Review Recommended"

        )


    else:

        risk_level = "LOW"

        verdict = (

            "No Significant Anomaly Detected"

        )


    # ========================================================
    # CONFIDENCE
    # ========================================================
    #
    # Confidence is based on the number of independent
    # forensic signals supporting the result.
    #
    # This is NOT model probability.
    #
    # ========================================================

    signal_count = len(

        detected_signals

    )


    if signal_count >= 4:

        confidence = 0.90


    elif signal_count == 3:

        confidence = 0.82


    elif signal_count == 2:

        confidence = 0.72


    elif signal_count == 1:

        confidence = 0.60


    else:

        confidence = 0.45


    # ========================================================
    # FINAL RESULT
    # ========================================================

    return {

        "risk_score": score,

        "risk_level": risk_level,

        "verdict": verdict,

        "confidence": round(

            confidence,

            2

        ),

        "signals_detected": signal_count,

        "detected_signals": detected_signals,

        "explanations": explanations

    }