from pathlib import Path

import cv2
import numpy as np

from backend.document_analysis.region_anomaly import (
    analyze_region_anomaly
)


# ==========================================
# Convert Bounding Box
# ==========================================

def bbox_to_rect(bbox):

    xs = [int(p[0]) for p in bbox]
    ys = [int(p[1]) for p in bbox]

    return (

        min(xs),

        min(ys),

        max(xs),

        max(ys)

    )


# ==========================================
# Risk Color
# ==========================================

def get_color(score):

    if score >= 80:

        return (0,0,255)

    elif score >= 60:

        return (0,165,255)

    elif score >= 40:

        return (0,255,255)

    return (0,255,0)


# ==========================================
# Draw Heatmap
# ==========================================

def generate_heatmap(

    image_path,

    output_dir

):

    image_path = Path(image_path)

    output_dir = Path(output_dir)

    output_dir.mkdir(

        parents=True,

        exist_ok=True

    )

    image = cv2.imread(

        str(image_path)

    )

    if image is None:

        raise ValueError(

            "Unable to read image"

        )

    overlay = image.copy()

    result = analyze_region_anomaly(

        image_path

    )

    regions = result["regions"]

    for region in regions:

        x1,y1,x2,y2 = bbox_to_rect(

            region["bbox"]

        )

        score = region["risk_score"]

        color = get_color(score)

        alpha = min(

            score / 100,

            0.8

        )

        cv2.rectangle(

            overlay,

            (x1,y1),

            (x2,y2),

            color,

            -1

        )

        cv2.rectangle(

            image,

            (x1,y1),

            (x2,y2),

            color,

            2

        )

        cv2.putText(

            image,

            f"{score}%",

            (x1,max(15,y1-5)),

            cv2.FONT_HERSHEY_SIMPLEX,

            0.45,

            color,

            1,

            cv2.LINE_AA

        )

    heatmap = cv2.addWeighted(

        overlay,

        0.35,

        image,

        0.65,

        0

    )

    legend = np.full(

        (70,350,3),

        255,

        dtype=np.uint8

    )

    cv2.putText(

        legend,

        "Risk Legend",

        (10,20),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.6,

        (0,0,0),

        2

    )

    cv2.rectangle(

        legend,

        (10,35),

        (30,55),

        (0,255,0),

        -1

    )

    cv2.putText(

        legend,

        "Low",

        (40,50),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.5,

        (0,0,0),

        1

    )

    cv2.rectangle(

        legend,

        (120,35),

        (140,55),

        (0,255,255),

        -1

    )

    cv2.putText(

        legend,

        "Medium",

        (150,50),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.5,

        (0,0,0),

        1

    )

    cv2.rectangle(

        legend,

        (250,35),

        (270,55),

        (0,0,255),

        -1

    )

    cv2.putText(

        legend,

        "High",

        (280,50),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.5,

        (0,0,0),

        1

    )

    heatmap_path = (

        output_dir /

        f"{image_path.stem}_heatmap.jpg"

    )

    legend_path = (

        output_dir /

        f"{image_path.stem}_legend.jpg"

    )

    cv2.imwrite(

        str(heatmap_path),

        heatmap

    )

    cv2.imwrite(

        str(legend_path),

        legend

    )

    print()

    print("========== HEATMAP ==========")

    print(

        "Regions:",

        len(regions)

    )

    print(

        "Saved:",

        heatmap_path

    )

    print("=============================")

    print()

    return {

        "heatmap": str(heatmap_path),

        "legend": str(legend_path),

        "regions": len(regions),

        "overall_score":

            result["overall_score"],

        "overall_verdict":

            result["overall_verdict"]

    }