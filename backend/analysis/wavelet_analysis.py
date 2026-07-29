import cv2
import numpy as np

import pywt


def analyze_wavelet(
    image_path: str,
    output_path: str
):

    image = cv2.imread(
        image_path,
        cv2.IMREAD_GRAYSCALE
    )


    if image is None:

        raise ValueError(
            "Unable to read image"
        )


    image = image.astype(
        np.float32
    )


    # Haar wavelet
    coeffs = pywt.dwt2(
        image,
        "haar"
    )


    approximation, (
        horizontal,
        vertical,
        diagonal
    ) = coeffs


    # High frequency components
    high_frequency = (

        np.abs(horizontal)

        +

        np.abs(vertical)

        +

        np.abs(diagonal)

    )


    high_frequency_energy = np.mean(
        high_frequency
    )


    # Normalize
    score = min(
        high_frequency_energy / 255.0,
        1.0
    )


    # Create visualization
    wavelet_map = np.abs(
        high_frequency
    )


    # Normalize for display
    wavelet_map = cv2.normalize(
        wavelet_map,
        None,
        0,
        255,
        cv2.NORM_MINMAX
    )


    wavelet_map = wavelet_map.astype(
        np.uint8
    )


    # Resize to original size
    wavelet_map = cv2.resize(
        wavelet_map,
        (
            image.shape[1],
            image.shape[0]
        )
    )


    # Save
    cv2.imwrite(
        output_path,
        wavelet_map
    )


    return {

        "high_frequency_energy":
            float(
                high_frequency_energy
            ),

        "wavelet_score":
            float(
                score
            )

    }