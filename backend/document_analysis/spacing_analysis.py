from pathlib import Path

import cv2
import numpy as np

from backend.document_analysis.text_layout_analysis import (
    analyze_text_layout
)


# ==========================================
# Distance
# ==========================================

def distance(a, b):

    return abs(a - b)


# ==========================================
# Analyze Layout Spacing
# ==========================================

def analyze_spacing(image_path, layout_data=None, analysis_dir=None):
    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(image_path)

    layout = layout_data or analyze_text_layout(str(image_path), analysis_dir=analysis_dir)

    lines = layout["lines"]

    suspicious_lines = []

    word_spacings = []

    line_starts = []

    line_centers = []

    # ======================================
    # Analyze every line
    # ======================================

    for line in lines:

        words = line["words"]

        if len(words) == 0:

            continue

        line_starts.append(

            words[0]["bbox"][0][0]

        )

        xs = []

        spacings = []

        previous_right = None

        for word in words:

            left = word["bbox"][0][0]

            right = word["bbox"][1][0]

            xs.append(

                word["center_x"]

            )

            if previous_right is not None:

                gap = left - previous_right

                spacings.append(gap)

                word_spacings.append(gap)

            previous_right = right

        line_centers.append(

            np.mean(xs)

        )

        if len(spacings):

            std = np.std(spacings)

            mean = np.mean(spacings)

        else:

            std = 0

            mean = 0

        suspicious_lines.append({

            "line": line["line_number"],

            "text": line["text"],

            "mean_spacing": round(float(mean),2),

            "spacing_variation": round(float(std),2),

            "spacing_anomaly": std > 20

        })

    # ======================================
    # Overall statistics
    # ======================================

    overall_word_spacing = (

        np.mean(word_spacings)

        if word_spacings

        else 0

    )

    spacing_std = (

        np.std(word_spacings)

        if word_spacings

        else 0

    )

    alignment_std = (

        np.std(line_starts)

        if line_starts

        else 0

    )

    center_std = (

        np.std(line_centers)

        if line_centers

        else 0

    )

    # ======================================
    # Verdict
    # ======================================

    findings = []

    risk = 0

    if spacing_std > 18:

        findings.append(

            "Abnormal word spacing detected"

        )

        risk += 25

    if alignment_std > 25:

        findings.append(

            "Text alignment inconsistency"

        )

        risk += 20

    if center_std > 30:

        findings.append(

            "Possible shifted text rows"

        )

        risk += 20

    anomaly_count = sum(

        l["spacing_anomaly"]

        for l in suspicious_lines

    )

    if anomaly_count > 3:

        findings.append(

            "Multiple suspicious text lines"

        )

        risk += 25

    if risk > 100:

        risk = 100

    if risk >= 70:

        verdict = "High Layout Anomaly"

    elif risk >= 40:

        verdict = "Moderate Layout Anomaly"

    else:

        verdict = "Layout Appears Consistent"

    print()

    print("========== SPACING ANALYSIS ==========")

    print("Lines:", len(lines))

    print(

        "Average Word Spacing:",

        round(float(overall_word_spacing),2)

    )

    print(

        "Spacing Std:",

        round(float(spacing_std),2)

    )

    print(

        "Alignment Std:",

        round(float(alignment_std),2)

    )

    print(

        "Center Std:",

        round(float(center_std),2)

    )

    print("Risk:", risk)

    print("Verdict:", verdict)

    print("======================================")

    print()

    return {

        "verdict": verdict,

        "risk_score": risk,

        "average_word_spacing":

            round(float(overall_word_spacing),2),

        "spacing_variation":

            round(float(spacing_std),2),

        "alignment_variation":

            round(float(alignment_std),2),

        "line_center_variation":

            round(float(center_std),2),

        "findings": findings,

        "lines": suspicious_lines

    }