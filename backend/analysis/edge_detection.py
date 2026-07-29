import cv2
import numpy as np


def analyze_edges(
    image_path: str,
    output_path: str
):

    image = cv2.imread(
        image_path
    )


    if image is None:

        raise ValueError(
            "Unable to read image"
        )


    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )


    # Otsu threshold
    threshold_value, _ = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY +
        cv2.THRESH_OTSU
    )


    # Canny edge detection
    edges = cv2.Canny(
        gray,
        threshold_value * 0.5,
        threshold_value
    )


    # Save visualization
    cv2.imwrite(
        output_path,
        edges
    )


    # Calculate edge density
    edge_pixels = np.count_nonzero(
        edges
    )


    total_pixels = edges.size


    edge_density = (
        edge_pixels /
        total_pixels
    )


    return {

        "edge_density":
            float(
                edge_density
            ),

        "edge_pixels":
            int(
                edge_pixels
            ),

        "total_pixels":
            int(
                total_pixels
            )

    }