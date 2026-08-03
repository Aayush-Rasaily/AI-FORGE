from pathlib import Path

import cv2
import numpy as np

from backend.document_analysis.text_layout_analysis import (
    analyze_text_layout
)

from backend.document_analysis.font_consistency import (
    analyze_font_consistency
)

from backend.document_analysis.spacing_analysis import (
    analyze_spacing
)


# ==========================================
# Crop Region
# ==========================================

def crop_region(image, bbox):

    xs = [int(p[0]) for p in bbox]
    ys = [int(p[1]) for p in bbox]

    x1 = max(min(xs), 0)
    x2 = min(max(xs), image.shape[1])

    y1 = max(min(ys), 0)
    y2 = min(max(ys), image.shape[0])

    return image[y1:y2, x1:x2]


# ==========================================
# Region Metrics
# ==========================================

def region_metrics(region):

    gray = cv2.cvtColor(

        region,

        cv2.COLOR_BGR2GRAY

    )

    edges = cv2.Canny(

        gray,

        100,

        200

    )

    edge_density = (

        np.sum(edges > 0)

        /

        (gray.size + 1)

    )

    noise = np.std(gray)

    brightness = np.mean(gray)

    lap = cv2.Laplacian(

        gray,

        cv2.CV_64F

    )

    texture = lap.var()

    return {

        "edge_density":

            round(float(edge_density),4),

        "noise":

            round(float(noise),2),

        "brightness":

            round(float(brightness),2),

        "texture":

            round(float(texture),2)

    }


# ==========================================
# Main
# ==========================================

def analyze_region_anomaly(image_path):

    image_path = Path(image_path)

    image = cv2.imread(

        str(image_path)

    )

    layout = analyze_text_layout(

        image_path

    )

    font = analyze_font_consistency(

        image_path

    )

    spacing = analyze_spacing(

        image_path

    )

    suspicious_words = {

        w["text"]

        for w in font["suspicious_words"]

    }

    suspicious_lines = {

        l["line"]

        for l in spacing["lines"]

        if l["spacing_anomaly"]

    }

    regions = []

    for line in layout["lines"]:

        line_no = line["line_number"]

        for word in line["words"]:

            crop = crop_region(

                image,

                word["bbox"]

            )

            if crop.size == 0:

                continue

            metrics = region_metrics(

                crop

            )

            score = 0

            reasons = []

            if word["text"] in suspicious_words:

                score += 40

                reasons.append(

                    "Font inconsistency"

                )

            if line_no in suspicious_lines:

                score += 25

                reasons.append(

                    "Layout anomaly"

                )

            if metrics["noise"] > 45:

                score += 15

                reasons.append(

                    "Noise variation"

                )

            if metrics["edge_density"] > 0.18:

                score += 10

                reasons.append(

                    "High edge density"

                )

            if metrics["texture"] > 1200:

                score += 10

                reasons.append(

                    "Texture inconsistency"

                )

            score = min(score,100)

            if score >= 40:

                verdict = "Suspicious"

            else:

                verdict = "Normal"

            regions.append({

                "text":

                    word["text"],

                "line":

                    line_no,

                "bbox":

                    word["bbox"],

                "risk_score":

                    score,

                "verdict":

                    verdict,

                "reasons":

                    reasons,

                "metrics":

                    metrics

            })

    high_risk = [

        r

        for r in regions

        if r["risk_score"] >= 40

    ]

    overall = np.mean(

        [

            r["risk_score"]

            for r in regions

        ]

    )

    if overall >= 60:

        verdict = "High Risk"

    elif overall >= 35:

        verdict = "Moderate Risk"

    else:

        verdict = "Low Risk"

    print()

    print("========== REGION ANALYSIS ==========")

    print(

        "Regions:",

        len(regions)

    )

    print(

        "High Risk:",

        len(high_risk)

    )

    print(

        "Overall:",

        round(overall,2)

    )

    print(

        "Verdict:",

        verdict

    )

    print("=====================================")

    print()

    return {

        "overall_score":

            round(float(overall),2),

        "overall_verdict":

            verdict,

        "regions":

            regions,

        "high_risk_regions":

            high_risk

    }