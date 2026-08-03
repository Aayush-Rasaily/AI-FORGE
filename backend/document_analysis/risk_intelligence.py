from typing import List, Dict, Any

from backend.document_analysis.evidence import Evidence


# ============================================================
# RISK INTELLIGENCE ENGINE
# ============================================================
#
# Purpose:
# Convert multiple forensic signals into a single
# explainable risk assessment.
#
# This layer does NOT replace forensic detectors.
# It combines their outputs.
#
# ============================================================


# ============================================================
# SIGNAL GROUPS
# ============================================================

DOCUMENT_SIGNALS = {
    "Font",
    "Spacing",
    "Region",
    "OCR"
}

IMAGE_SIGNALS = {
    "ELA",
    "Wavelet",
    "CopyMove",
    "Noise",
    "Metadata"
}


# ============================================================
# SEVERITY WEIGHTS
# ============================================================

SEVERITY_WEIGHT = {

    "LOW": 1.0,

    "MEDIUM": 1.15,

    "HIGH": 1.35,

    "CRITICAL": 1.60

}


# ============================================================
# CLAMP
# ============================================================

def clamp(
    value,
    minimum=0.0,
    maximum=100.0
):

    return max(

        minimum,

        min(

            maximum,

            value

        )

    )


# ============================================================
# NORMALIZE EVIDENCE
# ============================================================

def normalize_evidence(
    evidence_list: List[Evidence]
):

    normalized = []

    for evidence in evidence_list:

        score = float(

            evidence.score

        )

        confidence = float(

            evidence.confidence

        )

        severity = (

            evidence.severity

            or

            "LOW"

        ).upper()

        severity_factor = (

            SEVERITY_WEIGHT.get(

                severity,

                1.0

            )

        )

        # ----------------------------------------------------
        # Base contribution
        # ----------------------------------------------------

        contribution = (

            score

            *

            confidence

            *

            severity_factor

        )

        normalized.append({

            "module":

                evidence.module,

            "score":

                score,

            "confidence":

                confidence,

            "severity":

                severity,

            "reason":

                evidence.reason,

            "location":

                evidence.location,

            "contribution":

                contribution

        })

    return normalized


# ============================================================
# CALCULATE BASE RISK
# ============================================================

def calculate_base_risk(
    evidence
):

    if not evidence:

        return 0.0

    total_weight = 0.0

    weighted_score = 0.0

    # Equal base contribution for each
    # available evidence source.
    #
    # This avoids over-relying on a single
    # detector.

    for ev in evidence:

        weight = 1.0

        weighted_score += (

            ev["score"]

            *

            ev["confidence"]

            *

            ev["severity_factor"]

            if "severity_factor" in ev

            else

            ev["contribution"]

        )

        total_weight += weight

    if total_weight == 0:

        return 0.0

    # Normalize approximately to 0-100

    average = (

        weighted_score

        /

        total_weight

    )

    return clamp(

        average * 100

    )


# ============================================================
# STRONG SIGNAL ANALYSIS
# ============================================================

def analyze_strong_signals(
    evidence
):

    strong_signals = []

    for ev in evidence:

        effective_score = (

            ev["score"]

            *

            ev["confidence"]

        )

        if effective_score >= 0.60:

            strong_signals.append(

                ev

            )

    return strong_signals


# ============================================================
# SIGNAL DIVERSITY
# ============================================================

def calculate_signal_diversity(
    evidence
):

    active_modules = [

        ev["module"]

        for ev in evidence

        if (

            ev["score"]

            *

            ev["confidence"]

        ) >= 0.40

    ]

    unique_modules = set(

        active_modules

    )

    return len(

        unique_modules

    )


# ============================================================
# DOCUMENT CORRELATION
# ============================================================

