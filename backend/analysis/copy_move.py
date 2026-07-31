from pathlib import Path

import cv2
import numpy as np


def detect_copy_move(
    image_path,
    output_dir=None
):

    # -----------------------------------------
    # Read image
    # -----------------------------------------

    image = cv2.imread(
        str(image_path)
    )

    if image is None:

        raise ValueError(
            "Unable to read image"
        )


    # -----------------------------------------
    # Prepare artifact path
    # -----------------------------------------

    artifact_path = None

    if output_dir:

        output_dir = Path(
            output_dir
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        artifact_path = (

            output_dir /

            f"{Path(image_path).stem}_copy_move.jpg"

        )


    # -----------------------------------------
    # Default result
    # -----------------------------------------

    result = {

        "verdict":
            "No Copy-Move Detected",

        "copy_move_detected":
            False,

        "copy_move_score": 0.0,

        "matched_points":
            0,

        "inliers":
            0,

        "artifact":
            str(artifact_path)
            if artifact_path
            else None

    }


    # -----------------------------------------
    # Convert to grayscale
    # -----------------------------------------

    gray = cv2.cvtColor(

        image,

        cv2.COLOR_BGR2GRAY

    )


    # -----------------------------------------
    # ORB
    # -----------------------------------------

    orb = cv2.ORB_create(

        nfeatures=5000

    )


    keypoints, descriptors = (

        orb.detectAndCompute(

            gray,

            None

        )

    )


    # -----------------------------------------
    # If no features
    # -----------------------------------------

    if descriptors is None:

        if artifact_path:

            cv2.imwrite(

                str(artifact_path),

                image

            )

        return result


    # -----------------------------------------
    # BF Matcher
    # -----------------------------------------

    matcher = cv2.BFMatcher(

        cv2.NORM_HAMMING,

        crossCheck=False

    )


    matches = matcher.knnMatch(

        descriptors,

        descriptors,

        k=2

    )


    # -----------------------------------------
    # Ratio Test
    # -----------------------------------------

    good_matches = []


    for pair in matches:

        if len(pair) < 2:

            continue


        m, n = pair


        if (

            m.distance

            <

            0.75 * n.distance

        ):

            if (

                m.queryIdx

                !=

                m.trainIdx

            ):

                good_matches.append(m)


    # Update matched points

    result["matched_points"] = (

        len(good_matches)

    )


    # -----------------------------------------
    # Not enough matches
    # -----------------------------------------

    if len(good_matches) < 4:

        if artifact_path:

            cv2.imwrite(

                str(artifact_path),

                image

            )

        return result


    # -----------------------------------------
    # Extract points
    # -----------------------------------------

    src_pts = np.float32([

        keypoints[
            m.queryIdx
        ].pt

        for m in good_matches

    ]).reshape(

        -1,

        1,

        2

    )


    dst_pts = np.float32([

        keypoints[
            m.trainIdx
        ].pt

        for m in good_matches

    ]).reshape(

        -1,

        1,

        2

    )


    # -----------------------------------------
    # RANSAC
    # -----------------------------------------

    homography, mask = cv2.findHomography(

        src_pts,

        dst_pts,

        cv2.RANSAC,

        5.0

    )


    # -----------------------------------------
    # Homography failed
    # -----------------------------------------

    if mask is None:

        if artifact_path:

            cv2.imwrite(

                str(artifact_path),

                image

            )

        return result


    # -----------------------------------------
    # Inliers
    # -----------------------------------------

    inliers = int(

        mask.ravel().sum()

    )


    result["inliers"] = inliers


    # -----------------------------------------
    # Score
    # -----------------------------------------

    score = (

        inliers /

        max(

            len(good_matches),

            1

        )

    )


    result["copy_move_score"] = round(
    float(score),
    4
    )


    # -----------------------------------------
    # Detection
    # -----------------------------------------

    copy_move_detected = (

        inliers >= 10

        and

        score >= 0.20

    )


    result["copy_move_detected"] = (

        copy_move_detected

    )


    if copy_move_detected:

        result["verdict"] = (

            "Potential Copy-Move Forgery"

        )


    # -----------------------------------------
    # Create visualization
    # -----------------------------------------

    visualization = image.copy()


    for i, match in enumerate(

        good_matches

    ):

        if mask[i]:

            x, y = map(

                int,

                keypoints[
                    match.queryIdx
                ].pt

            )


            cv2.circle(

                visualization,

                (x, y),

                8,

                (0, 0, 255),

                -1

            )


    # -----------------------------------------
    # Save artifact
    # -----------------------------------------

    if artifact_path:

        cv2.imwrite(

            str(artifact_path),

            visualization

        )


    return result