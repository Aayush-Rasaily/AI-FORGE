from pathlib import Path

from PIL import Image


def analyze_jpeg_compression(image_path):

    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(
            f"Image not found: {image_path}"
        )

    result = {

        "is_jpeg": False,

        "quality_estimate": None,

        "suspicious": False,

        "recompression_difference": 0.0,

        "reason": None

    }

    try:

        image = Image.open(image_path)

        # ---------------------------------
        # Check JPEG
        # ---------------------------------

        if image.format != "JPEG":

            result["reason"] = (
                "Image is not JPEG format"
            )

            return result

        result["is_jpeg"] = True

        # ---------------------------------
        # Read original pixels
        # ---------------------------------

        original = image.convert(
            "RGB"
        )

        # ---------------------------------
        # Re-save at high quality
        # ---------------------------------

        temp_path = (

            image_path.parent /

            f"{image_path.stem}_recompressed.jpg"

        )

        original.save(

            temp_path,

            format="JPEG",

            quality=95,

            optimize=False

        )

        recompressed = Image.open(
            temp_path
        ).convert("RGB")

        # ---------------------------------
        # Compare pixel differences
        # ---------------------------------

        import numpy as np

        original_array = np.asarray(
            original,
            dtype=np.float32
        )

        recompressed_array = np.asarray(
            recompressed,
            dtype=np.float32
        )

        difference = np.abs(

            original_array -

            recompressed_array

        )

        mean_difference = float(

            np.mean(

                difference

            )

        )

        result[
            "recompression_difference"
        ] = round(

            mean_difference,

            4

        )

        # ---------------------------------
        # Suspicion
        # ---------------------------------

        # This is intentionally conservative.
        # Recompression difference alone
        # should NOT prove forgery.

        if mean_difference > 8.0:

            result["suspicious"] = True

            result["reason"] = (

                "High JPEG recompression "
                "difference detected"

            )

        elif mean_difference > 4.0:

            result["reason"] = (

                "Moderate JPEG recompression "
                "difference detected"

            )

        else:

            result["reason"] = (

                "Normal JPEG compression "
                "behavior"

            )

        # ---------------------------------
        # Remove temporary file
        # ---------------------------------

        if temp_path.exists():

            temp_path.unlink()

    except Exception as e:

        result["error"] = str(e)

    return result