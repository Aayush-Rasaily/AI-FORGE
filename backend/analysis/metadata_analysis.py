from pathlib import Path

from PIL import Image


def analyze_metadata(image_path):

    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(
            f"Image not found: {image_path}"
        )

    result = {
        "metadata_found": False,
        "metadata_missing": True,
        "suspicious": False,
        "software_detected": False,
        "software": None,
        "camera_make": None,
        "camera_model": None,
        "creation_time": None,
        "modification_time": None,
        "metadata_count": 0,
        "suspicious_reasons": []
    }

    try:

        image = Image.open(image_path)

        exif_data = image.getexif()

        if not exif_data:

            result["suspicious_reasons"].append(
                "No EXIF metadata found"
            )

            return result

        metadata = {}

        for tag_id, value in exif_data.items():

            metadata[tag_id] = value

        result["metadata_count"] = len(metadata)

        result["metadata_found"] = (
            len(metadata) > 0
        )

        result["metadata_missing"] = False

        # Image Description
        if 270 in metadata:

            result["description"] = str(
                metadata[270]
            )

        # Camera Make
        if 271 in metadata:

            result["camera_make"] = str(
                metadata[271]
            )

        # Camera Model
        if 272 in metadata:

            result["camera_model"] = str(
                metadata[272]
            )

        # DateTime
        if 306 in metadata:

            result["creation_time"] = str(
                metadata[306]
            )

        # Software
        if 305 in metadata:

            software = str(
                metadata[305]
            )

            result["software"] = software

            result["software_detected"] = True

            software_lower = (
                software.lower()
            )

            suspicious_software = [

                "photoshop",
                "adobe",
                "gimp",
                "paint.net",
                "pixlr",
                "canva",
                "affinity",
                "lightroom"

            ]

            for software_name in suspicious_software:

                if software_name in software_lower:

                    result["suspicious"] = True

                    result[
                        "suspicious_reasons"
                    ].append(

                        f"Editing software detected: "
                        f"{software}"

                    )

                    break

    except Exception as e:

        result["error"] = str(e)

    return result