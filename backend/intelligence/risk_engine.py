from typing import Any, Dict


# ============================================================
# UNIFIED FRAUD RISK ENGINE
# ============================================================
#
# This module combines the results from:
#
# 1. Image Forensics
# 2. Document Forensics
# 3. Signature Verification
# 4. Video Analytics
#
# It does NOT replace the individual forensic modules.
#
# It acts as a higher-level decision layer.
#
# Output:
#
# - fraud_score       -> 0 to 100
# - risk_level        -> LOW / MEDIUM / HIGH
# - verdict           -> final investigation verdict
# - signals           -> detected suspicious indicators
# - explanation       -> human-readable explanation
#
# ============================================================


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def safe_float(
    value: Any,
    default: float = 0.0
) -> float:

    try:

        return float(value)

    except (
        TypeError,
        ValueError
    ):

        return default


def safe_int(
    value: Any,
    default: int = 0
) -> int:

    try:

        return int(value)

    except (
        TypeError,
        ValueError
    ):

        return default


def safe_bool(
    value: Any
) -> bool:

    if isinstance(
        value,
        bool
    ):

        return value

    if isinstance(
        value,
        str
    ):

        return value.lower() in {

            "true",
            "1",
            "yes",
            "detected"

        }

    return bool(value)


# ============================================================
# NORMALIZE SCORE
# ============================================================

def normalize_score(
    score: float
) -> float:

    """
    Converts a score into a 0-1 range.

    Handles:
        0.0 - 1.0
        0   - 100

    Example:

        0.75 -> 0.75
        75   -> 0.75
    """

    score = safe_float(
        score
    )

    if score > 1:

        score = score / 100.0

    return max(
        0.0,
        min(
            score,
            1.0
        )
    )


# ============================================================
# IMAGE RISK ANALYSIS
# ============================================================

def analyze_image_risk(
    image_result: Dict[str, Any]
) -> Dict[str, Any]:

    if not isinstance(
        image_result,
        dict
    ):

        return {

            "score": 0.0,

            "signals": []

        }


    signals = image_result.get(
        "signals",
        {}
    )


    if not isinstance(
        signals,
        dict
    ):

        signals = {}


    forensic_score = normalize_score(

        image_result.get(

            "forensic_score",

            0.0

        )

    )


    copy_move_detected = safe_bool(

        signals.get(

            "copy_move_detected",

            False

        )

    )


    copy_move_score = normalize_score(

        signals.get(

            "copy_move_score",

            0.0

        )

    )


    ela_score = normalize_score(

        signals.get(

            "ela_score",

            0.0

        )

    )


    wavelet_score = normalize_score(

        signals.get(

            "wavelet_score",

            0.0

        )

    )


    edge_density = normalize_score(

        signals.get(

            "edge_density",

            0.0

        )

    )


    detected_signals = []


    # -----------------------------------------
    # Copy-Move
    # -----------------------------------------

    if copy_move_detected:

        detected_signals.append(

            "Copy-move manipulation detected"

        )


    elif copy_move_score >= 0.5:

        detected_signals.append(

            "Elevated copy-move detection score"

        )


    # -----------------------------------------
    # ELA
    # -----------------------------------------

    if ela_score >= 0.5:

        detected_signals.append(

            "Compression-level anomaly detected"

        )


    # -----------------------------------------
    # Wavelet
    # -----------------------------------------

    if wavelet_score >= 0.5:

        detected_signals.append(

            "High-frequency image artifact detected"

        )


    # -----------------------------------------
    # Edge
    # -----------------------------------------

    if edge_density >= 0.7:

        detected_signals.append(

            "Unusual structural edge density detected"

        )


    # -----------------------------------------
    # Final Image Score
    # -----------------------------------------

    if copy_move_detected:

        score = max(

            forensic_score,

            0.80

        )

    else:

        score = forensic_score


    return {

        "score":
            round(
                score,
                4
            ),

        "signals":
            detected_signals

    }


# ============================================================
# DOCUMENT RISK ANALYSIS
# ============================================================

