"""GradCAM saliency maps for CNN-based forensic models."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np

from backend.analysis.ml_models import _load_rgb_image, get_efficientnet_bundle

logger = logging.getLogger("ai_forge.gradcam")

TARGET_LAYER = "features"


def _normalize_cam(cam: np.ndarray) -> np.ndarray:
    cam = cam.astype(np.float32)
    lo, hi = float(cam.min()), float(cam.max())
    if hi - lo < 1e-8:
        return np.zeros_like(cam, dtype=np.float32)
    return (cam - lo) / (hi - lo)


def generate_gradcam(
    image_path: str,
    output_dir: str,
    target_score: float = 0.5,
) -> Dict[str, Any]:
    """Generate GradCAM heatmap explaining model focus regions."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    heatmap_path = out / "gradcam_heatmap.jpg"
    overlay_path = out / "gradcam_overlay.jpg"

    bundle = get_efficientnet_bundle()
    if not bundle:
        return _fallback_gradcam(image_path, str(heatmap_path), str(overlay_path))

    try:
        import torch

        rgb = _load_rgb_image(image_path, max_side=512)
        h, w = rgb.shape[:2]
        model = bundle["model"]
        device = bundle["device"]
        transform = bundle["transform"]

        activations = {}
        gradients = {}

        def fwd_hook(_module, _inp, output):
            activations["value"] = output.detach()

        def bwd_hook(_module, _grad_in, grad_out):
            gradients["value"] = grad_out[0].detach()

        last_block = model.features[-1]
        handle_f = last_block.register_forward_hook(fwd_hook)
        handle_b = last_block.register_full_backward_hook(bwd_hook)

        tensor = transform(rgb).unsqueeze(0).to(device)
        model.zero_grad()
        output = model(tensor)
        if output.ndim == 1:
            output = output.unsqueeze(0)
        score = output.sum()
        score.backward()

        handle_f.remove()
        handle_b.remove()

        acts = activations["value"][0]
        grads = gradients["value"][0]
        weights = grads.mean(dim=(1, 2))
        cam = torch.zeros(acts.shape[1:], device=device)
        for i, w in enumerate(weights):
            cam += w * acts[i]
        cam = torch.relu(cam).cpu().numpy()
        cam = _normalize_cam(cam)
        cam = cv2.resize(cam, (int(w), int(h)))

        colored = cv2.applyColorMap((cam * 255).astype(np.uint8), cv2.COLORMAP_JET)
        original = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        overlay = cv2.addWeighted(original, 0.55, colored, 0.45, 0)

        cv2.imwrite(str(heatmap_path), colored)
        cv2.imwrite(str(overlay_path), overlay)

        peak_y, peak_x = np.unravel_index(int(np.argmax(cam)), cam.shape)
        why = (
            f"GradCAM highlights pixels the EfficientNet backbone weighted most heavily "
            f"(peak at {peak_x},{peak_y}). High activation here drove the "
            f"{'manipulation' if target_score >= 0.5 else 'authenticity'} signal."
        )

        return {
            "method": "gradcam",
            "model": bundle.get("name", "efficientnet_b0"),
            "heatmap": str(heatmap_path),
            "overlay": str(overlay_path),
            "map": cam.tolist() if cam.size < 50000 else [],
            "peak": [int(peak_x), int(peak_y)],
            "score": float(np.mean(cam[cam > 0.6]) if np.any(cam > 0.6) else np.mean(cam)),
            "why": why,
            "confidence": 0.78,
        }
    except Exception as exc:
        logger.warning("GradCAM failed: %s", exc)
        return _fallback_gradcam(image_path, str(heatmap_path), str(overlay_path), error=str(exc))


def _fallback_gradcam(
    image_path: str,
    heatmap_path: str,
    overlay_path: str,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if gray is None:
        return {"method": "gradcam_heuristic", "error": error or "read failed", "why": "GradCAM unavailable."}
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    cam = _normalize_cam(np.abs(lap))
    colored = cv2.applyColorMap((cam * 255).astype(np.uint8), cv2.COLORMAP_JET)
    original = cv2.imread(image_path)
    overlay = cv2.addWeighted(original, 0.55, colored, 0.45, 0)
    cv2.imwrite(heatmap_path, colored)
    cv2.imwrite(overlay_path, overlay)
    return {
        "method": "gradcam_heuristic",
        "heatmap": heatmap_path,
        "overlay": overlay_path,
        "score": float(np.mean(cam)),
        "why": "GradCAM model unavailable — using edge-variance proxy to show suspicious texture regions.",
        "confidence": 0.45,
        "error": error,
    }
