from pathlib import Path

import cv2
import numpy as np


def detect_copy_move(
    image_path,
    output_dir=None
):
    """
    Detect possible copy-move forgery using ORB
    feature matching with spatial separation.

    The detector looks for similar local features
    appearing at different spatial locations in
    the same image.

    Returns:
        dict containing:
        - verdict
        - copy_move_detected
        - copy_move_score
        - matched_points
        - inliers
        - spatial_matches
        - artifact
    """

    # ==========================================
    # READ IMAGE
    # ==========================================

    image = cv2.imread(
        str(image_path)
    )

    if image is None:

        raise ValueError(
            f"Unable to read image: {image_path}"
        )


    # ==========================================
    # PREPARE ARTIFACT PATH
    # ==========================================

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


    # ==========================================
    # DEFAULT RESULT
    # ==========================================

    result = {

        "verdict":
            "No Copy-Move Detected",

        "copy_move_detected":
            False,

        "copy_move_score":
            0.0,

        "matched_points":
            0,

        "inliers":
            0,

        "spatial_matches":
            0,

        "artifact":
            str(artifact_path)
            if artifact_path
            else None

    }


    # ==========================================
    # CONVERT TO GRAYSCALE
    # ==========================================

    gray = cv2.cvtColor(

        image,

        cv2.COLOR_BGR2GRAY

    )


    # ==========================================
    # ORB FEATURE DETECTION
    # ==========================================

    orb = cv2.ORB_create(

        nfeatures=10000,

        scaleFactor=1.2,

        nlevels=8,

        edgeThreshold=31,

        patchSize=31,

        fastThreshold=10

    )


    keypoints, descriptors = (

        orb.detectAndCompute(

            gray,

            None

        )

    )


    # ==========================================
    # CHECK FEATURES
    # ==========================================

    if (

        descriptors is None

        or

        len(keypoints) < 10

    ):

        if artifact_path:

            cv2.imwrite(

                str(artifact_path),

                image

            )

        return result


    # ==========================================
    # BF MATCHER
    # ==========================================

    matcher = cv2.BFMatcher(

        cv2.NORM_HAMMING,

        crossCheck=False

    )


    # ==========================================
    # SELF MATCHING
    #
    # We still compare descriptors within the
    # same image, but we explicitly remove:
    #
    # 1. Self matches
    # 2. Spatially-near matches
    #
    # This is important for copy-move detection.
    # ==========================================

    matches = matcher.knnMatch(

        descriptors,

        descriptors,

        k=3

    )


    # ==========================================
    # CONFIGURATION
    # ==========================================

    RATIO_THRESHOLD = 0.70

    MIN_SPATIAL_DISTANCE = 50

    good_matches = []


    # ==========================================
    # RATIO TEST + SPATIAL SEPARATION
    # ==========================================

    for pair in matches:

        if len(pair) < 3:

            continue


        m = pair[0]

        n = pair[1]

        p = pair[2]


        # --------------------------------------
        # REMOVE SELF MATCH
        # --------------------------------------

        if (

            m.queryIdx

            ==

            m.trainIdx

        ):

            # Find the first non-self candidate

            candidates = [

                match

                for match in pair

                if match.queryIdx
                !=
                match.trainIdx

            ]

            if len(candidates) < 2:

                continue

            m = candidates[0]

            n = candidates[1]


        # --------------------------------------
        # RATIO TEST
        # --------------------------------------

        if (

            m.distance

            >=

            RATIO_THRESHOLD * n.distance

        ):

            continue


        # --------------------------------------
        # GET KEYPOINT LOCATIONS
        # --------------------------------------

        point1 = np.array(

            keypoints[
                m.queryIdx
            ].pt

        )


        point2 = np.array(

            keypoints[
                m.trainIdx
            ].pt

        )


        # --------------------------------------
        # SPATIAL DISTANCE
        # --------------------------------------

        spatial_distance = np.linalg.norm(

            point1

            -

            point2

        )


        # --------------------------------------
        # REMOVE LOCAL / NEARBY MATCHES
        #
        # A genuine copy-move region should
        # generally appear at a different
        # spatial location.
        # --------------------------------------

        if (

            spatial_distance

            <

            MIN_SPATIAL_DISTANCE

        ):

            continue


        good_matches.append(

            m

        )


    # ==========================================
    # MATCHED POINT COUNT
    # ==========================================

    result["matched_points"] = (

        len(good_matches)

    )

    result["spatial_matches"] = (

        len(good_matches)

    )


    # ==========================================
    # NOT ENOUGH MATCHES
    # ==========================================

    if len(good_matches) < 4:

        if artifact_path:

            cv2.imwrite(

                str(artifact_path),

                image

            )

        return result


    # ==========================================
    # EXTRACT MATCH POINTS
    # ==========================================

    src_pts = np.float32([

        keypoints[
            match.queryIdx
        ].pt

        for match in good_matches

    ]).reshape(

        -1,

        1,

        2

    )


    dst_pts = np.float32([

        keypoints[
            match.trainIdx
        ].pt

        for match in good_matches

    ]).reshape(

        -1,

        1,

        2

    )


    # ==========================================
    # RANSAC HOMOGRAPHY
    # ==========================================

    try:

        homography, mask = cv2.findHomography(

            src_pts,

            dst_pts,

            cv2.RANSAC,

            5.0

        )

    except cv2.error:

        homography = None

        mask = None


    # ==========================================
    # HOMOGRAPHY FAILED
    # ==========================================

    if (

        homography is None

        or

        mask is None

    ):

        if artifact_path:

            cv2.imwrite(

                str(artifact_path),

                image

            )

        return result


    # ==========================================
    # RANSAC INLIERS
    # ==========================================

    inliers = int(

        mask.ravel().sum()

    )


    result["inliers"] = (

        inliers

    )


    # ==========================================
    # COPY-MOVE SCORE
    # ==========================================

    score = (

        inliers

        /

        max(

            len(good_matches),

            1

        )

    )


    result["copy_move_score"] = round(

        float(score),

        4

    )


    # ==========================================
    # DETECTION THRESHOLD
    #
    # We require both:
    #
    # - Minimum number of spatial matches
    # - Minimum RANSAC inliers
    # - Minimum inlier ratio
    #
    # This avoids declaring forgery from
    # a few random matches.
    # ==========================================

    copy_move_detected = (

        len(good_matches) >= 10

        and

        inliers >= 8

        and

        score >= 0.20

    )


    result["copy_move_detected"] = (

        copy_move_detected

    )


    # ==========================================
    # VERDICT
    # ==========================================

    if copy_move_detected:

        result["verdict"] = (

            "Potential Copy-Move Forgery"

        )


    # ==========================================
    # VISUALIZATION
    # ==========================================

    visualization = image.copy()


    for index, match in enumerate(

        good_matches

    ):

        # --------------------------------------
        # Only draw RANSAC inliers
        # --------------------------------------

        if mask[index]:

            x1, y1 = map(

                int,

                keypoints[
                    match.queryIdx
                ].pt

            )


            x2, y2 = map(

                int,

                keypoints[
                    match.trainIdx
                ].pt

            )


            # ----------------------------------
            # Draw source point
            # ----------------------------------

            cv2.circle(

                visualization,

                (x1, y1),

                6,

                (0, 0, 255),

                -1

            )


            # ----------------------------------
            # Draw destination point
            # ----------------------------------

            cv2.circle(

                visualization,

                (x2, y2),

                6,

                (0, 255, 0),

                -1

            )


            # ----------------------------------
            # Connect duplicated regions
            # ----------------------------------

            cv2.line(

                visualization,

                (x1, y1),

                (x2, y2),

                (255, 0, 0),

                1

            )


    # ==========================================
    # SAVE ARTIFACT
    # ==========================================

    if artifact_path:

        cv2.imwrite(

            str(artifact_path),

            visualization

        )


    # ==========================================
    # DEBUG
    # ==========================================

    print(

        "\n========== COPY-MOVE RESULT =========="

    )

    print(

        "Image:",

        image_path

    )

    print(

        "Keypoints:",

        len(keypoints)

    )

    print(

        "Spatial Matches:",

        len(good_matches)

    )

    print(

        "RANSAC Inliers:",

        inliers

    )

    print(

        "Copy-Move Score:",

        result["copy_move_score"]

    )

    print(

        "Detected:",

        copy_move_detected

    )

    print(

        "======================================\n"

    )


    return result