def analyze_document_risk(
    document_result: Dict[str, Any]
) -> Dict[str, Any]:

    if not isinstance(
        document_result,
        dict
    ):

        return {

            "score": 0.0,

            "signals": []

        }


    pages = document_result.get(

        "pages",

        []

    )


    if not isinstance(
        pages,
        list
    ):

        pages = []


    page_scores = []

    detected_signals = []


    # -----------------------------------------
    # Analyze Every Page
    # -----------------------------------------

    for page_index, page in enumerate(

        pages

    ):

        if not isinstance(
            page,
            dict
        ):

            continue


        page_number = page.get(

            "page_number",

            page_index + 1

        )


        forensic_result = page.get(

            "forensics",

            {}

        )


        if not isinstance(

            forensic_result,

            dict

        ):

            forensic_result = {}


        page_score = normalize_score(

            forensic_result.get(

                "forensic_score",

                0.0

            )

        )


        page_scores.append(

            page_score

        )


        # -------------------------------------
        # Check Forensic Verdict
        # -------------------------------------

        page_verdict = str(

            forensic_result.get(

                "verdict",

                ""

            )

        ).lower()


        if (

            "forgery"

            in

            page_verdict

            or

            "suspicious"

            in

            page_verdict

        ):

            detected_signals.append(

                f"Suspicious forensic indicators "
                f"detected on page {page_number}"

            )


        # -------------------------------------
        # Check Signals
        # -------------------------------------

        signals = forensic_result.get(

            "signals",

            {}

        )


        if not isinstance(

            signals,

            dict

        ):

            signals = {}


        if safe_bool(

            signals.get(

                "copy_move_detected",

                False

            )

        ):

            detected_signals.append(

                f"Copy-move manipulation detected "
                f"on page {page_number}"

            )


        if normalize_score(

            signals.get(

                "ela_score",

                0.0

            )

        ) >= 0.5:

            detected_signals.append(

                f"ELA anomaly detected "
                f"on page {page_number}"

            )


    # -----------------------------------------
    # Calculate Document Score
    # -----------------------------------------

    if page_scores:

        document_score = max(

            page_scores

        )

    else:

        document_score = 0.0


    return {

        "score":

            round(

                document_score,

                4

            ),

        "signals":

            detected_signals

    }


# ============================================================
# SIGNATURE RISK ANALYSIS
# ============================================================

def analyze_signature_risk(
    signature_result: Dict[str, Any]
) -> Dict[str, Any]:

    if not isinstance(

        signature_result,

        dict

    ):

        return {

            "score": 0.0,

            "signals": []

        }


    verdict = str(

        signature_result.get(

            "verdict",

            ""

        )

    ).lower()


    similarity = normalize_score(

        signature_result.get(

            "similarity",

            0.0

        )

    )


    detected_signals = []


    # -----------------------------------------
    # Potential Forgery
    # -----------------------------------------

    if (

        "forgery"

        in

        verdict

    ):

        detected_signals.append(

            "Signature verification indicates potential forgery"

        )


        score = 0.90


    elif similarity < 0.5:

        detected_signals.append(

            "Low signature similarity detected"

        )


        score = 0.75


    else:

        score = 0.0


    return {

        "score":

            round(

                score,

                4

            ),

        "signals":

            detected_signals

    }


# ============================================================
# VIDEO RISK ANALYSIS
# ============================================================

def analyze_video_risk(
    video_result: Dict[str, Any]
) -> Dict[str, Any]:

    """
    Video analysis adapter.

    Your current video analyzer structure has not been
    provided yet, so this function is intentionally flexible.

    It checks common fields such as:

        fraud_score
        forensic_score
        manipulation_score
        deepfake_score
        tampering_detected
        manipulated
        verdict

    Once you send the actual video analyzer response,
    we can make this adapter precise.
    """

    if not isinstance(

        video_result,

        dict

    ):

        return {

            "score": 0.0,

            "signals": []

        }


    detected_signals = []


    # -----------------------------------------
    # Score
    # -----------------------------------------

    score = max(

        normalize_score(

            video_result.get(

                "fraud_score",

                0.0

            )

        ),

        normalize_score(

            video_result.get(

                "forensic_score",

                0.0

            )

        ),

        normalize_score(

            video_result.get(

                "manipulation_score",

                0.0

            )

        ),

        normalize_score(

            video_result.get(

                "deepfake_score",

                0.0

            )

        )

    )


    # -----------------------------------------
    # Manipulation Detection
    # -----------------------------------------

    manipulation_detected = (

        safe_bool(

            video_result.get(

                "tampering_detected",

                False

            )

        )

        or

        safe_bool(

            video_result.get(

                "manipulated",

                False

            )

        )

    )


    if manipulation_detected:

        detected_signals.append(

            "Video manipulation detected"

        )


        score = max(

            score,

            0.80

        )


    # -----------------------------------------
    # Verdict
    # -----------------------------------------

    verdict = str(

        video_result.get(

            "verdict",

            ""

        )

    ).lower()


    if (

        "fake"

        in

        verdict

        or

        "forg"

        in

        verdict

        or

        "manipulat"

        in

        verdict

    ):

        detected_signals.append(

            "Video analysis indicates possible manipulation"

        )


        score = max(

            score,

            0.75

        )


    return {

        "score":

            round(

                score,

                4

            ),

        "signals":

            detected_signals

    }


