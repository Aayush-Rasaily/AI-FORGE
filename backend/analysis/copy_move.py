from pathlib import Path
import cv2
import numpy as np
from backend.utils.safe_image_io import atomic_cv2_write, safe_image_copy

def _extract_multi_feature_matches(gray: np.ndarray):
    """
    Combines ORB, SIFT, BRISK, and AKAZE feature matchers for robust clone detection.
    Returns combined good keypoint match pairs [(pt1, pt2), ...].
    """
    match_pairs = []

    # 1. ORB Detector
    try:
        orb = cv2.ORB_create(nfeatures=3000, scaleFactor=1.2, nlevels=6, patchSize=31, fastThreshold=10)
        kp_orb, des_orb = orb.detectAndCompute(gray, None)
        if des_orb is not None and len(kp_orb) >= 10:
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
            knn = bf.knnMatch(des_orb, des_orb, k=2)
            for pair in knn:
                if len(pair) == 2 and pair[0].queryIdx != pair[0].trainIdx:
                    m, n = pair[0], pair[1]
                    if m.distance < 0.75 * n.distance:
                        p1 = np.array(kp_orb[m.queryIdx].pt)
                        p2 = np.array(kp_orb[m.trainIdx].pt)
                        if np.linalg.norm(p1 - p2) > 40:
                            match_pairs.append((p1, p2))
    except Exception:
        pass

    # 2. SIFT Detector
    try:
        sift = cv2.SIFT_create(nfeatures=2000)
        kp_sift, des_sift = sift.detectAndCompute(gray, None)
        if des_sift is not None and len(kp_sift) >= 10:
            bf = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
            knn = bf.knnMatch(des_sift, des_sift, k=2)
            for pair in knn:
                if len(pair) == 2 and pair[0].queryIdx != pair[0].trainIdx:
                    m, n = pair[0], pair[1]
                    if m.distance < 0.70 * n.distance:
                        p1 = np.array(kp_sift[m.queryIdx].pt)
                        p2 = np.array(kp_sift[m.trainIdx].pt)
                        if np.linalg.norm(p1 - p2) > 40:
                            match_pairs.append((p1, p2))
    except Exception:
        pass

    # 3. AKAZE Detector
    try:
        akaze = cv2.AKAZE_create()
        kp_akaze, des_akaze = akaze.detectAndCompute(gray, None)
        if des_akaze is not None and len(kp_akaze) >= 10:
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
            knn = bf.knnMatch(des_akaze, des_akaze, k=2)
            for pair in knn:
                if len(pair) == 2 and pair[0].queryIdx != pair[0].trainIdx:
                    m, n = pair[0], pair[1]
                    if m.distance < 0.72 * n.distance:
                        p1 = np.array(kp_akaze[m.queryIdx].pt)
                        p2 = np.array(kp_akaze[m.trainIdx].pt)
                        if np.linalg.norm(p1 - p2) > 40:
                            match_pairs.append((p1, p2))
    except Exception:
        pass

    # 4. BRISK Detector
    try:
        brisk = cv2.BRISK_create()
        kp_brisk, des_brisk = brisk.detectAndCompute(gray, None)
        if des_brisk is not None and len(kp_brisk) >= 10:
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
            knn = bf.knnMatch(des_brisk, des_brisk, k=2)
            for pair in knn:
                if len(pair) == 2 and pair[0].queryIdx != pair[0].trainIdx:
                    m, n = pair[0], pair[1]
                    if m.distance < 0.72 * n.distance:
                        p1 = np.array(kp_brisk[m.queryIdx].pt)
                        p2 = np.array(kp_brisk[m.trainIdx].pt)
                        if np.linalg.norm(p1 - p2) > 40:
                            match_pairs.append((p1, p2))
    except Exception:
        pass

    # 5. Fast Block Matching / PatchMatch fallback if feature count low
    if len(match_pairs) < 6:
        try:
            h, w = gray.shape
            block_size = 16
            step = 16
            blocks = []
            coords = []
            for y in range(0, h - block_size + 1, step):
                for x in range(0, w - block_size + 1, step):
                    blk = gray[y:y + block_size, x:x + block_size].flatten().astype(np.float32)
                    norm = np.linalg.norm(blk)
                    if norm > 10.0:
                        blocks.append(blk / norm)
                        coords.append((x + block_size // 2, y + block_size // 2))
            if len(blocks) > 20:
                blocks_arr = np.array(blocks)
                sim_mat = np.dot(blocks_arr, blocks_arr.T)
                np.fill_diagonal(sim_mat, 0)
                high_sim = np.argwhere(sim_mat > 0.96)
                for idx1, idx2 in high_sim[:50]:
                    if idx1 < idx2:
                        p1 = np.array(coords[idx1], dtype=np.float32)
                        p2 = np.array(coords[idx2], dtype=np.float32)
                        if np.linalg.norm(p1 - p2) > 50:
                            match_pairs.append((p1, p2))
        except Exception:
            pass

    return match_pairs


def _cluster_matches(match_pairs, max_clusters=12):
    """Group pairs into spatial clusters representing cohesive clone operations and filter with RANSAC."""
    import cv2
    if not match_pairs:
        return []
    
    # Calculate shift vectors (dx, dy)
    shifts = [p2 - p1 for p1, p2 in match_pairs]
    shifts_arr = np.array(shifts)

    clusters = []
    visited = [False] * len(match_pairs)

    for i in range(len(match_pairs)):
        if visited[i]:
            continue
        cluster = [match_pairs[i]]
        visited[i] = True
        shift_i = shifts_arr[i]
        for j in range(i + 1, len(match_pairs)):
            if visited[j]:
                continue
            shift_j = shifts_arr[j]
            if np.linalg.norm(shift_i - shift_j) < 35.0:
                cluster.append(match_pairs[j])
                visited[j] = True
                
        # RANSAC filtering per cluster
        if len(cluster) >= 4:
            src_pts = np.float32([p[0] for p in cluster]).reshape(-1, 1, 2)
            dst_pts = np.float32([p[1] for p in cluster]).reshape(-1, 1, 2)
            # Find affine transformation (allows rotation, scale, translation)
            M, inliers = cv2.estimateAffinePartial2D(src_pts, dst_pts, method=cv2.RANSAC, ransacReprojThreshold=5.0)
            if inliers is not None:
                inlier_cluster = [cluster[idx] for idx, val in enumerate(inliers) if val == 1]
                if len(inlier_cluster) >= 3:
                    clusters.append(inlier_cluster)
        elif len(cluster) == 3:
            clusters.append(cluster)

    clusters.sort(key=lambda c: len(c), reverse=True)
    return clusters[:max_clusters]


def detect_copy_move(image_path, output_dir=None):
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
        "duplicated_regions": [],
        "artifact": str(artifact_path) if artifact_path else None,
        "legacy_artifact": str(legacy_path) if legacy_path else None,
    }

    try:
        with safe_image_copy(image_path) as tmp_path:
            image = cv2.imread(str(tmp_path))
            if image is None:
                raise ValueError(f"Unable to read image: {image_path}")

        orig_h, orig_w = image.shape[:2]
        max_side = 1200
        scale = 1.0
        if max(orig_h, orig_w) > max_side:
            scale = max_side / max(orig_h, orig_w)
            resized_img = cv2.resize(image, (int(orig_w * scale), int(orig_h * scale)), interpolation=cv2.INTER_AREA)
        else:
            resized_img = image.copy()

        gray = cv2.cvtColor(resized_img, cv2.COLOR_BGR2GRAY)
        match_pairs = _extract_multi_feature_matches(gray)

        result["matched_points"] = len(match_pairs)
        result["spatial_matches"] = len(match_pairs)

        if len(match_pairs) < 4:
            if artifact_path:
                atomic_cv2_write(artifact_path, image)
            return result

        clusters = _cluster_matches(match_pairs)
        inliers_count = sum(len(c) for c in clusters)
        score = round(min(1.0, inliers_count / max(len(match_pairs), 10)), 4)

        copy_move_detected = len(clusters) > 0 or (len(match_pairs) >= 12 and inliers_count >= 6)
        result["copy_move_detected"] = copy_move_detected
        result["inliers"] = inliers_count
        result["copy_move_score"] = score
        if copy_move_detected:
            result["verdict"] = "Potential Copy-Move Forgery"

        # Color Palette for Directional Match Arrows
        palette = [
            (0, 255, 255),  # Yellow
            (255, 0, 255),  # Magenta
            (0, 255, 0),    # Bright Green
            (255, 128, 0),  # Orange
            (255, 0, 128),  # Rose
            (0, 128, 255),  # Cyan
            (128, 255, 0),  # Lime
            (128, 0, 255),  # Purple
        ]

        visualization = resized_img.copy()
        duplicated_regions = []

        for idx, cluster in enumerate(clusters):
            color = palette[idx % len(palette)]
            src_pts = np.array([p1 for p1, p2 in cluster])
            dst_pts = np.array([p2 for p1, p2 in cluster])

            src_center = np.mean(src_pts, axis=0)
            dst_center = np.mean(dst_pts, axis=0)

            # Draw directional arrow from Original Area -> Copied Area
            pt1 = (int(src_center[0]), int(src_center[1]))
            pt2 = (int(dst_center[0]), int(dst_center[1]))

            cv2.arrowedLine(visualization, pt1, pt2, color, 3, tipLength=0.25)
            cv2.circle(visualization, pt1, 8, (0, 255, 0), -1)  # Green = Source
            cv2.circle(visualization, pt2, 8, (0, 0, 255), -1)  # Red = Target

            for p1, p2 in cluster:
                cv2.line(visualization, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), color, 1)

            s_min = np.min(src_pts, axis=0) / scale
            s_max = np.max(src_pts, axis=0) / scale
            d_min = np.min(dst_pts, axis=0) / scale
            d_max = np.max(dst_pts, axis=0) / scale
            
            s_min_x, s_min_y = s_min[0], s_min[1]
            s_max_x, s_max_y = s_max[0], s_max[1]
            d_min_x, d_min_y = d_min[0], d_min[1]
            d_max_x, d_max_y = d_max[0], d_max[1]

            s_w = int(s_max_x - s_min_x)
            s_h = int(s_max_y - s_min_y)
            d_w = int(d_max_x - d_min_x)
            d_h = int(d_max_y - d_min_y)
            if s_w <= 0 or s_h <= 0:
                s_w, s_h = max(s_w, 16), max(s_h, 16)
                s_min_x = int(src_center[0] / scale) - s_w // 2
                s_min_y = int(src_center[1] / scale) - s_h // 2
            if d_w <= 0 or d_h <= 0:
                d_w, d_h = max(d_w, 16), max(d_h, 16)
                d_min_x = int(dst_center[0] / scale) - d_w // 2
                d_min_y = int(dst_center[1] / scale) - d_h // 2

            # Semantic classification based on bounding box
            classification = "duplicated region"
            if s_h > 0 and s_w > 0:
                aspect_ratio = s_w / float(s_h)
                area = s_w * s_h
                if aspect_ratio > 2.5 and s_h < 100:
                    classification = "copied text"
                elif 0.8 <= aspect_ratio <= 1.2 and area > 10000:
                    classification = "copied logo"
                elif 1.2 < aspect_ratio <= 2.5 and 2000 < area < 20000:
                    classification = "cloned signature"

            duplicated_regions.append({
                "cluster_id": idx + 1,
                "classification": classification,
                "confidence": round(min(0.99, 0.6 + len(cluster) * 0.05), 2),
                "original_area": {
                    "center": [int(src_center[0] / scale), int(src_center[1] / scale)],
                    "bbox": [int(s_min_x), int(s_min_y), s_w, s_h],
                },
                "copied_area": {
                    "center": [int(dst_center[0] / scale), int(dst_center[1] / scale)],
                    "bbox": [int(d_min_x), int(d_min_y), d_w, d_h],
                },
                "matched_keypoints": len(cluster),
                "arrow_color_rgb": [int(color[2]), int(color[1]), int(color[0])],
            })

        # Scale visualization to match original if needed
        if scale != 1.0:
            visualization = cv2.resize(visualization, (orig_w, orig_h), interpolation=cv2.INTER_CUBIC)

        result["duplicated_regions"] = duplicated_regions

        if output_dir:
            import json
            json_path = output_dir / "copymove.json"
            with open(json_path, "w") as f:
                json.dump(result, f, indent=2)

        if artifact_path:
            atomic_cv2_write(artifact_path, visualization)
            if legacy_path:
                try:
                    atomic_cv2_write(legacy_path, visualization)
                except Exception:
                    pass

        return result
    except Exception as exc:
        if artifact_path and 'image' in locals() and image is not None:
            atomic_cv2_write(artifact_path, image)
        return result

