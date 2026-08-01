from pathlib import Path

import cv2
import numpy as np

from backend.ingestion.video_processor import (

    get_video_metadata,

    extract_keyframes

)


def calculate_frame_signals(

    frame_path: str

):

    image = cv2.imread(

        str(frame_path)

    )


    if image is None:

        return {

            "edge_density":

                0.0,

            "brightness":

                0.0,

            "blur_score":

                0.0

        }


    # ------------------------------------------
    # Convert to grayscale
    # ------------------------------------------

    gray = cv2.cvtColor(

        image,

        cv2.COLOR_BGR2GRAY

    )


    # ------------------------------------------
    # Edge Detection
    # ------------------------------------------

    edges = cv2.Canny(

        gray,

        100,

        200

    )


    edge_pixels = np.count_nonzero(

        edges

    )


    total_pixels = (

        edges.shape[0] *

        edges.shape[1]

    )


    edge_density = (

        edge_pixels /

        total_pixels

        if total_pixels > 0

        else 0.0

    )


    # ------------------------------------------
    # Brightness
    # ------------------------------------------

    brightness = float(

        np.mean(

            gray

        )

    )


    # ------------------------------------------
    # Blur Detection
    #
    # Variance of Laplacian
    # ------------------------------------------

    blur_score = float(

        cv2.Laplacian(

            gray,

            cv2.CV_64F

        ).var()

    )


    return {

        "edge_density":

            round(

                edge_density,

                4

            ),

        "brightness":

            round(

                brightness,

                2

            ),

        "blur_score":

            round(

                blur_score,

                2

            )

    }


def analyze_video(

    video_path: str,

    analysis_dir: str,

    max_frames: int = 12

):

    video_path = Path(

        video_path

    )

    analysis_dir = Path(

        analysis_dir

    )


    if not video_path.exists():

        raise FileNotFoundError(

            f"Video not found: {video_path}"

        )


    analysis_dir.mkdir(

        parents=True,

        exist_ok=True

    )


    print(

        f"\n[VIDEO] Starting analysis: "

        f"{video_path.name}"

    )


    # ------------------------------------------
    # Metadata
    # ------------------------------------------

    print(

        "[VIDEO] Extracting metadata..."

    )


    metadata = get_video_metadata(

        str(video_path)

    )


    print(

        "[VIDEO] Metadata extraction completed."

    )


    # ------------------------------------------
    # Extract keyframes
    # ------------------------------------------

    frames_dir = (

        analysis_dir /

        "keyframes"

    )


    print(

        "[VIDEO] Extracting keyframes..."

    )


    keyframes = extract_keyframes(

        str(video_path),

        str(frames_dir),

        max_frames

    )


    print(

        f"[VIDEO] Extracted "

        f"{len(keyframes)} keyframes."

    )


    # ------------------------------------------
    # Analyze frames
    # ------------------------------------------

    frame_results = []


    for frame in keyframes:

        print(

            f"[VIDEO] Analyzing frame "

            f"{frame['frame_index']}..."

        )


        signals = calculate_frame_signals(

            frame["path"]

        )


        frame_results.append({

            "frame_number":

                frame["frame_number"],

            "frame_index":

                frame["frame_index"],

            "timestamp":

                frame["timestamp"],

            "image":

                frame["path"],

            "signals":

                signals

        })


    # ------------------------------------------
    # Calculate summary
    # ------------------------------------------

    if frame_results:

        edge_values = [

            item["signals"]["edge_density"]

            for item in frame_results

        ]


        brightness_values = [

            item["signals"]["brightness"]

            for item in frame_results

        ]


        blur_values = [

            item["signals"]["blur_score"]

            for item in frame_results

        ]


        average_edge_density = (

            sum(edge_values) /

            len(edge_values)

        )


        average_brightness = (

            sum(brightness_values) /

            len(brightness_values)

        )


        average_blur_score = (

            sum(blur_values) /

            len(blur_values)

        )

    else:

        average_edge_density = 0.0

        average_brightness = 0.0

        average_blur_score = 0.0


    # ------------------------------------------
    # Final result
    # ------------------------------------------

    result = {

        "video":

            metadata,

        "summary": {

            "frames_analyzed":

                len(frame_results),

            "average_edge_density":

                round(

                    average_edge_density,

                    4

                ),

            "average_brightness":

                round(

                    average_brightness,

                    2

                ),

            "average_blur_score":

                round(

                    average_blur_score,

                    2

                )

        },

        "frames":

            frame_results

    }


    print(

        "[VIDEO] Analysis completed successfully."

    )


    return result