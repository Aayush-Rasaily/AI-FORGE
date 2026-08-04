"""
AI-FORGE Risk Intelligence
==========================

This module converts forensic evidence into a final risk assessment.

IMPORTANT ARCHITECTURE RULE
---------------------------

This file MUST NOT import:

    evidence_fusion.py

That would create:

    evidence_fusion
        -> risk_intelligence
            -> evidence_fusion

which causes a circular import.

Instead:

    evidence_fusion
        -> risk_intelligence

This module is completely independent.
"""

from typing import Any


# ================================================================
# JSON SERIALIZATION
# ================================================================

def make_json_serializable(value: Any) -> Any:
    """
    Recursively converts NumPy, Torch and other values
    into standard Python JSON-compatible values.
    """

    if value is None:
        return None

    # ------------------------------------------------------------
    # Native Python values
    # ------------------------------------------------------------

    if isinstance(
        value,
        (
            str,
            int,
            float,
            bool
        )
    ):
        return value

    # ------------------------------------------------------------
    # NumPy
    # ------------------------------------------------------------

    try:

        import numpy as np

        if isinstance(
            value,
            np.integer
        ):
            return int(
                value
            )

        if isinstance(
            value,
            np.floating
        ):
            return float(
                value
            )

        if isinstance(
            value,
            np.bool_
        ):
            return bool(
                value
            )

        if isinstance(
            value,
            np.ndarray
        ):
            return [
                make_json_serializable(
                    item
                )
                for item in value.tolist()
            ]

    except ImportError:
        pass

    # ------------------------------------------------------------
    # PyTorch
    # ------------------------------------------------------------

    try:

        import torch

        if isinstance(
            value,
            torch.Tensor
        ):

            if value.numel() == 1:

                return make_json_serializable(
                    value.detach()
                    .cpu()
                    .item()
                )

            return make_json_serializable(
                value.detach()
                .cpu()
                .tolist()
            )

    except ImportError:
        pass

    # ------------------------------------------------------------
    # Dictionary
    # ------------------------------------------------------------

    if isinstance(
        value,
        dict
    ):

        return {

            str(key):
                make_json_serializable(
                    val
                )

            for key, val
            in value.items()

        }

    # ------------------------------------------------------------
    # List
    # ------------------------------------------------------------

    if isinstance(
        value,
        list
    ):

        return [

            make_json_serializable(
                item
            )

            for item
            in value

        ]

    # ------------------------------------------------------------
    # Tuple
    # ------------------------------------------------------------

    if isinstance(
        value,
        tuple
    ):

        return [

            make_json_serializable(
                item
            )

            for item
            in value

        ]

    # ------------------------------------------------------------
    # Set
    # ------------------------------------------------------------

    if isinstance(
        value,
        set
    ):

        return [

            make_json_serializable(
                item
            )

            for item
            in value

        ]

    # ------------------------------------------------------------
    # Objects with item()
    # ------------------------------------------------------------

    if hasattr(
        value,
        "item"
    ):

        try:

            return make_json_serializable(
                value.item()
            )

        except Exception:
            pass

    # ------------------------------------------------------------
    # Objects with tolist()
    # ------------------------------------------------------------

    if hasattr(
        value,
        "tolist"
    ):

        try:

            return make_json_serializable(
                value.tolist()
            )

        except Exception:
            pass

    # ------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------

    return str(
        value
    )


# ================================================================
# SAFE FLOAT
# ================================================================

def safe_float(
    value,
    default=0.0
):

    try:

        result = float(
            value
        )

        if result != result:
            return default

        return result

    except Exception:

        return default


# ================================================================
# NORMALIZE EVIDENCE
# ================================================================

def normalize_evidence(
    evidence_list
):

    normalized = []

    if evidence_list is None:

        return normalized

    for evidence in evidence_list:

        # --------------------------------------------------------
        # Evidence object with to_dict()
        # --------------------------------------------------------

        if hasattr(
            evidence,
            "to_dict"
        ):

            try:

                evidence = evidence.to_dict()

            except Exception:

                continue

        # --------------------------------------------------------
        # Ignore invalid values
        # --------------------------------------------------------

        if not isinstance(
            evidence,
            dict
        ):

            continue

        # --------------------------------------------------------
        # Extract values
        # --------------------------------------------------------

        module = str(
            evidence.get(
                "module",
                "Unknown"
            )
        )

        score = safe_float(
            evidence.get(
                "score",
                0.0
            )
        )

        confidence = safe_float(
            evidence.get(
                "confidence",
                0.0
            )
        )

        severity = str(
            evidence.get(
                "severity",
                "LOW"
            )
        ).upper()

        reason = str(
            evidence.get(
                "reason",
                ""
            )
        )

        location = evidence.get(
            "location"
        )

        # --------------------------------------------------------
        # Clamp values
        # --------------------------------------------------------

        score = max(
            0.0,
            min(
                1.0,
                score
            )
        )

        confidence = max(
            0.0,
            min(
                1.0,
                confidence
            )
        )

        # --------------------------------------------------------
        # Append normalized evidence
        # --------------------------------------------------------

        normalized.append(

            {

                "module":
                    module,

                "score":
                    score,

                "confidence":
                    confidence,

                "severity":
                    severity,

                "reason":
                    reason,

                "location":
                    location

            }

        )

    return normalized


# ================================================================
# MAIN RISK INTELLIGENCE FUNCTION
# ================================================================

