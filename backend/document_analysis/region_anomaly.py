from pathlib import Path

import cv2
import numpy as np

from backend.document_analysis.text_layout_analysis import (
    analyze_text_layout
)

from backend.document_analysis.font_consistency import (
    analyze_font_consistency
)

from backend.document_analysis.spacing_analysis import (
    analyze_spacing
)


# ==========================================
# Crop Region
# ==========================================

def crop_region(image, bbox):

    xs = [int(p[0]) for p in bbox]
    ys = [int(p[1]) for p in bbox]

    x1 = max(min(xs), 0)
    x2 = min(max(xs), image.shape[1])

    y1 = max(min(ys), 0)
    y2 = min(max(ys), image.shape[0])

    return image[y1:y2, x1:x2]


# ==========================================
# Region Metrics
# ==========================================

def region_metrics(region):

    gray = cv2.cvtColor(

        region,

        cv2.COLOR_BGR2GRAY

    )

    edges = cv2.Canny(

        gray,

        100,

        200

    )

    edge_density = (

        np.sum(edges > 0)

        /

        (gray.size + 1)

    )

    noise = np.std(gray)

    brightness = np.mean(gray)

    lap = cv2.Laplacian(

        gray,

        cv2.CV_64F

    )

    texture = lap.var()

    return {

        "edge_density":

            round(float(edge_density),4),

        "noise":

            round(float(noise),2),

        "brightness":

            round(float(brightness),2),

        "texture":

            round(float(texture),2)

    }


# ==========================================
# Main
# ==========================================

def analyze_region_anomaly(image_path, layout_data=None, font_data=None, spacing_data=None, analysis_dir=None):
    image_path = Path(image_path)
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"Cannot read image: {image_path}")

    layout = layout_data or analyze_text_layout(image_path, analysis_dir=analysis_dir)
    font = font_data or analyze_font_consistency(image_path, layout_data=layout, analysis_dir=analysis_dir)
    spacing = spacing_data or analyze_spacing(image_path, layout_data=layout, analysis_dir=analysis_dir)

    suspicious_words = {w["text"] for w in font.get("suspicious_words", [])}
    suspicious_lines = {
        l["line"] for l in spacing.get("lines", []) if l.get("spacing_anomaly")
    }

    regions = []
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    tile_size = 64 if max(h, w) > 1200 else 32

    # Adaptive tile scan — only deep-analyze suspicious tiles
    tile_scores = []
    for y in range(0, h - tile_size, tile_size):
        for x in range(0, w - tile_size, tile_size):
            tile = gray[y: y + tile_size, x: x + tile_size]
            edges = cv2.Canny(tile, 80, 160)
            edge_density = float(np.count_nonzero(edges)) / edges.size
            texture = float(cv2.Laplacian(tile, cv2.CV_64F).var())
            quick_score = edge_density * 100 + texture / 200.0
            tile_scores.append((quick_score, x, y, edge_density, texture))

    tile_scores.sort(reverse=True)
    suspicious_tiles = [t for t in tile_scores if t[0] > 8.0][:24]

    for quick_score, x, y, edge_density, texture in suspicious_tiles:
        crop = image[y: y + tile_size, x: x + tile_size]
        metrics = region_metrics(crop)
        score = min(100, quick_score * 3)
        reasons = ["Adaptive tile anomaly"]
        if metrics["noise"] > 45:
            score += 15
            reasons.append("Noise variation")
        if edge_density > 0.18:
            score += 10
            reasons.append("High edge density")
        if score >= 40:
            regions.append({
                "bbox": [[x, y], [x + tile_size, y], [x + tile_size, y + tile_size], [x, y + tile_size]],
                "score": round(score, 2),
                "reasons": reasons,
                "metrics": metrics,
            })

    # Word-level refinement for layout-flagged words only
    for line in layout.get("lines", []):
        line_no = line["line_number"]
        for word in line.get("words", []):
            if word["text"] not in suspicious_words and line_no not in suspicious_lines:
                continue
            crop = crop_region(image, word["bbox"])
            if crop.size == 0:
                continue
            metrics = region_metrics(crop)
            score = 0
            reasons = []
            if word["text"] in suspicious_words:
                score += 40
                reasons.append("Font inconsistency")
            if line_no in suspicious_lines:
                score += 25
                reasons.append("Layout anomaly")
            if metrics["noise"] > 45:
                score += 15
                reasons.append("Noise variation")
            if metrics["edge_density"] > 0.18:
                score += 10
                reasons.append("High edge density")
            if score >= 40:
                regions.append({
                    "text": word["text"],
                    "bbox": word["bbox"],
                    "score": score,
                    "reasons": reasons,
                    "metrics": metrics,
                })

    high_risk = [r for r in regions if r.get("score", 0) >= 60]
    overall = float(np.mean([r.get("score", 0) for r in regions])) if regions else 0.0

    if overall >= 60:
        verdict = "High Risk"
    elif overall >= 35:
        verdict = "Moderate Risk"
    else:
        verdict = "Low Risk"

    return {
        "overall_score": round(overall, 2),
        "overall_verdict": verdict,
        "regions": regions,
        "high_risk_regions": high_risk,
        "tile_size": tile_size,
    }
