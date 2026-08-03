from pathlib import Path

import cv2
import numpy as np


def analyze_noise(image_path):

    image_path = Path(image_path)

    if not image_path.exists():

        raise FileNotFoundError(
            f"Image not found: {image_path}"
        )

    image = cv2.imread(

        str(image_path),

        cv2.IMREAD_GRAYSCALE

    )

    if image is None:

        raise ValueError(
            "Unable to read image"
        )

    # ---------------------------------
    # Blur image
    # ---------------------------------

    denoised = cv2.GaussianBlur(

        image,

        (5, 5),

        0

    )

    # ---------------------------------
    # Estimate residual noise
    # ---------------------------------

    noise = (

        image.astype(np.float32)

        -

        denoised.astype(np.float32)

    )

    noise_std = float(

        np.std(noise)

    )

    # ---------------------------------
    # Divide image into regions
    # ---------------------------------

    height, width = image.shape

    grid_size = 4

    local_scores = []

    for row in range(grid_size):

        for col in range(grid_size):

            y1 = int(
                row * height / grid_size
            )

            y2 = int(
                (row + 1) * height / grid_size
            )

            x1 = int(
                col * width / grid_size
            )

            x2 = int(
                (col + 1) * width / grid_size
            )

            region = noise[
                y1:y2,
                x1:x2
            ]

            local_std = float(

                np.std(region)

            )

            local_scores.append(

                local_std

            )

    # ---------------------------------
    # Calculate inconsistency
    # ---------------------------------

    if local_scores:

        mean_noise = float(

            np.mean(local_scores)

        )

        std_noise = float(

            np.std(local_scores)

        )

        if mean_noise > 0:

            inconsistency = (

                std_noise /

                mean_noise

            )

        else:

            inconsistency = 0.0

    else:

        inconsistency = 0.0

    # ---------------------------------
    # Normalize
    # ---------------------------------

    normalized_inconsistency = min(

        inconsistency / 1.5,

        1.0

    )

    # ---------------------------------
    # Suspicion
    # ---------------------------------

    suspicious = (

        normalized_inconsistency >= 0.65

    )

    return {

        "noise_score": round(

            noise_std,

            4

        ),

        "noise_inconsistency": round(

            float(inconsistency),

            4

        ),

        "normalized_noise_inconsistency":
            round(

                float(
                    normalized_inconsistency
                ),

                4

            ),

        "suspicious":

            suspicious,

        "regions_analyzed":

            len(local_scores)

    }