def analyze_risk_intelligence(
    evidence_list
):
    """
    Analyze a collection of forensic evidence findings.

    This function ALWAYS returns a dictionary containing:

        verdict
        forensic_score
        risk_score
        confidence
        evidence_coverage
        findings
        evidence

    This guarantees that the frontend receives the
    expected fields.
    """

    # ------------------------------------------------------------
    # Normalize input
    # ------------------------------------------------------------

    evidence = normalize_evidence(
        evidence_list
    )

    # ------------------------------------------------------------
    # Empty evidence
    # ------------------------------------------------------------

    if not evidence:

        return {

            "verdict":
                "INSUFFICIENT EVIDENCE",

            "forensic_score":
                0.0,

            "risk_score":
                0.0,

            "confidence":
                0,

            "evidence_coverage":
                0.0,

            "recommendation":
                "Insufficient forensic evidence is available for a reliable risk assessment.",

            "findings":
                [],

            "evidence":
                []

        }

    # ------------------------------------------------------------
    # Calculate weighted score
    #
    # score × confidence
    # ------------------------------------------------------------

    weighted_scores = []

    confidence_values = []

    for item in evidence:

        score = item[
            "score"
        ]

        confidence = item[
            "confidence"
        ]

        weighted_score = (

            score
            *
            confidence

        )

        weighted_scores.append(
            weighted_score
        )

        confidence_values.append(
            confidence
        )

    # ------------------------------------------------------------
    # Final forensic score
    # ------------------------------------------------------------

    if weighted_scores:

        total_weight = sum(
            confidence_values
        )

        if total_weight > 0:

            forensic_score = (

                sum(
                    weighted_scores
                )

                /

                total_weight

            )

        else:

            forensic_score = 0.0

    else:

        forensic_score = 0.0

    forensic_score = max(
        0.0,
        min(
            1.0,
            forensic_score
        )
    )

    # ------------------------------------------------------------
    # Risk score 0-100
    # ------------------------------------------------------------

    risk_score = (

        forensic_score
        *
        100.0

    )

    # ------------------------------------------------------------
    # Overall confidence
    # ------------------------------------------------------------

    if confidence_values:

        average_confidence = (

            sum(
                confidence_values
            )

            /

            len(
                confidence_values
            )

        )

    else:

        average_confidence = 0.0

    confidence = round(

        average_confidence
        *
        100

    )

    # ------------------------------------------------------------
    # Evidence coverage
    #
    # Measures how many evidence modules contributed.
    #
    # We use unique module names.
    # ------------------------------------------------------------

    modules = set(

        item[
            "module"
        ]

        for item
        in evidence

    )

    evidence_coverage = min(

        1.0,

        len(
            modules
        )
        /
        8.0

    )

    # ------------------------------------------------------------
    # Determine verdict
    # ------------------------------------------------------------

    if risk_score >= 80:

        verdict = (
            "HIGH RISK - STRONG FORENSIC ANOMALIES"
        )

        recommendation = (

            "Multiple strong forensic indicators "
            "suggest potential manipulation. "
            "Manual forensic review is strongly recommended."

        )

    elif risk_score >= 60:

        verdict = (
            "SUSPICIOUS"
        )

        recommendation = (

            "Several forensic anomalies were detected. "
            "Additional evidence and manual review are recommended."

        )

    elif risk_score >= 35:

        verdict = (
            "MEDIUM RISK - POSSIBLE ANOMALIES"
        )

        recommendation = (

            "Some forensic anomalies were detected. "
            "The available evidence is not sufficient "
            "to confirm manipulation."

        )

    elif risk_score >= 15:

        verdict = (
            "LOW RISK - MINOR ANOMALIES"
        )

        recommendation = (

            "Some weak forensic anomalies were detected, "
            "but the available evidence is not sufficient "
            "to confirm manipulation."

        )

    else:

        verdict = (
            "LOW RISK - NO SIGNIFICANT ANOMALIES"
        )

        recommendation = (

            "No significant forensic manipulation indicators "
            "were detected in the available evidence."

        )

    # ============================================================
    # BUILD FINDINGS
    # ============================================================

    findings = []

    for item in evidence:

        severity = item[
            "severity"
        ]

        score = item[
            "score"
        ]

        # --------------------------------------------------------
        # Only include meaningful findings
        # --------------------------------------------------------

        if (

            severity in [
                "MEDIUM",
                "HIGH",
                "CRITICAL"
            ]

            or

            score >= 0.5

        ):

            findings.append(

                {

                    "module":
                        item[
                            "module"
                        ],

                    "severity":
                        severity,

                    "reason":
                        item[
                            "reason"
                        ],

                    "score":
                        round(
                            score,
                            4
                        ),

                    "confidence":
                        round(
                            item[
                                "confidence"
                            ],
                            4
                        ),

                    "location":
                        item[
                            "location"
                        ]

                }

            )

    # ============================================================
    # FINAL RESULT
    # ============================================================

    result = {

        "verdict":
            verdict,

        "forensic_score":
            round(
                forensic_score,
                4
            ),

        "risk_score":
            round(
                risk_score,
                2
            ),

        "confidence":
            int(
                confidence
            ),

        "evidence_coverage":
            round(
                evidence_coverage,
                4
            ),

        "recommendation":
            recommendation,

        "findings":
            findings,

        "evidence":
            evidence

    }

    # ------------------------------------------------------------
    # Final serialization safety
    # ------------------------------------------------------------

    return make_json_serializable(
        result
    )


# ================================================================
# EXPORTS
# ================================================================

__all__ = [

    "analyze_risk_intelligence",

    "make_json_serializable",

    "normalize_evidence"

]