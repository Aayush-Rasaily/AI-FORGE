"""
Shared lazy-loaded ML backbones — GPU when available, CPU fallback.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np

from backend.utils.hardware import get_torch_device
from backend.utils.inference_engine import (
    get_onnx_session_for,
    onnx_embed,
    optimize_torch_model,
    torch_infer,
)

logger = logging.getLogger("ai_forge.ml_models")

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


def _weight_norm(weights) -> tuple:
    meta = getattr(weights, "meta", None) or {}
    mean = meta.get("mean", IMAGENET_MEAN)
    std = meta.get("std", IMAGENET_STD)
    return mean, std


def _load_rgb_image(image_path: str, max_side: int = 1024) -> np.ndarray:
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"Cannot read image: {image_path}")
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    h, w = rgb.shape[:2]
    if max(h, w) > max_side:
        scale = max_side / max(h, w)
        rgb = cv2.resize(rgb, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return rgb


@lru_cache(maxsize=1)
def get_efficientnet_bundle() -> Dict[str, Any]:
    try:
        import torch
        import torchvision.transforms as T
        from torchvision.models import EfficientNet_B0_Weights, efficientnet_b0

        device = torch.device(get_torch_device())
        weights = EfficientNet_B0_Weights.IMAGENET1K_V1
        model = efficientnet_b0(weights=weights)
        model.classifier = torch.nn.Identity()
        model = optimize_torch_model(model, device)
        mean, std = _weight_norm(weights)
        transform = T.Compose([
            T.ToPILImage(),
            T.Resize((224, 224)),
            T.ToTensor(),
            T.Normalize(mean=mean, std=std),
        ])
        return {"model": model, "transform": transform, "device": device, "name": "efficientnet_b0"}
    except Exception as exc:
        logger.warning("EfficientNet unavailable: %s", exc)
        return {}


@lru_cache(maxsize=1)
def get_vit_bundle() -> Dict[str, Any]:
    try:
        import torch
        import torchvision.transforms as T
        from torchvision.models import ViT_B_16_Weights, vit_b_16

        device = torch.device(get_torch_device())
        weights = ViT_B_16_Weights.IMAGENET1K_V1
        model = vit_b_16(weights=weights)
        model.heads = torch.nn.Identity()
        model = optimize_torch_model(model, device)
        mean, std = _weight_norm(weights)
        transform = T.Compose([
            T.ToPILImage(),
            T.Resize((224, 224)),
            T.ToTensor(),
            T.Normalize(mean=mean, std=std),
        ])
        return {"model": model, "transform": transform, "device": device, "name": "vit_b_16"}
    except Exception as exc:
        logger.warning("ViT unavailable: %s", exc)
        return {}


@lru_cache(maxsize=1)
def get_clip_bundle() -> Dict[str, Any]:
    try:
        import torch
        from transformers import CLIPModel, CLIPProcessor

        device = torch.device(get_torch_device())
        model_name = "openai/clip-vit-base-patch32"
        processor = CLIPProcessor.from_pretrained(model_name)
        model = CLIPModel.from_pretrained(model_name).eval().to(device)
        model = optimize_torch_model(model, device)
        return {
            "model": model,
            "processor": processor,
            "device": device,
            "name": "clip_vit_base_patch32",
        }
    except Exception as exc:
        logger.warning("CLIP unavailable: %s", exc)
        return {}


@lru_cache(maxsize=1)
def get_xception_bundle() -> Dict[str, Any]:
    try:
        import torch
        import torchvision.transforms as T
        import timm

        device = torch.device(get_torch_device())
        model = timm.create_model("xception", pretrained=True, num_classes=0)
        model = optimize_torch_model(model, device)
        transform = T.Compose([
            T.ToPILImage(),
            T.Resize((299, 299)),
            T.ToTensor(),
            T.Normalize(mean=(0.5, 0.5, 0.5), std=(0.5, 0.5, 0.5)),
        ])
        return {"model": model, "transform": transform, "device": device, "name": "xception"}
    except Exception as exc:
        logger.warning("Xception unavailable: %s", exc)
        return {}


def embed_image(bundle: Dict[str, Any], rgb: np.ndarray) -> Optional[np.ndarray]:
    if not bundle:
        return None
    name = bundle.get("name", "")
    try:
        import torch

        onnx_sess = get_onnx_session_for(name)
        tensor = bundle["transform"](rgb).unsqueeze(0)
        if onnx_sess is not None:
            inp_name = onnx_sess.get_inputs()[0].name
            arr = tensor.numpy()
            return onnx_embed(onnx_sess, inp_name, arr)

        device = bundle["device"]
        tensor = tensor.to(device)
        out = torch_infer(bundle["model"], tensor, device)
        return out.float().cpu().numpy().flatten()
    except Exception as exc:
        logger.warning("Embedding failed (%s): %s", bundle.get("name"), exc)
        return None


def patch_embedding_variance(bundle: Dict[str, Any], rgb: np.ndarray) -> float:
    """Patch-level embedding inconsistency — higher for synthetic/edited regions."""
    h, w = rgb.shape[:2]
    embeddings = []
    for py in (0.2, 0.5, 0.8):
        for px in (0.2, 0.5, 0.8):
            y1 = max(0, int(h * py) - 112)
            x1 = max(0, int(w * px) - 112)
            patch = rgb[y1: min(h, y1 + 224), x1: min(w, x1 + 224)]
            if patch.size < 2000:
                continue
            emb = embed_image(bundle, patch)
            if emb is not None:
                embeddings.append(emb)

    if len(embeddings) < 2:
        full = embed_image(bundle, rgb)
        if full is None:
            return 0.0
        return float(np.std(full) / (np.mean(np.abs(full)) + 1e-6))

    dists = [
        float(np.linalg.norm(embeddings[i] - embeddings[j]))
        for i in range(len(embeddings))
        for j in range(i + 1, len(embeddings))
    ]
    base = embed_image(bundle, rgb)
    norm = float(np.linalg.norm(base)) if base is not None else 1.0
    return float(np.mean(dists) / (norm + 1e-6))
