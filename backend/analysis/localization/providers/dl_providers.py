"""Optional DL segmentation providers — load weights when present, else defer to heuristic."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from backend.analysis.localization.contracts import SegmentationOutput
from backend.analysis.localization.providers.base import MODELS_ROOT, try_load_torch_weights
from backend.analysis.localization.providers.heuristic import HeuristicSegmentationProvider

logger = logging.getLogger("ai_forge.localization.dl")


class _DLProviderBase:
    """Shared pattern: attempt torch inference, fall back to heuristic."""

    name: str = "dl"
    weights_name: str = ""

    def __init__(self) -> None:
        self._fallback = HeuristicSegmentationProvider()
        self._weights = MODELS_ROOT / self.weights_name

    def is_available(self) -> bool:
        return try_load_torch_weights(self._weights)

    def _run_torch(self, image_path: str, output_dir: str) -> SegmentationOutput | None:
        try:
            import torch
            import cv2
            import numpy as np
            from backend.analysis.localization.providers.base import (
                build_output,
                load_bgr,
                normalize_map,
                save_segmentation_artifacts,
            )

            original = load_bgr(image_path)
            if original is None:
                return None

            # Generic checkpoint — expects dict with 'mask' head or full model state
            checkpoint = torch.load(str(self._weights), map_location="cpu", weights_only=False)
            model = checkpoint.get("model") if isinstance(checkpoint, dict) else None
            if model is None:
                return None

            model.eval()
            rgb = cv2.cvtColor(original, cv2.COLOR_BGR2RGB)
            tensor = torch.from_numpy(rgb).permute(2, 0, 1).float().unsqueeze(0) / 255.0
            with torch.no_grad():
                out = model(tensor)
                if isinstance(out, (tuple, list)):
                    out = out[0]
                heatmap = out.squeeze().cpu().numpy()
            if heatmap.ndim > 2:
                heatmap = heatmap[0]
            heatmap = normalize_map(heatmap)
            if heatmap.shape != original.shape[:2]:
                heatmap = cv2.resize(heatmap, (original.shape[1], original.shape[0]))
            binary = ((heatmap >= 0.5) * 255).astype(np.uint8)
            paths = save_segmentation_artifacts(Path(output_dir), self.name, heatmap, binary, original)
            logger.info("Generated: %s -> saved", self.name.upper())
            return build_output(
                self.name,
                heatmap,
                binary,
                float(heatmap.mean()),
                min(0.98, 0.5 + float(heatmap.mean()) * 0.5),
                f"{self.name} deep segmentation model.",
                paths,
            )
        except Exception as exc:
            logger.debug("%s torch inference unavailable: %s", self.name, exc)
            return None

    def segment(self, image_path: str, output_dir: str) -> SegmentationOutput:
        if self.is_available():
            result = self._run_torch(image_path, output_dir)
            if result is not None:
                return result
        out = self._fallback.segment(image_path, output_dir)
        out.provider = f"{self.name}_heuristic_fallback"
        out.explanation = f"{self.name} weights unavailable — {out.explanation}"
        return out


class TruForProvider(_DLProviderBase):
    name = "trufor"
    weights_name = "trufor.pth"


class MVSSProvider(_DLProviderBase):
    name = "mvss"
    weights_name = "mvss.pth"


class CATNetProvider(_DLProviderBase):
    name = "catnet"
    weights_name = "catnet.pth"


class PSCCProvider(_DLProviderBase):
    name = "pscc"
    weights_name = "pscc.pth"


class ManTraNetProvider(_DLProviderBase):
    name = "mantranet"
    weights_name = "mantranet.pth"
