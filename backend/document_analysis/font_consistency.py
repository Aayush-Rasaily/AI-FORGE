from pathlib import Path

import cv2
import numpy as np

from backend.document_analysis.text_layout_analysis import (
    analyze_text_layout
)


# ==========================================
# Crop Word
# ==========================================

def crop_word(image, bbox):

    xs = [int(p[0]) for p in bbox]
    ys = [int(p[1]) for p in bbox]

    x1 = max(min(xs), 0)
    x2 = min(max(xs), image.shape[1])

    y1 = max(min(ys), 0)
    y2 = min(max(ys), image.shape[0])

    return image[y1:y2, x1:x2]


# ==========================================
# Extract Font Features
# ==========================================

def extract_font_features(word_img):

    gray = cv2.cvtColor(

        word_img,

        cv2.COLOR_BGR2GRAY

    )

    _, thresh = cv2.threshold(

        gray,

        0,

        255,

        cv2.THRESH_BINARY_INV +

        cv2.THRESH_OTSU

    )

    h, w = thresh.shape

    black_ratio = np.sum(

        thresh > 0

    ) / (h * w + 1)

    edges = cv2.Canny(

        gray,

        100,

        200

    )

    edge_density = np.sum(

        edges > 0

    ) / (h * w + 1)

    return {

        "height": h,

        "width": w,

        "aspect_ratio": round(

            w / max(h, 1),

            3

        ),

        "black_ratio": round(

            float(black_ratio),

            4

        ),

        "edge_density": round(

            float(edge_density),

            4

        ),

        "mean_intensity": round(

            float(np.mean(gray)),

            2

        ),

        "std_intensity": round(

            float(np.std(gray)),

            2

        )

    }


# ==========================================
# Main Analysis
# ==========================================

def analyze_font_consistency(image_path):

    image = cv2.imread(str(image_path))

    layout = analyze_text_layout(image_path)

    words = []

    for line in layout["lines"]:

        for word in line["words"]:

            crop = crop_word(

                image,

                word["bbox"]

            )

            if crop.size == 0:

                continue

            features = extract_font_features(

                crop

            )

            words.append({

                "text": word["text"],

                "bbox": word["bbox"],

                "features": features

            })

    if len(words) == 0:

        return {

            "suspicious_words": [],

            "average": {}

        }

    avg_black = np.mean([

        w["features"]["black_ratio"]

        for w in words

    ])

    avg_edge = np.mean([

        w["features"]["edge_density"]

        for w in words

    ])

    suspicious = []

    for word in words:

        score = 0

        if abs(

            word["features"]["black_ratio"]

            - avg_black

        ) > 0.08:

            score += 1

        if abs(

            word["features"]["edge_density"]

            - avg_edge

        ) > 0.08:

            score += 1

        if score >= 2:

            suspicious.append({

                "text": word["text"],

                "bbox": word["bbox"],

                "score": score,

                "features": word["features"]

            })

    print()

    print("========== FONT ANALYSIS ==========")

    print("Words:", len(words))

    print(

        "Suspicious:",

        len(suspicious)

    )

    print("===================================")

    print()

    return {

        "average": {

            "black_ratio":

                round(

                    float(avg_black),

                    4

                ),

            "edge_density":

                round(

                    float(avg_edge),

                    4

                )

        },

        "total_words": len(words),

        "suspicious_words": suspicious

    }