# ============================================================
# UNIFIED FRAUD RISK ENGINE
# ============================================================

def calculate_unified_risk(
    image_result=None,
    document_result=None,
    signature_result=None,
    video_result=None
):

    """
    Combine all available forensic analysis results.

    Each modality contributes only when its result
    is available.

    The score is calculated using weighted evidence.

    The weights are dynamically normalized based on
    available modalities.
    """

    modality_results = []


    # -----------------------------------------
    # IMAGE
    # -----------------------------------------

    if image_result:

        image_risk = analyze_image_risk(

            image_result

        )


        modality_results.append({

            "name":
                "Image Forensics",

            "score":
                image_risk["score"],

            "signals":
                image_risk["signals"],

            "weight":
                0.30

        })


    # -----------------------------------------
    # DOCUMENT
    # -----------------------------------------

    if document_result:

        document_risk = analyze_document_risk(

            document_result

        )


        modality_results.append({

            "name":
                "Document Forensics",

            "score":
                document_risk["score"],

            "signals":
                document_risk["signals"],

            "weight":
                0.25

        })


    # -----------------------------------------
    # SIGNATURE
    # -----------------------------------------

    if signature_result:

        signature_risk = analyze_signature_risk(

            signature_result

        )


        modality_results.append({

            "name":
                "Signature Verification",

            "score":
                signature_risk["score"],

            "signals":
                signature_risk["signals"],

            "weight":
                0.20

        })


    # -----------------------------------------
    # VIDEO
    # -----------------------------------------

    if video_result:

        video_risk = analyze_video_risk(

            video_result

        )


        modality_results.append({

            "name":
                "Video Analytics",

            "score":
                video_risk["score"],

            "signals":
                video_risk["signals"],

            "weight":
                0.25

        })


    # ========================================================
    # NO RESULTS
    # ========================================================

    if not modality_results:

        return {

            "fraud_score":
                0,

            "risk_level":
                "UNKNOWN",

            "verdict":
                "Insufficient Evidence",

            "signals":
                [],

            "modalities":
                [],

            "explanation":
                "No forensic analysis results were provided."

        }


    # ========================================================
    # WEIGHT NORMALIZATION
    # ========================================================

    total_weight = sum(

        item["weight"]

        for item in modality_results

    )


    if total_weight <= 0:

        total_weight = 1.0


    # ========================================================
    # CALCULATE WEIGHTED SCORE
    # ========================================================

    weighted_score = sum(

        item["score"]

        *

        item["weight"]

        for item in modality_results

    )


    weighted_score = (

        weighted_score

        /

        total_weight

    )


    fraud_score = round(

        weighted_score * 100,

        2

    )


    # ========================================================
    # COLLECT SIGNALS
    # ========================================================

    all_signals = []


    for item in modality_results:

        for signal in item["signals"]:

            all_signals.append(

                f"{item['name']}: {signal}"

            )


    # ========================================================
    # RISK LEVEL
    # ========================================================

    if fraud_score >= 70:

        risk_level = "HIGH"

        verdict = (

            "Potentially Manipulated Evidence"

        )


    elif fraud_score >= 40:

        risk_level = "MEDIUM"

        verdict = (

            "Suspicious Evidence"

        )


    else:

        risk_level = "LOW"

        verdict = (

            "Likely Authentic Evidence"

        )


    # ========================================================
    # EXPLANATION
    # ========================================================

    if all_signals:

        explanation = (

            "The unified assessment identified "

            f"{len(all_signals)} suspicious forensic "

            "indicator(s) across the available "

            "analysis modalities."

        )

    else:

        explanation = (

            "No significant suspicious forensic "

            "indicators were identified by the "

            "available analysis modules."

        )


    # ========================================================
    # MODALITY SUMMARY
    # ========================================================

    modality_summary = []


    for item in modality_results:

        modality_summary.append({

            "name":
                item["name"],

            "risk_score":
                round(

                    item["score"] * 100,

                    2

                ),

            "signals":
                item["signals"]

        })


    # ========================================================
    # FINAL RESULT
    # ========================================================

    result = {

        "fraud_score":
            fraud_score,

        "risk_level":
            risk_level,

        "verdict":
            verdict,

        "signals":
            all_signals,

        "modalities":
            modality_summary,

        "explanation":
            explanation

    }


    # ========================================================
    # DEBUG
    # ========================================================

    print(

        "\n========== UNIFIED FRAUD RISK =========="

    )


    print(

        "Fraud Score:",

        fraud_score

    )


    print(

        "Risk Level:",

        risk_level

    )


    print(

        "Verdict:",

        verdict

    )


    print(

        "Signals:",

        all_signals

    )


    print(

        "========================================\n"

    )


    return result