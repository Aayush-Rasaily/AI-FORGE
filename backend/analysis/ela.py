from pathlib import Path

import numpy as np

from PIL import (
    Image,
    ImageChops,
    ImageEnhance
)


def generate_ela(
    image_path: str,
    output_path: str,
    quality: int = 90,
    scale: int = 10
):
    """
    Generate an ELA visualization
    and save it to disk.
    """

    image_path = Path(
        image_path
    )

    output_path = Path(
        output_path
    )


    original = Image.open(
        image_path
    ).convert("RGB")


    temp_path = image_path.with_suffix(
        ".ela_temp.jpg"
    )


    try:

        # Recompress image
        original.save(
            temp_path,
            "JPEG",
            quality=quality
        )


        recompressed = Image.open(
            temp_path
        ).convert("RGB")


        # Calculate difference
        difference = ImageChops.difference(
            original,
            recompressed
        )


        # Amplify difference
        enhanced = ImageEnhance.Brightness(
            difference
        ).enhance(scale)


        # Save ELA image
        enhanced.save(
            output_path
        )


        return enhanced


    finally:

        if temp_path.exists():

            temp_path.unlink()


def calculate_ela_score(
    ela_image
) -> float:

    """
    Calculate normalized ELA anomaly score.
    """

    ela_array = np.asarray(
        ela_image
    ).astype(
        np.float32
    )


    mean_difference = np.mean(
        ela_array
    )


    score = min(
        mean_difference / 255.0,
        1.0
    )


    return float(
        score
    )