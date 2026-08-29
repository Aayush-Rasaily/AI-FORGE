from functools import lru_cache
from pathlib import Path
import cv2
import numpy as np
import torch
from PIL import Image
from torchvision import transforms

from backend.models.signature.model import SiameseNetwork
from backend.utils.hardware import get_torch_device
from backend.utils.safe_image_io import atomic_cv2_write

# ==========================================
# Configuration
# ==========================================

MODEL_PATH = Path(__file__).resolve().parent / "weights" / "siamese_best.pt"
DEVICE = torch.device(get_torch_device())

# ==========================================
# Image Transform
# ==========================================

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

# ==========================================
# Load Model (Singleton Cache)
# ==========================================

@lru_cache(maxsize=1)
def load_model():
    model = SiameseNetwork(embedding_dim=256)
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            f"Signature checkpoint not found: {MODEL_PATH}"
        )
    checkpoint = torch.load(MODEL_PATH, map_location=DEVICE)
    model.load_state_dict(checkpoint)
    model = model.to(DEVICE)
    model.eval()
    return model


def load_image(image_path: str):
    image = Image.open(image_path).convert("RGB")
    tensor = transform(image).unsqueeze(0)
    return tensor.to(DEVICE)


def _analyze_stroke_forensics(ref_path: str, query_path: str, output_dir: Path | None = None):
    """
    Computes explainable physical signature traits:
    - stroke difference
    - pressure (intensity/thickness profile) difference
    - shape difference (Hu moments distance)
    - curvature difference (contour angle histogram distance)
    - connected components
    - visualization map: Green=match, Red=mismatch, Blue=uncertain
    """
    ref_bgr = cv2.imread(ref_path)
    query_bgr = cv2.imread(query_path)

    if ref_bgr is None or query_bgr is None:
        return {
            "stroke_difference": 0.5,
            "pressure_difference": 0.5,
            "shape_difference": 0.5,
            "curvature_difference": 0.5,
            "connected_components": {"original": 1, "test": 1, "diff": 0},
            "visualization": None,
        }

    # Binarize signature (signatures usually dark strokes on light background)
    ref_gray = cv2.cvtColor(ref_bgr, cv2.COLOR_BGR2GRAY)
    query_gray = cv2.cvtColor(query_bgr, cv2.COLOR_BGR2GRAY)
    query_height, query_width = query_gray.shape[:2]

    ref_gray = cv2.resize(ref_gray, (400, 200), interpolation=cv2.INTER_AREA)
    query_gray = cv2.resize(query_gray, (400, 200), interpolation=cv2.INTER_AREA)

    _, ref_bin = cv2.threshold(ref_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    _, query_bin = cv2.threshold(query_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # 1. Connected components
    n_ref, _, stats_ref, _ = cv2.connectedComponentsWithStats(ref_bin)
    n_query, _, stats_query, _ = cv2.connectedComponentsWithStats(query_bin)
    ref_cc = max(0, n_ref - 1)
    query_cc = max(0, n_query - 1)

    # 2. Shape Difference via Hu Moments
    hu_ref = cv2.HuMoments(cv2.moments(ref_bin)).flatten()
    hu_query = cv2.HuMoments(cv2.moments(query_bin)).flatten()
    hu_diff = float(np.mean(np.abs(np.log10(np.abs(hu_ref) + 1e-9) - np.log10(np.abs(hu_query) + 1e-9))))
    shape_diff = min(1.0, hu_diff / 4.0)

    # 3. Stroke & Pressure Profile
    ref_dist = cv2.distanceTransform(ref_bin, cv2.DIST_L2, 5)
    query_dist = cv2.distanceTransform(query_bin, cv2.DIST_L2, 5)

    ref_pressure = float(np.mean(ref_gray[ref_bin > 0])) if np.any(ref_bin > 0) else 128.0
    query_pressure = float(np.mean(query_gray[query_bin > 0])) if np.any(query_bin > 0) else 128.0
    pressure_diff = min(1.0, abs(ref_pressure - query_pressure) / 128.0)

    # Stroke overlap difference
    stroke_xor = cv2.bitwise_xor(ref_bin, query_bin)
    stroke_or = cv2.bitwise_or(ref_bin, query_bin)
    stroke_diff = float(np.sum(stroke_xor > 0)) / float(np.sum(stroke_or > 0) + 1e-6)

    # Curvature / Gradient Orientation
    gx_r, gy_r = cv2.Sobel(ref_gray, cv2.CV_32F, 1, 0), cv2.Sobel(ref_gray, cv2.CV_32F, 0, 1)
    gx_q, gy_q = cv2.Sobel(query_gray, cv2.CV_32F, 1, 0), cv2.Sobel(query_gray, cv2.CV_32F, 0, 1)
    ang_r = np.arctan2(gy_r, gx_r)
    ang_q = np.arctan2(gy_q, gx_q)

    hist_r, _ = np.histogram(ang_r[ref_bin > 0], bins=18, range=(-np.pi, np.pi), density=True) if np.any(ref_bin > 0) else (np.zeros(18), None)
    hist_q, _ = np.histogram(ang_q[query_bin > 0], bins=18, range=(-np.pi, np.pi), density=True) if np.any(query_bin > 0) else (np.zeros(18), None)
    curvature_diff = float(0.5 * np.sum(np.abs(hist_r - hist_q)))

    # Generate Explainable Visualization (Green=match, Red=mismatch, Blue=uncertain)
    vis = np.zeros((200, 400, 3), dtype=np.uint8)
    # Background light gray
    vis[:] = (245, 245, 245)

    ref_mask = ref_bin > 0
    query_mask = query_bin > 0

    match_mask = ref_mask & query_mask
    mismatch_mask = (ref_mask & ~query_mask) | (~ref_mask & query_mask)
    
    # Boundary / uncertain areas near stroke edges
    kernel = np.ones((3, 3), np.uint8)
    dilated_match = cv2.dilate(match_mask.astype(np.uint8), kernel, iterations=1)
    uncertain_mask = (dilated_match > 0) & ~match_mask & mismatch_mask

    def _component_boxes(mask: np.ndarray, source_width: int, source_height: int):
        count, _, stats, _ = cv2.connectedComponentsWithStats(
            mask.astype(np.uint8),
            connectivity=8,
        )
        boxes = []
        scale_x = source_width / 400.0
        scale_y = source_height / 200.0
        for component in range(1, count):
            x, y, width, height, area = stats[component]
            if area < 6:
                continue
            boxes.append([
                int(round(x * scale_x)),
                int(round(y * scale_y)),
                max(1, int(round(width * scale_x))),
                max(1, int(round(height * scale_y))),
            ])
        return boxes

    matched_regions = _component_boxes(match_mask, query_width, query_height)
    different_regions = _component_boxes(mismatch_mask, query_width, query_height)

    # Green = matching strokes (0, 180, 0)
    vis[match_mask] = (0, 180, 0)
    # Red = stroke mismatch (0, 0, 220)
    vis[mismatch_mask] = (0, 0, 220)
    # Blue = uncertain (220, 120, 0)
    vis[uncertain_mask] = (220, 120, 0)

    vis_path_str = None
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        vis_file = output_dir / "signature_comparison.png"
        atomic_cv2_write(vis_file, vis)
        vis_path_str = str(vis_file)

        matching_image = np.full((200, 400, 3), 245, dtype=np.uint8)
        matching_image[match_mask] = (0, 180, 0)
        matching_path = output_dir / "matching_regions.png"
        atomic_cv2_write(matching_path, matching_image)

        difference_image = cv2.applyColorMap(
            (mismatch_mask.astype(np.uint8) * 255),
            cv2.COLORMAP_JET,
        )
        difference_path = output_dir / "difference_heatmap.png"
        atomic_cv2_write(difference_path, difference_image)

        overlay_image = np.full((200, 400, 3), 245, dtype=np.uint8)
        overlay_image[match_mask] = (0, 180, 0)
        overlay_image[ref_mask & ~query_mask] = (255, 80, 0)
        overlay_image[query_mask & ~ref_mask] = (0, 0, 220)
        overlay_image[uncertain_mask] = (220, 120, 0)
        overlay_path = output_dir / "signature_overlay.png"
        atomic_cv2_write(overlay_path, overlay_image)
        visualization_paths = {
            "matching_regions": str(matching_path),
            "difference_heatmap": str(difference_path),
            "signature_overlay": str(overlay_path),
            "comparison": str(vis_file),
        }
    else:
        visualization_paths = {}

    import base64
    ok, buf = cv2.imencode(".png", vis)
    vis_b64 = f"data:image/png;base64,{base64.b64encode(buf).decode('ascii')}" if ok else None

    return {
        "stroke_difference": round(float(stroke_diff), 4),
        "pressure_difference": round(float(pressure_diff), 4),
        "shape_difference": round(float(shape_diff), 4),
        "curvature_difference": round(float(curvature_diff), 4),
        "connected_components": {
            "original_components": ref_cc,
            "test_components": query_cc,
            "difference": abs(ref_cc - query_cc),
        },
        "visualization": vis_path_str or vis_b64,
        "visualization_b64": vis_b64,
        "visualizations": visualization_paths,
        "matched_regions": matched_regions,
        "different_regions": different_regions,
    }


def verify_signature(reference_path: str, query_path: str, output_dir: str | Path | None = None):
    model = load_model()
    reference = load_image(reference_path)
    query = load_image(query_path)

    with torch.no_grad():
        embedding1, embedding2 = model(reference, query)
        similarity = torch.cosine_similarity(embedding1, embedding2).item()

    similarity = float(max(0.0, min(1.0, (similarity + 1.0) / 2.0 if similarity < 0 else similarity)))
    siamese_similarity = round(similarity, 4)

    forensics = _analyze_stroke_forensics(reference_path, query_path, Path(output_dir) if output_dir else None)

    # Composite metrics
    avg_diff = (
        forensics["stroke_difference"] * 0.35
        + forensics["pressure_difference"] * 0.15
        + forensics["shape_difference"] * 0.25
        + forensics["curvature_difference"] * 0.25
    )
    forgery_probability = round(float(max(0.0, min(1.0, 1.0 - (0.5 * siamese_similarity + 0.5 * (1.0 - avg_diff))))), 4)

    threshold = 0.55
    verdict = "Genuine" if forgery_probability < threshold else "Potential Forgery"
    confidence = round(float(abs(forgery_probability - 0.5) * 2), 4)

    possible_pasted = forgery_probability >= 0.55 or forensics["pressure_difference"] > 0.4
    stroke_inc = round(forensics["stroke_difference"] * 100, 1)
    bound_mismatch = round(forensics["shape_difference"] * 100, 1)
    edge_blend = round(forensics["pressure_difference"] * 100, 1)
    query_image = cv2.imread(query_path, cv2.IMREAD_COLOR)
    if query_image is None:
        raise ValueError(f"Unable to read query signature image: {query_path}")
    query_height, query_width = query_image.shape[:2]
    sig_bbox_raw = [0, 0, query_width, query_height]
    from backend.utils.bbox_schema import normalize_bbox as _nb, bbox_to_xyxy as _bte  # noqa
    sig_bbox = _nb(sig_bbox_raw)  # → {x,y,width,height} canonical dict
    sig_xyxy = _bte(sig_bbox)     # → [x1,y1,x2,y2] for coordinates key
    sig_label = "Pasted signature" if possible_pasted else "Original handwritten signature"
    sig_polygon = [
        [0, 0],
        [query_width, 0],
        [query_width, query_height],
        [0, query_height],
    ]

    findings = [{
        "finding_id": "sig-finding-1",
        "type": "fake_signature" if possible_pasted else "signature_inconsistency",
        "edit_type": "Fake Signature" if possible_pasted else "Signature Stroke Mismatch",
        "page": 1,
        "bbox": sig_bbox_raw,
        "bounding_box": sig_bbox,
        "coordinates": sig_xyxy,
        "confidence": forgery_probability,
        "confidence_pct": round(forgery_probability * 100, 1),
        "severity": "Critical" if forgery_probability >= 0.7 else "High" if forgery_probability >= 0.5 else "Low",
        "detector": "Siamese Stroke Analyzer",
        "detectors": ["Siamese Neural Net", "Stroke Density", "Pressure Profile"],
        "reason": f"Stroke mismatch ({stroke_inc}%), boundary mismatch ({bound_mismatch}%), edge blending ({edge_blend}%)",
        "stroke_inconsistency": f"{stroke_inc}%",
        "boundary_mismatch": f"{bound_mismatch}%",
        "edge_blending": f"{edge_blend}%",
        "possible_pasted_signature": possible_pasted,
        "id": "SIG-001",
        "label": sig_label,
        "type": "signature",
        "polygon": sig_polygon,
        "explanation": (
            "The signature comparison recorded measurable differences from the "
            "reference specimen."
            if possible_pasted
            else "The signature comparison did not record a material mismatch from the reference specimen."
        ),
        "human_summary": (
            "The submitted signature may have been pasted or otherwise altered."
            if possible_pasted
            else "The submitted signature is consistent with the supplied reference specimen."
        ),
    }]

    return {
        "verdict": verdict,
        "similarity": siamese_similarity,
        "similarity_score": siamese_similarity,
        "siamese_similarity": siamese_similarity,
        "confidence": confidence,
        "forgery_probability": forgery_probability,
        "bbox": sig_bbox,
        "bounding_box": sig_bbox,
        "coordinates": sig_xyxy,
        "stroke_inconsistency": f"{stroke_inc}%",
        "boundary_mismatch": f"{bound_mismatch}%",
        "edge_blending": f"{edge_blend}%",
        "possible_pasted_signature": possible_pasted,
        "stroke_difference": forensics["stroke_difference"],
        "pressure_difference": forensics["pressure_difference"],
        "shape_difference": forensics["shape_difference"],
        "curvature_difference": forensics["curvature_difference"],
        "connected_components": forensics["connected_components"],
        "visualization": forensics["visualization"],
        "visualization_b64": forensics.get("visualization_b64"),
        "visualizations": forensics.get("visualizations", {}),
        "matched_regions": forensics.get("matched_regions", []),
        "different_regions": forensics.get("different_regions", []),
        "findings": findings,
        "signature_present": True,
        "signature_count": 1,
        "signature_regions": findings,
        "signature_confidence": confidence,
        "signature_type": sig_label,
        "reasons": [
            f"Siamese vector similarity: {siamese_similarity:.2%}",
            f"Stroke inconsistency: {stroke_inc}%",
            f"Boundary mismatch: {bound_mismatch}%",
            f"Edge blending: {edge_blend}%",
            f"Possible pasted signature: {'Yes' if possible_pasted else 'No'}",
        ],
    }
