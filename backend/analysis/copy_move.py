from pathlib import Path

import cv2
import numpy as np

from backend.utils.safe_image_io import atomic_cv2_write, safe_image_copy


def detect_copy_move(image_path, output_dir=None):
    """
    Detect possible copy-move forgery using ORB feature matching.

    Never reads the original upload directly — uses a temp copy to avoid
    WinError 32 file-lock conflicts on Windows.
    """
    image_path = Path(image_path)
    artifact_path = None
    legacy_path = None

    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = output_dir / "copymove.png"
        legacy_path = output_dir / f"{image_path.stem}_copy_move.jpg"

    result = {
        "verdict": "No Copy-Move Detected",
        "copy_move_detected": False,
        "copy_move_score": 0.0,
        "matched_points": 0,
        "inliers": 0,
        "spatial_matches": 0,
        "artifact": str(artifact_path) if artifact_path else None,
        "legacy_artifact": str(legacy_path) if legacy_path else None,
    }

    image = None
    gray = None
    visualization = None
    orb = None
    keypoints = None
    descriptors = None

    try:
        with safe_image_copy(image_path) as tmp_path:
            image = cv2.imread(str(tmp_path))
            if image is None:
                raise ValueError(f"Unable to read image: {image_path}")

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        max_side = 1200
        if max(h, w) > max_side:
            scale = max_side / max(h, w)
            gray = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

        orb = cv2.ORB_create(
            nfeatures=2800,
            scaleFactor=1.2,
            nlevels=6,
            edgeThreshold=31,
            patchSize=31,
            fastThreshold=12,
        )
        keypoints, descriptors = orb.detectAndCompute(gray, None)

        if descriptors is None or len(keypoints) < 10:
            if artifact_path:
                atomic_cv2_write(artifact_path, image)
            return result

        matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        matches = matcher.knnMatch(descriptors, descriptors, k=2)

        RATIO_THRESHOLD = 0.75
        MIN_SPATIAL_DISTANCE = 50
        MAX_CANDIDATES = 250
        good_matches = []

        for pair in matches:
            if len(pair) < 2:
                continue
            m, n = pair[0], pair[1]
            if m.queryIdx == m.trainIdx:
                continue
            if m.distance >= RATIO_THRESHOLD * n.distance:
                continue
            p1 = np.array(keypoints[m.queryIdx].pt)
            p2 = np.array(keypoints[m.trainIdx].pt)
            if np.linalg.norm(p1 - p2) < MIN_SPATIAL_DISTANCE:
                continue
            good_matches.append(m)
            if len(good_matches) >= MAX_CANDIDATES:
                break

        result["matched_points"] = len(good_matches)
        result["spatial_matches"] = len(good_matches)

        if len(good_matches) < 4:
            if artifact_path:
                atomic_cv2_write(artifact_path, image)
            return result

        src_pts = np.float32([keypoints[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([keypoints[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

        try:
            homography, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        except cv2.error:
            homography, mask = None, None

        if homography is None or mask is None:
            if artifact_path:
                atomic_cv2_write(artifact_path, image)
            return result

        inliers = int(mask.ravel().sum())
        result["inliers"] = inliers
        score = inliers / max(len(good_matches), 1)
        result["copy_move_score"] = round(float(score), 4)

        copy_move_detected = len(good_matches) >= 10 and inliers >= 8 and score >= 0.20
        result["copy_move_detected"] = copy_move_detected
        if copy_move_detected:
            result["verdict"] = "Potential Copy-Move Forgery"

        visualization = image.copy()
        for index, match in enumerate(good_matches):
            if mask[index]:
                x1, y1 = map(int, keypoints[match.queryIdx].pt)
                x2, y2 = map(int, keypoints[match.trainIdx].pt)
                cv2.circle(visualization, (x1, y1), 6, (0, 0, 255), -1)
                cv2.circle(visualization, (x2, y2), 6, (0, 255, 0), -1)
                cv2.line(visualization, (x1, y1), (x2, y2), (255, 0, 0), 1)

        if artifact_path:
            atomic_cv2_write(artifact_path, visualization)
            if legacy_path:
                try:
                    atomic_cv2_write(legacy_path, visualization)
                except Exception:
                    pass

        return result

    finally:
        image = None
        gray = None
        visualization = None
        orb = None
        keypoints = None
        descriptors = None
