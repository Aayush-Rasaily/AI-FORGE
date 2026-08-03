from pathlib import Path
import cv2
import numpy as np
import easyocr

# ==========================================
# Load OCR Reader (Singleton)
# ==========================================

reader = easyocr.Reader(
    ["en"],
    gpu=False
)


# ==========================================
# Calculate Box Center
# ==========================================

def get_center(box):

    xs = [p[0] for p in box]
    ys = [p[1] for p in box]

    return (

        float(sum(xs) / 4),

        float(sum(ys) / 4)

    )


# ==========================================
# Group OCR words into text lines
# ==========================================

def group_lines(words, y_threshold=20):

    words = sorted(
        words,
        key=lambda w: w["center_y"]
    )

    lines = []

    for word in words:

        added = False

        for line in lines:

            avg_y = np.mean(

                [w["center_y"] for w in line]

            )

            if abs(

                word["center_y"] - avg_y

            ) <= y_threshold:

                line.append(word)

                added = True

                break

        if not added:

            lines.append([word])

    # sort every line left to right

    for line in lines:

        line.sort(

            key=lambda w: w["center_x"]

        )

    return lines


# ==========================================
# Compute Average Word Spacing
# ==========================================

def calculate_word_spacing(lines):

    spacing = []

    for line in lines:

        for i in range(

            len(line) - 1

        ):

            right = line[i]["bbox"][1][0]

            left = line[i + 1]["bbox"][0][0]

            spacing.append(

                left - right

            )

    if len(spacing) == 0:

        return 0

    return round(

        float(np.mean(spacing)),

        2

    )


# ==========================================
# Compute Line Spacing
# ==========================================

def calculate_line_spacing(lines):

    centers = []

    for line in lines:

        ys = [

            w["center_y"]

            for w in line

        ]

        centers.append(

            np.mean(ys)

        )

    centers.sort()

    spacing = []

    for i in range(

        len(centers) - 1

    ):

        spacing.append(

            centers[i + 1] - centers[i]

        )

    if len(spacing) == 0:

        return 0

    return round(

        float(np.mean(spacing)),

        2

    )


# ==========================================
# Detect Alignment
# ==========================================

def detect_alignment(lines):

    left_edges = []

    for line in lines:

        left_edges.append(

            line[0]["bbox"][0][0]

        )

    std = np.std(left_edges)

    if std < 12:

        return "Left"

    return "Mixed"


# ==========================================
# Main Function
# ==========================================

def analyze_text_layout(image_path):

    image_path = Path(image_path)

    if not image_path.exists():

        raise FileNotFoundError(

            image_path

        )

    image = cv2.imread(

        str(image_path)

    )

    if image is None:

        raise ValueError(

            "Cannot read image"

        )

    results = reader.readtext(

        str(image_path)

    )

    words = []

    for idx, item in enumerate(results):

        box, text, confidence = item

        center_x, center_y = get_center(box)

        words.append({

            "id": idx + 1,

            "text": text,

            "confidence": round(

                float(confidence),

                3

            ),

            "bbox": box,

            "center_x": center_x,

            "center_y": center_y

        })

    # ---------------------------------

    lines = group_lines(words)

    # ---------------------------------

    word_spacing = calculate_word_spacing(lines)

    line_spacing = calculate_line_spacing(lines)

    alignment = detect_alignment(lines)

    # ---------------------------------

    line_results = []

    for i, line in enumerate(lines):

        line_results.append({

            "line_number": i + 1,

            "text":

                " ".join(

                    [

                        w["text"]

                        for w in line

                    ]

                ),

            "words": line

        })

    # ---------------------------------

    result = {

        "total_words": len(words),

        "total_lines": len(lines),

        "alignment": alignment,

        "average_word_spacing": word_spacing,

        "average_line_spacing": line_spacing,

        "lines": line_results

    }

    # ---------------------------------

    print("\n========== TEXT LAYOUT ==========")

    print("Words:", len(words))

    print("Lines:", len(lines))

    print("Alignment:", alignment)

    print("Word Spacing:", word_spacing)

    print("Line Spacing:", line_spacing)

    print("=================================\n")

    return result