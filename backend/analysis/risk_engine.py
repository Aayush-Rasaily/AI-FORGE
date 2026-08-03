from pathlib import Path

from backend.analysis.image_forensics import analyze_image
from backend.analysis.copy_move import detect_copy_move
from backend.analysis.metadata_analysis import analyze_metadata
from backend.analysis.noise_analysis import analyze_noise

from backend.document_analysis.font_consistency import (
    analyze_font_consistency
)

from backend.document_analysis.spacing_analysis import (
    analyze_spacing
)

from backend.document_analysis.region_anomaly import (
    analyze_region_anomaly
)


# ==========================================
# MAIN
# ==========================================

def analyze_document_risk(

    image_path,

    analysis_dir

):

    image_path = Path(image_path)

    analysis_dir = Path(analysis_dir)

    analysis_dir.mkdir(

        parents=True,

        exist_ok=True

    )

    # --------------------------------------
    # Run all analyses
    # --------------------------------------

    forensic = analyze_image(

        str(image_path),

        str(analysis_dir)

    )

    copy_move = detect_copy_move(

        str(image_path),

        analysis_dir

    )

    metadata = analyze_metadata(

        str(image_path)

    )

    noise = analyze_noise(

        str(image_path)

    )

    font = analyze_font_consistency(

        str(image_path)

    )

    spacing = analyze_spacing(

        str(image_path)

    )

    regions = analyze_region_anomaly(

        str(image_path)

    )

    # --------------------------------------
    # Risk
    # --------------------------------------

    score = 0

    findings = []

    # ======================================
    # ELA
    # ======================================

    ela = forensic["signals"]["ela_score"]

    if ela > 0.18:

        score += 10

        findings.append(

            "High ELA score"

        )

    # ======================================
    # Wavelet
    # ======================================

    wavelet = forensic["signals"]["wavelet_score"]

    if wavelet > 0.25:

        score += 10

        findings.append(

            "Wavelet anomaly"

        )

    # ======================================
    # Copy Move
    # ======================================

    if copy_move["copy_move_detected"]:

        score += 30

        findings.append(

            "Copy-Move forgery"

        )

    # ======================================
    # Metadata
    # ======================================

    if metadata["suspicious"]:

        score += 15

        findings.append(

            "Editing software metadata"

        )

    # ======================================
    # Noise
    # ======================================

    if noise["noise_inconsistency"] > 0.20:

        score += 10

        findings.append(

            "Noise inconsistency"

        )

    # ======================================
    # Font
    # ======================================

    font_count = len(

        font["suspicious_words"]

    )

    if font_count:

        score += min(

            25,

            font_count * 3

        )

        findings.append(

            f"{font_count} suspicious words"

        )

    # ======================================
    # Layout
    # ======================================

    if spacing["risk_score"] > 40:

        score += 15

        findings.append(

            "Layout anomaly"

        )

    # ======================================
    # Region
    # ======================================

    region_count = len(

        regions["high_risk_regions"]

    )

    if region_count:

        score += min(

            20,

            region_count * 2

        )

        findings.append(

            f"{region_count} suspicious regions"

        )

    score = min(

        score,

        100

    )

    # ======================================
    # Verdict
    # ======================================

    if score >= 80:

        verdict = "HIGH RISK"

        recommendation = (

            "Strong evidence of manipulation."

        )

    elif score >= 55:

        verdict = "MEDIUM RISK"

        recommendation = (

            "Manual verification recommended."

        )

    elif score >= 30:

        verdict = "LOW RISK"

        recommendation = (

            "Minor anomalies detected."

        )

    else:

        verdict = "AUTHENTIC"

        recommendation = (

            "No significant anomaly detected."

        )

    confidence = round(

        70 + score * 0.3,

        2

    )

    confidence = min(

        confidence,

        99.9

    )

    print()

    print("========== RISK ENGINE ==========")

    print("Risk:", score)

    print("Verdict:", verdict)

    print("Confidence:", confidence)

    print("=================================")

    print()

    return {

        "risk_score": score,

        "confidence": confidence,

        "overall_verdict": verdict,

        "recommendation": recommendation,

        "findings": findings,

        "signals":{

            "ela": ela,

            "wavelet": wavelet,

            "copy_move":

                copy_move["copy_move_detected"],

            "noise":

                noise["noise_inconsistency"],

            "metadata":

                metadata["suspicious"],

            "font":

                font_count,

            "regions":

                region_count

        }

    }