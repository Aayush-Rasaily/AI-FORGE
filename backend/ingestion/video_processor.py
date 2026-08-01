from pathlib import Path

import cv2


def get_video_metadata(
    video_path: str
):

    video_path = Path(
        video_path
    )

    if not video_path.exists():

        raise FileNotFoundError(
            f"Video not found: {video_path}"
        )


    capture = cv2.VideoCapture(
        str(video_path)
    )


    if not capture.isOpened():

        raise ValueError(
            f"Unable to open video: {video_path}"
        )


    # ------------------------------------------
    # Read metadata
    # ------------------------------------------

    fps = capture.get(
        cv2.CAP_PROP_FPS
    )

    frame_count = int(
        capture.get(
            cv2.CAP_PROP_FRAME_COUNT
        )
    )

    width = int(
        capture.get(
            cv2.CAP_PROP_FRAME_WIDTH
        )
    )

    height = int(
        capture.get(
            cv2.CAP_PROP_FRAME_HEIGHT
        )
    )


    # ------------------------------------------
    # Calculate duration
    # ------------------------------------------

    if fps > 0:

        duration = (
            frame_count /
            fps
        )

    else:

        duration = 0.0


    capture.release()


    return {

        "filename":
            video_path.name,

        "fps":
            round(
                float(fps),
                2
            ),

        "frame_count":
            frame_count,

        "width":
            width,

        "height":
            height,

        "duration":
            round(
                duration,
                2
            )

    }


def extract_keyframes(

    video_path: str,

    output_dir: str,

    max_frames: int = 12

):

    video_path = Path(
        video_path
    )

    output_dir = Path(
        output_dir
    )


    if not video_path.exists():

        raise FileNotFoundError(
            f"Video not found: {video_path}"
        )


    output_dir.mkdir(

        parents=True,

        exist_ok=True

    )


    capture = cv2.VideoCapture(

        str(video_path)

    )


    if not capture.isOpened():

        raise ValueError(

            f"Unable to open video: {video_path}"

        )


    total_frames = int(

        capture.get(

            cv2.CAP_PROP_FRAME_COUNT

        )

    )


    if total_frames <= 0:

        capture.release()

        raise ValueError(

            "Video contains no readable frames."

        )


    # ------------------------------------------
    # Determine frame positions
    # ------------------------------------------

    frame_count = min(

        max_frames,

        total_frames

    )


    if frame_count == 1:

        frame_positions = [

            0

        ]

    else:

        frame_positions = [

            int(

                i *

                (total_frames - 1) /

                (frame_count - 1)

            )

            for i in range(

                frame_count

            )

        ]


    extracted_frames = []


    # ------------------------------------------
    # Extract frames
    # ------------------------------------------

    for index, frame_position in enumerate(

        frame_positions

    ):

        capture.set(

            cv2.CAP_PROP_POS_FRAMES,

            frame_position

        )


        success, frame = capture.read()


        if not success:

            continue


        frame_filename = (

            f"frame_{index + 1:04d}.jpg"

        )


        frame_path = (

            output_dir /

            frame_filename

        )


        cv2.imwrite(

            str(frame_path),

            frame

        )


        timestamp = (

            frame_position /

            capture.get(

                cv2.CAP_PROP_FPS

            )

            if capture.get(

                cv2.CAP_PROP_FPS

            ) > 0

            else 0

        )


        extracted_frames.append({

            "frame_number":

                frame_position,

            "frame_index":

                index + 1,

            "timestamp":

                round(

                    float(timestamp),

                    2

                ),

            "path":

                str(frame_path)

        })


    capture.release()


    return extracted_frames