def calculate_document_correlation(
    evidence
):

    document_hits = 0

    for ev in evidence:

        if ev["module"] in DOCUMENT_SIGNALS:

            effective_score = (

                ev["score"]

                *

                ev["confidence"]

            )

            if effective_score >= 0.40:

                document_hits += 1

    # Multiple document-level anomalies
    # reinforce each other.

    if document_hits >= 3:

        return 20.0

    if document_hits == 2:

        return 12.0

    if document_hits == 1:

        return 4.0

    return 0.0


# ============================================================
# IMAGE CORRELATION
# ============================================================

def calculate_image_correlation(
    evidence
):

    image_hits = 0

    for ev in evidence:

        if ev["module"] in IMAGE_SIGNALS:

            effective_score = (

                ev["score"]

                *

                ev["confidence"]

            )

            if effective_score >= 0.40:

                image_hits += 1

    if image_hits >= 3:

        return 15.0

    if image_hits == 2:

        return 8.0

    if image_hits == 1:

        return 3.0

    return 0.0


# ============================================================
# STRONG SIGNAL BOOST
# ============================================================

def calculate_strong_signal_boost(
    strong_signals
):

    if not strong_signals:

        return 0.0

    count = len(

        strong_signals

    )

    if count >= 4:

        return 20.0

    if count == 3:

        return 15.0

    if count == 2:

        return 10.0

    if count == 1:

        return 5.0

    return 0.0


# ============================================================
# FINDINGS
# ============================================================

def build_findings(
    evidence
):

    findings = []

    for ev in evidence:

        effective_score = (

            ev["score"]

            *

            ev["confidence"]

        )

        if effective_score >= 0.70:

            findings.append({

                "module":

                    ev["module"],

                "severity":

                    "HIGH",

                "reason":

                    ev["reason"],

                "score":

                    round(

                        ev["score"],

                        4

                    ),

                "confidence":

                    round(

                        ev["confidence"],

                        4

                    ),

                "location":

                    ev["location"]

            })

        elif effective_score >= 0.40:

            findings.append({

                "module":

                    ev["module"],

                "severity":

                    "MEDIUM",

                "reason":

                    ev["reason"],

                "score":

                    round(

                        ev["score"],

                        4

                    ),

                "confidence":

                    round(

                        ev["confidence"],

                        4

                    ),

                "location":

                    ev["location"]

            })

    return findings


# ============================================================
# FINAL VERDICT
# ============================================================

def determine_verdict(
    risk_score
):

    if risk_score >= 80:

        return (

            "HIGH RISK - STRONG EVIDENCE"

        )

    elif risk_score >= 60:

        return (

            "MEDIUM-HIGH RISK - MULTIPLE ANOMALIES"

        )

    elif risk_score >= 40:

        return (

            "MEDIUM RISK - MANUAL VERIFICATION"

        )

    elif risk_score >= 20:

        return (

            "LOW RISK - MINOR ANOMALIES"

        )

    return (

        "AUTHENTIC - NO SIGNIFICANT ANOMALY"

    )


# ============================================================
# RECOMMENDATION
# ============================================================

def generate_recommendation(
    risk_score,
    strong_signal_count,
    diversity
):

    if risk_score >= 80:

        return (

            "Multiple independent forensic signals indicate "

            "a high probability of manipulation. Evidence "

            "should be escalated for detailed forensic review."

        )

    if risk_score >= 60:

        return (

            "Several independent anomalies were detected. "

            "Manual verification and additional evidence "

            "should be requested before accepting the document."

        )

    if risk_score >= 40:

        return (

            "Moderate forensic anomalies were detected. "

            "The evidence should undergo manual verification."

        )

    if risk_score >= 20:

        return (

            "Some weak forensic anomalies were detected, "

            "but the available evidence is not sufficient "

            "to confirm manipulation."

        )

    return (

        "No significant forensic anomaly was detected. "

        "The evidence appears consistent with an authentic "

        "document, although automated analysis cannot "

        "guarantee authenticity."

    )


# ============================================================
# CONFIDENCE
# ============================================================

