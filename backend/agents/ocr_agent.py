import easyocr
from typing import Dict, List

reader = easyocr.Reader(
    ["en"],
    gpu=False
)


def extract_text(image_path: str) -> Dict:

    results = reader.readtext(image_path)

    detections: List[Dict] = []

    full_text = []

    for bbox, text, confidence in results:

        x_coords = [point[0] for point in bbox]
        y_coords = [point[1] for point in bbox]

        detections.append({

            "text": text,

            "confidence": float(confidence),

            "bbox": bbox,

            "left": min(x_coords),

            "right": max(x_coords),

            "top": min(y_coords),

            "bottom": max(y_coords),

            "width": max(x_coords) - min(x_coords),

            "height": max(y_coords) - min(y_coords),

            "center_x": sum(x_coords) / 4,

            "center_y": sum(y_coords) / 4

        })

        full_text.append(text)

    return {

        "full_text": " ".join(full_text),

        "detections": detections

    }