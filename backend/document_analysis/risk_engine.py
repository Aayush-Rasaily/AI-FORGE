from pathlib import Path


from backend.analysis.image_forensics import (
    analyze_image
)

from backend.analysis.copy_move import (
    detect_copy_move
)

from backend.analysis.metadata_analysis import (
    analyze_metadata
)

from backend.analysis.noise_analysis import (
    analyze_noise
)


from backend.document_analysis.font_consistency import (
    analyze_font_consistency
)

from backend.document_analysis.spacing_analysis import (
    analyze_spacing
)

from backend.document_analysis.region_anomaly import (
    analyze_region_anomaly
)

from backend.document_analysis.text_layout_analysis import (
    analyze_text_layout
)


from backend.document_analysis.evidence import (
    Evidence
)

from backend.document_analysis.evidence_fusion import (
    fuse_evidence
)


# ==========================================
# SAFE FLOAT
# ==========================================

def safe_float(

    value,

    default=0.0

):

    try:

        return float(value)

    except (

        TypeError,

        ValueError

    ):

        return default


# ==========================================
# SAFE BOOL
# ==========================================

def safe_bool(

    value

):

    return bool(value)


# ==========================================
# MAIN RISK ENGINE
# ==========================================

def analyze_document_risk(

    image_path,

    analysis_dir

):

    image_path = Path(

        image_path

    )

    analysis_dir = Path(

        analysis_dir

    )


    if not image_path.exists():

        raise FileNotFoundError(

            f"Image not found: {image_path}"

        )


    analysis_dir.mkdir(

        parents=True,

        exist_ok=True

    )


    print()

    print(

        "========== RISK ENGINE START =========="

    )


    # ======================================
    # 1. IMAGE FORENSICS
    # ======================================

    forensic = analyze_image(

        str(image_path),

        str(analysis_dir)

    )


    signals = forensic.get(

        "signals",

        {}

    )


    ela = safe_float(

        signals.get(

            "ela_score",

            0

        )

    )


    wavelet = safe_float(

        signals.get(

            "wavelet_score",

            0

        )

    )


    # ======================================
    # 2. COPY MOVE
    # ======================================

    copy_move = detect_copy_move(

        str(image_path),

        analysis_dir

    )


    copy_move_detected = safe_bool(

        copy_move.get(

            "copy_move_detected",

            copy_move.get(

                "detected",

                False

            )

        )

    )


    copy_move_score = safe_float(

        copy_move.get(

            "copy_move_score",

            copy_move.get(

                "score",

                0

            )

        )

    )


    if copy_move_detected:

        copy_move_score = max(

            copy_move_score,

            0.85

        )


    # ======================================
    # 3. METADATA
    # ======================================

    metadata = analyze_metadata(

        str(image_path)

    )


    metadata_suspicious = (

        metadata.get(

            "suspicious",

            False

        )

    )


    metadata_score = (

        0.85

        if metadata_suspicious

        else 0.0

    )


    # ======================================
    # 4. NOISE
    # ======================================

    noise = analyze_noise(

        str(image_path)

    )


    noise_inconsistency = safe_float(

        noise.get(

            "noise_inconsistency",

            0

        )

    )


    # Convert inconsistency into
    # normalized suspicion score.

    noise_score = min(

        noise_inconsistency / 0.50,

        1.0

    )


    # ======================================
    # 5. TEXT LAYOUT
    # ======================================

    layout = analyze_text_layout(

        str(image_path)

    )


    # ======================================
    # 6. FONT
    # ======================================

    font = analyze_font_consistency(

        str(image_path)

    )


    suspicious_font_count = len(

        font.get(

            "suspicious_words",

            []

        )

    )


    total_words = max(

        font.get(

            "total_words",

            1

        ),

        1

    )


    font_score = min(

        suspicious_font_count

        /

        max(

            total_words * 0.10,

            1

        ),

        1.0

    )


    # ======================================
    # 7. SPACING
    # ======================================

    spacing = analyze_spacing(

        str(image_path)

    )


    spacing_risk = safe_float(

        spacing.get(

            "risk_score",

            0

        )

    )


    spacing_score = min(

        spacing_risk / 100,

        1.0

    )


    # ======================================
    # 8. REGION
    # ======================================

    regions = analyze_region_anomaly(

        str(image_path)

    )


    region_score = safe_float(

        regions.get(

            "overall_score",

            0

        )

    )


    region_score = min(

        region_score / 100,

        1.0

    )


    high_risk_regions = len(

        regions.get(

            "high_risk_regions",

            []

        )

    )


    # ======================================
    # EVIDENCE COLLECTION
    # ======================================

    evidence = []


    # ======================================
    # ELA
    # ======================================

    if ela > 0:

        evidence.append(

            Evidence(

                module="ELA",

                score=min(

                    ela,

                    1.0

                ),

                confidence=0.70,

                severity=get_severity(

                    ela

                ),

                reason=(

                    "JPEG Error Level Analysis "

                    "indicates possible local "

                    "compression inconsistency."

                )

            )

        )


    # ======================================
    # WAVELET
    # ======================================

    if wavelet > 0:

        evidence.append(

            Evidence(

                module="Wavelet",

                score=min(

                    wavelet,

                    1.0

                ),

                confidence=0.65,

                severity=get_severity(

                    wavelet

                ),

                reason=(

                    "Wavelet frequency analysis "

                    "detected possible texture "

                    "or frequency inconsistency."

                )

            )

        )


    # ======================================
    # COPY MOVE
    # ======================================

    if copy_move_detected:

        evidence.append(

            Evidence(

                module="CopyMove",

                score=copy_move_score,

                confidence=0.90,

                severity="CRITICAL",

                reason=(

                    "Repeated image regions were "

                    "detected using copy-move analysis."

                )

            )

        )


    # ======================================
    # METADATA
    # ======================================

    if metadata_suspicious:

        evidence.append(

            Evidence(

                module="Metadata",

                score=metadata_score,

                confidence=0.75,

                severity="HIGH",

                reason=(

                    "Image metadata contains "

                    "software associated with "

                    "image editing."

                )

            )

        )


    # ======================================
    # NOISE
    # ======================================

    if noise_score > 0.20:

        evidence.append(

            Evidence(

                module="Noise",

                score=noise_score,

                confidence=0.60,

                severity=get_severity(

                    noise_score

                ),

                reason=(

                    "Spatial noise distribution "

                    "shows possible inconsistency "

                    "between image regions."

                )

            )

        )


    # ======================================
    # FONT
    # ======================================

    if font_score > 0.20:

        evidence.append(

            Evidence(

                module="Font",

                score=font_score,

                confidence=0.55,

                severity=get_severity(

                    font_score

                ),

                reason=(

                    f"{suspicious_font_count} "

                    "text regions show possible "

                    "font or rendering inconsistency."

                )

            )

        )


    # ======================================
    # SPACING
    # ======================================

    if spacing_score > 0.20:

        evidence.append(

            Evidence(

                module="Spacing",

                score=spacing_score,

                confidence=0.60,

                severity=get_severity(

                    spacing_score

                ),

                reason=(

                    "Text spacing or alignment "

                    "patterns differ from the "

                    "dominant document layout."

                )

            )

        )


    # ======================================
    # REGION
    # ======================================

    if region_score > 0.20:

        evidence.append(

            Evidence(

                module="Region",

                score=region_score,

                confidence=0.60,

                severity=get_severity(

                    region_score

                ),

                reason=(

                    f"{high_risk_regions} "

                    "regions show combined "

                    "forensic anomalies."

                )

            )

        )


    # ======================================
    # FUSE EVIDENCE
    # ======================================

    fusion = fuse_evidence(

        evidence

    )


    risk_score = fusion[

        "risk_score"

    ]


    confidence = fusion[

        "confidence"

    ]


    evidence_coverage = fusion[

        "evidence_coverage"

    ]


    # ======================================
    # FINAL VERDICT
    # ======================================

    if risk_score >= 80:

        verdict = "CRITICAL RISK"

        recommendation = (

            "Strong multi-signal evidence "

            "of possible document manipulation. "

            "Manual forensic verification is "

            "strongly recommended."

        )


    elif risk_score >= 60:

        verdict = "HIGH RISK"

        recommendation = (

            "Multiple forensic signals indicate "

            "possible manipulation. "

            "Manual verification recommended."

        )


    elif risk_score >= 35:

        verdict = "MEDIUM RISK"

        recommendation = (

            "Some suspicious signals were detected. "

            "Additional verification is recommended."

        )


    elif risk_score >= 15:

        verdict = "LOW RISK"

        recommendation = (

            "Minor forensic anomalies were detected, "

            "but evidence is insufficient to confirm "

            "manipulation."

        )


    else:

        verdict = "NO SIGNIFICANT ANOMALY"

        recommendation = (

            "No significant forensic evidence "

            "of manipulation was detected."

        )


    # ======================================
    # RESULT
    # ======================================

    result = {

        "risk_score":

            risk_score,

        "confidence":

            confidence,

        "evidence_coverage":

            evidence_coverage,

        "overall_verdict":

            verdict,

        "recommendation":

            recommendation,

        "findings":

            fusion["findings"],

        "evidence":

            fusion["evidence"],

        "signals": {

            "ela":

                ela,

            "wavelet":

                wavelet,

            "copy_move":

                copy_move_detected,

            "copy_move_score":

                copy_move_score,

            "noise":

                noise_inconsistency,

            "metadata":

                metadata_suspicious,

            "font":

                suspicious_font_count,

            "spacing":

                spacing_score,

            "regions":

                high_risk_regions

        },

        "raw_analysis": {

            "forensic":

                forensic,

            "copy_move":

                copy_move,

            "metadata":

                metadata,

            "noise":

                noise,

            "layout":

                layout,

            "font":

                font,

            "spacing":

                spacing,

            "regions":

                regions

        }

    }


    # ======================================
    # DEBUG
    # ======================================

    print(

        "Risk Score:",

        risk_score

    )

    print(

        "Confidence:",

        confidence

    )

    print(

        "Evidence Coverage:",

        evidence_coverage

    )

    print(

        "Verdict:",

        verdict

    )

    print(

        "Evidence Modules:",

        len(evidence)

    )

    print(

        "Findings:",

        len(

            fusion["findings"]

        )

    )

    print(

        "======================================"

    )

    print()

    from backend.document_analysis.evidence_fusion import make_json_serializable

    result = make_json_serializable(result)

    return result


# ==========================================
# SEVERITY HELPER
# ==========================================

def get_severity(

    score

):

    if score >= 0.80:

        return "CRITICAL"

    elif score >= 0.60:

        return "HIGH"

    elif score >= 0.35:

        return "MEDIUM"

    return "LOW"