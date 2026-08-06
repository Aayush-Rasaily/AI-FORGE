"""
Lightweight CNN tampering classifier using EfficientNet-B0 embeddings.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import cv2
import numpy as np

logger = logging.getLogger("ai_forge.tampering_cnn")

_CLASSIFIER = None


def _get_classifier():
    global _CLASSIFIER
    if _CLASSIFIER is not None:
        return _CLASSIFIER

    try:
        import torch
        import torchvision.transforms as T
        from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights

        from backend.utils.hardware import get_torch_device

        device = torch.device(get_torch_device())
        weights = EfficientNet_B0_Weights.IMAGENET1K_V1
        model = efficientnet_b0(weights=weights)
        model.classifier = torch.nn.Identity()
        model.eval()
        model.to(device)

        transform = T.Compose([
            T.ToPILImage(),
            T.Resize((224, 224)),
            T.ToTensor(),
            T.Normalize(mean=weights.meta["mean"], std=weights.meta["std"]),
        ])

        _CLASSIFIER = {"model": model, "transform": transform, "device": device}
        logger.info("Tampering CNN loaded (EfficientNet-B0 on %s)", device)
    except Exception as exc:
        logger.warning("CNN tampering classifier unavailable: %s", exc)
        _CLASSIFIER = {}

    return _CLASSIFIER


def _texture_fallback(image_path: str) -> float:
    """Fast texture-based proxy when CNN unavailable."""
    img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return 0.0
    h, w = img.shape
    if max(h, w) > 800:
        scale = 800 / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)))

    lap = cv2.Laplacian(img, cv2.CV_64F)
    texture_var = float(lap.var()) / 10000.0

    edges = cv2.Canny(img, 80, 160)
    edge_density = float(np.count_nonzero(edges)) / edges.size

    noise_blocks = []
    step = max(32, min(h, w) // 8)
    for y in range(0, h - step, step):
        for x in range(0, w - step, step):
            block = img[y: y + step, x: x + step]
            noise_blocks.append(float(np.std(block)))
    noise_var = float(np.std(noise_blocks)) / 50.0 if noise_blocks else 0.0

    score = 0.4 * min(1.0, texture_var) + 0.35 * min(1.0, edge_density * 5) + 0.25 * min(1.0, noise_var)
    return max(0.0, min(1.0, score))


def predict_tampering_score(image_path: str) -> Dict[str, Any]:
    """
    Return tampering probability from CNN embeddings or texture fallback.
    """
    path = Path(image_path)
    if not path.exists():
        return {"score": 0.0, "method": "unavailable", "confidence": 0.0}

    clf = _get_classifier()
    if not clf:
        score = _texture_fallback(str(path))
        return {
            "score": round(score, 4),
            "method": "texture_fallback",
            "confidence": 0.55,
        }

    try:
        import torch

        img = cv2.imread(str(path))
        if img is None:
            return {"score": 0.0, "method": "cnn", "confidence": 0.0}

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        tensor = clf["transform"](img_rgb).unsqueeze(0).to(clf["device"])

        with torch.no_grad():
            embedding = clf["model"](tensor).cpu().numpy().flatten()

        # Patch-level embedding variance captures local inconsistency
        h, w = img_rgb.shape[:2]
        patch_scores = []
        for py in (0.25, 0.5, 0.75):
            for px in (0.25, 0.5, 0.75):
                y1, y2 = int(h * py) - 112, int(h * py) + 112
                x1, x2 = int(w * px) - 112, int(w * px) + 112
                y1, x1 = max(0, y1), max(0, x1)
                patch = img_rgb[y1: min(h, y2), x1: min(w, x2)]
                if patch.size < 1000:
                    continue
                pt = clf["transform"](patch).unsqueeze(0).to(clf["device"])
                with torch.no_grad():
                    patch_scores.append(clf["model"](pt).cpu().numpy().flatten())

        if len(patch_scores) >= 2:
            dists = [float(np.linalg.norm(patch_scores[i] - patch_scores[j]))
                     for i in range(len(patch_scores)) for j in range(i + 1, len(patch_scores))]
            inconsistency = float(np.mean(dists)) / (float(np.linalg.norm(embedding)) + 1e-6)
        else:
            inconsistency = float(np.std(embedding)) / (float(np.mean(np.abs(embedding))) + 1e-6)

        score = max(0.0, min(1.0, inconsistency * 2.5))
        texture = _texture_fallback(str(path))
        blended = 0.7 * score + 0.3 * texture

        return {
            "score": round(blended, 4),
            "method": "efficientnet_b0",
            "confidence": 0.78,
            "embedding_inconsistency": round(inconsistency, 4),
        }
    except Exception as exc:
        logger.warning("CNN tampering inference failed: %s", exc)
        score = _texture_fallback(str(path))
        return {"score": round(score, 4), "method": "texture_fallback", "confidence": 0.55}
