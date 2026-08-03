"""
AI-FORGE
Unified Image Fraud Risk Scoring Engine

This module combines multiple forensic signals
into an explainable fraud risk assessment.

IMPORTANT:
This is a forensic risk assessment system.
It does not guarantee that an image is authentic
or forged. Results should be interpreted as
evidence requiring review.
"""


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def safe_float(
    value,
    default=0.0
):

    try:

        value = float(value)

        if value != value:  # NaN

            return default

        return value

    except (

        TypeError,

        ValueError

    ):

        return default


def clamp(

    value,

    minimum=0.0,

    maximum=1.0

):

    return max(

        minimum,

        min(

            maximum,

            value

        )

    )


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_ela(
    value
):

    value = safe_float(
        value
    )

    if value <= 1.0:

        return clamp(
            value
        )

    return clamp(

        value / 255.0

    )


def normalize_wavelet(
    value
):

    value = safe_float(
        value
    )

    if value <= 1.0:

        return clamp(
            value
        )

    return clamp(

        value / 255.0

    )


def normalize_copy_move(
    value
):

    return clamp(

        safe_float(
            value
        )

    )


def normalize_noise(
    value
):

    value = safe_float(
        value
    )

    # Noise inconsistency values
    # can exceed 1.

    return clamp(

        value / 2.0

    )


# ============================================================
# EXTRACT BOOLEAN SIGNAL
# ============================================================

def get_boolean(

    value

):

    if isinstance(

        value,

        bool

    ):

        return value


    if isinstance(

        value,

        str

    ):

        return value.lower() in [

            "true",

            "1",

            "yes",

            "detected",

            "suspicious"

        ]


    return bool(
        value
    )


# ============================================================
# MAIN RISK SCORING FUNCTION
# ============================================================