def calculate_confidence(
    evidence,
    diversity
):

    if not evidence:

        return 50.0

    confidence_values = [

        ev["confidence"]

        for ev in evidence

    ]

    average_confidence = (

        sum(confidence_values)

        /

        len(confidence_values)

    )

    # Evidence diversity improves confidence.

    diversity_bonus = min(

        diversity * 3,

        15

    )

    confidence = (

        average_confidence * 70

        +

        diversity_bonus

        +

        15

    )

    return round(

        clamp(

            confidence,

            50,

            99.9

        ),

        2

    )


# ============================================================
# MAIN RISK INTELLIGENCE FUNCTION
# ============================================================

def analyze_risk_intelligence(
    evidence_list: List[Evidence]
) -> Dict[str, Any]:

    print()

    print(

        "========== RISK INTELLIGENCE =========="

    )

    print(

        "Evidence sources:",

        len(evidence_list)

    )

    # --------------------------------------------------------
    # Normalize
    # --------------------------------------------------------

    evidence = normalize_evidence(

        evidence_list

    )

    # --------------------------------------------------------
    # Base risk
    # --------------------------------------------------------

    base_risk = calculate_base_risk(

        evidence

    )

    # --------------------------------------------------------
    # Strong signals
    # --------------------------------------------------------

    strong_signals = analyze_strong_signals(

        evidence

    )

    strong_boost = calculate_strong_signal_boost(

        strong_signals

    )

    # --------------------------------------------------------
    # Signal diversity
    # --------------------------------------------------------

    diversity = calculate_signal_diversity(

        evidence

    )

    # --------------------------------------------------------
    # Correlation
    # --------------------------------------------------------

    document_boost = (

        calculate_document_correlation(

            evidence

        )

    )

    image_boost = (

        calculate_image_correlation(

            evidence

        )

    )

    # --------------------------------------------------------
    # Final risk
    # --------------------------------------------------------

    final_score = (

        base_risk

        +

        strong_boost

        +

        document_boost

        +

        image_boost

    )

    final_score = round(

        clamp(

            final_score

        ),

        2

    )

    # --------------------------------------------------------
    # Verdict
    # --------------------------------------------------------

    verdict = determine_verdict(

        final_score

    )

    # --------------------------------------------------------
    # Confidence
    # --------------------------------------------------------

    confidence = calculate_confidence(

        evidence,

        diversity

    )

    # --------------------------------------------------------
    # Findings
    # --------------------------------------------------------

    findings = build_findings(

        evidence

    )

    # --------------------------------------------------------
    # Recommendation
    # --------------------------------------------------------

    recommendation = (

        generate_recommendation(

            final_score,

            len(strong_signals),

            diversity

        )

    )

    print(

        "Base Risk:",

        round(base_risk, 2)

    )

    print(

        "Strong Signal Boost:",

        strong_boost

    )

    print(

        "Document Correlation:",

        document_boost

    )

    print(

        "Image Correlation:",

        image_boost

    )

    print(

        "Signal Diversity:",

        diversity

    )

    print(

        "Final Risk:",

        final_score

    )

    print(

        "Verdict:",

        verdict

    )

    print(

        "Confidence:",

        confidence

    )

    print(

        "========================================"

    )

    print()

    return {

        "risk_score":

            final_score,

        "forensic_score":

            round(

                final_score / 100,

                4

            ),

        "confidence":

            confidence,

        "overall_verdict":

            verdict,

        "recommendation":

            recommendation,

        "findings":

            findings,

        "risk_breakdown": {

            "base_risk":

                round(

                    base_risk,

                    2

                ),

            "strong_signal_boost":

                strong_boost,

            "document_correlation_boost":

                document_boost,

            "image_correlation_boost":

                image_boost,

            "signal_diversity":

                diversity,

            "strong_signal_count":

                len(

                    strong_signals

                )

        },

        "evidence":

            evidence

    }