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


def extract_scene_keyframes(
    video_path: str,
    output_dir: str,
    max_frames: int = 12,
    scene_threshold: float = 0.35,
) -> list:
    """
    Scene-change based keyframe extraction using histogram difference.
    Falls back to uniform sampling if few scenes detected.
    """
    video_path = Path(video_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"Unable to open video: {video_path}")

    fps = capture.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))

    scene_positions = [0]
    prev_hist = None
    frame_idx = 0
    sample_stride = max(1, total_frames // 200)  # scan up to 200 samples

    while True:
        ret, frame = capture.read()
        if not ret:
            break
        if frame_idx % sample_stride == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            hist = cv2.calcHist([gray], [0], None, [64], [0, 256])
            cv2.normalize(hist, hist)
            if prev_hist is not None:
                diff = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA)
                if diff > scene_threshold:
                    scene_positions.append(frame_idx)
            prev_hist = hist
        frame_idx += 1

    capture.release()

    if len(scene_positions) < 2:
        return extract_keyframes(str(video_path), str(output_dir), max_frames)

    # Sample max_frames from scene positions
    if len(scene_positions) > max_frames:
        step = len(scene_positions) / max_frames
        scene_positions = [scene_positions[int(i * step)] for i in range(max_frames)]

    capture = cv2.VideoCapture(str(video_path))
    extracted = []
    for index, pos in enumerate(scene_positions):
        capture.set(cv2.CAP_PROP_POS_FRAMES, pos)
        success, frame = capture.read()
        if not success:
            continue
        frame_path = output_dir / f"frame_{index + 1:04d}.jpg"
        cv2.imwrite(str(frame_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        extracted.append({
            "frame_number": pos,
            "frame_index": index + 1,
            "timestamp": round(pos / fps, 2) if fps > 0 else 0,
            "path": str(frame_path),
            "scene_detected": True,
        })
    capture.release()
    return extracted