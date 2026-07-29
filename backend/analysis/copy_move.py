import cv2
import numpy as np


def detect_copy_move(
    image_path: str
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


    # ORB feature detector
    orb = cv2.ORB_create(
        nfeatures=2000
    )


    keypoints, descriptors = orb.detectAndCompute(
        gray,
        None
    )


    # Not enough features
    if descriptors is None or len(keypoints) < 10:

        return {
            "copy_move_detected": False,
            "match_count": 0,
            "copy_move_score": 0.0
        }


    # Brute-force matcher
    matcher = cv2.BFMatcher(
        cv2.NORM_HAMMING,
        crossCheck=False
    )


    matches = matcher.knnMatch(
        descriptors,
        descriptors,
        k=2
    )


    good_matches = []


    for pair in matches:

        if len(pair) < 2:
            continue

        m, n = pair

        # Lowe's ratio test
        if m.distance < 0.7 * n.distance:

            # Ignore self-match
            if m.queryIdx != m.trainIdx:

                good_matches.append(m)


    match_count = len(
        good_matches
    )


    # Normalize score
    copy_move_score = min(
        match_count / 100.0,
        1.0
    )


    return {
        "copy_move_detected":
            match_count >= 10,

        "match_count":
            match_count,

        "copy_move_score":
            round(
                copy_move_score,
                4
            )
    }