def calculate_risk_score(
    signals
):

    if not isinstance(

        signals,

        dict

    ):

        signals = {}


    # ========================================================
    # BASIC FORENSIC SIGNALS
    # ========================================================

    ela_score = normalize_ela(

        signals.get(

            "ela_score",

            0.0

        )

    )


    edge_density = clamp(

        safe_float(

            signals.get(

                "edge_density",

                0.0

            )

        )

    )


    wavelet_score = normalize_wavelet(

        signals.get(

            "wavelet_score",

            0.0

        )

    )


    copy_move_score = normalize_copy_move(

        signals.get(

            "copy_move_score",

            0.0

        )

    )


    copy_move_detected = get_boolean(

        signals.get(

            "copy_move_detected",

            False

        )

    )


    # ========================================================
    # NOISE
    # ========================================================

    noise_inconsistency = normalize_noise(

        signals.get(

            "noise_inconsistency",

            0.0

        )

    )


    # ========================================================
    # METADATA
    # ========================================================

    metadata_suspicious = get_boolean(

        signals.get(

            "metadata_suspicious",

            False

        )

    )


    software_detected = get_boolean(

        signals.get(

            "software_detected",

            False

        )

    )


    # ========================================================
    # JPEG
    # ========================================================

    jpeg_suspicious = get_boolean(

        signals.get(

            "jpeg_suspicious",

            False

        )

    )


    # ========================================================
    # INDIVIDUAL CONTRIBUTIONS
    # ========================================================

    contributions = {}


    contributions[

        "copy_move"

    ] = round(

        copy_move_score * 35,

        2

    )


    contributions[

        "ela"

    ] = round(

        ela_score * 15,

        2

    )


    contributions[

        "wavelet"

    ] = round(

        wavelet_score * 10,

        2

    )


    contributions[

        "noise"

    ] = round(

        noise_inconsistency * 15,

        2

    )


    # Edge density is only a weak
    # supporting signal.

    contributions[

        "edge"

    ] = round(

        edge_density * 5,

        2

    )


    # ========================================================
    # BASE RISK SCORE
    # ========================================================

    risk_score = (

        contributions[

            "copy_move"

        ]

        +

        contributions[

            "ela"

        ]

        +

        contributions[

            "wavelet"

        ]

        +

        contributions[

            "noise"

        ]

        +

        contributions[

            "edge"

        ]

    )


    # ========================================================
    # METADATA EVIDENCE
    # ========================================================

    if metadata_suspicious:

        risk_score += 10


    # ========================================================
    # JPEG EVIDENCE
    # ========================================================

    if jpeg_suspicious:

        risk_score += 10


    # ========================================================
    # SOFTWARE DETECTION
    # ========================================================

    # Software alone should NOT classify
    # an image as forged.
    #
    # Many legitimate images are edited.

    software_bonus = 0

    if software_detected:

        software_bonus = 2

        risk_score += software_bonus


    # ========================================================
    # COPY-MOVE DIRECT EVIDENCE
    # ========================================================

    if copy_move_detected:

        # Strong direct evidence.

        risk_score = max(

            risk_score,

            75

        )


    # ========================================================
    # NORMALIZE 0 - 100
    # ========================================================

    risk_score = max(

        0,

        min(

            100,

            risk_score

        )

    )


    risk_score = round(

        risk_score,

        2

    )


    # ========================================================
    # RISK LEVEL
    # ========================================================

    if risk_score >= 75:

        risk_level = (

            "CRITICAL"

        )


    elif risk_score >= 60:

        risk_level = (

            "HIGH"

        )


    elif risk_score >= 40:

        risk_level = (

            "MEDIUM"

        )


    elif risk_score >= 20:

        risk_level = (

            "LOW"

        )


    else:

        risk_level = (

            "MINIMAL"

        )


    # ========================================================
    # BUILD REASONS
    # ========================================================

    reasons = []


    # --------------------------------------------------------
    # COPY MOVE
    # --------------------------------------------------------

    if copy_move_detected:

        reasons.append({

            "signal":

                "Copy-Move Detection",

            "severity":

                "HIGH",

            "message":

                "Duplicated image regions were detected using feature matching and geometric verification."

        })


    elif copy_move_score >= 0.20:

        reasons.append({

            "signal":

                "Copy-Move Similarity",

            "severity":

                "MEDIUM",

            "message":

                "Some repeated visual patterns were detected, but the evidence is below the direct copy-move threshold."

        })


    # --------------------------------------------------------
    # ELA
    # --------------------------------------------------------

    if ela_score >= 0.50:

        reasons.append({

            "signal":

                "ELA",

            "severity":

                "MEDIUM",

            "message":

                "Elevated JPEG error-level differences were detected."

        })


    elif ela_score >= 0.30:

        reasons.append({

            "signal":

                "ELA",

            "severity":

                "LOW",

            "message":

                "Moderate compression differences were detected."

        })


    # --------------------------------------------------------
    # NOISE
    # --------------------------------------------------------

    if noise_inconsistency >= 0.50:

        reasons.append({

            "signal":

                "Noise Inconsistency",

            "severity":

                "HIGH",

            "message":

                "Different image regions exhibit substantially different noise characteristics."

        })


    elif noise_inconsistency >= 0.30:

        reasons.append({

            "signal":

                "Noise Inconsistency",

            "severity":

                "MEDIUM",

            "message":

                "Some regional noise inconsistencies were detected."

        })


    # --------------------------------------------------------
    # WAVELET
    # --------------------------------------------------------

    if wavelet_score >= 0.50:

        reasons.append({

            "signal":

                "Wavelet Analysis",

            "severity":

                "MEDIUM",

            "message":

                "High-frequency image characteristics show unusual patterns."

        })


    # --------------------------------------------------------
    # METADATA
    # --------------------------------------------------------

    if metadata_suspicious:

        reasons.append({

            "signal":

                "Metadata",

            "severity":

                "MEDIUM",

            "message":

                "Image metadata contains indicators associated with image editing software."

        })


    # --------------------------------------------------------
    # JPEG
    # --------------------------------------------------------

    if jpeg_suspicious:

        reasons.append({

            "signal":

                "JPEG Compression",

            "severity":

                "MEDIUM",

            "message":

                "JPEG compression characteristics indicate possible recompression or editing history."

        })


    # ========================================================
    # VERDICT
    # ========================================================

    if copy_move_detected:

        verdict = (

            "Potential Forgery"

        )


    elif risk_score >= 75:

        verdict = (

            "Likely Forged"

        )


    elif risk_score >= 60:

        verdict = (

            "High Risk of Manipulation"

        )


    elif risk_score >= 40:

        verdict = (

            "Suspicious"

        )


    elif risk_score >= 20:

        verdict = (

            "Low Risk - Review Recommended"

        )


    else:

        verdict = (

            "No Significant Anomaly Detected"

        )


    # ========================================================
    # CONFIDENCE
    # ========================================================

    evidence_count = len(

        reasons

    )


    if copy_move_detected:

        confidence = 0.92


    elif evidence_count >= 4:

        confidence = 0.88


    elif evidence_count == 3:

        confidence = 0.78


    elif evidence_count == 2:

        confidence = 0.68


    elif evidence_count == 1:

        confidence = 0.55


    else:

        confidence = 0.40


    # ========================================================
    # FINAL RESULT
    # ========================================================

    return {

        "risk_score":

            risk_score,


        "risk_level":

            risk_level,


        "verdict":

            verdict,


        "confidence":

            round(

                confidence,

                2

            ),


        "reasons":

            reasons,


        "contributions":

            contributions,


        "signal_summary": {

            "copy_move":

                copy_move_detected,

            "ela":

                round(

                    ela_score,

                    4

                ),

            "wavelet":

                round(

                    wavelet_score,

                    4

                ),

            "noise_inconsistency":

                round(

                    noise_inconsistency,

                    4

                ),

            "metadata":

                metadata_suspicious,

            "jpeg":

                jpeg_suspicious

        }

    }