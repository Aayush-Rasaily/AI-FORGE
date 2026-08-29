"""
Phase 6 AI-Guided Forensic Localization Engine — main orchestrator.

Runs segmentation, smart regions, OCR diff, signature/copy-move/video localization
in parallel where possible. Publishes artifacts to evidence vault.
"""

from __future__ import annotations

import json
import logging
import shutil
from concurrent.futures import as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

from backend.analysis.localization.copymove_localizer import localize_copy_move
from backend.analysis.localization.ocr_diff import build_ocr_diff_report
from backend.analysis.localization.providers.registry import get_active_provider
from backend.analysis.localization.region_explainability import attach_region_explanations
from backend.analysis.localization.signature_localizer import localize_signatures
from backend.analysis.localization.smart_regions import build_smart_regions
from backend.analysis.localization.video_localizer import build_video_localization
from backend.evidence.paths import get_analysis_artifacts_dir, get_evidence_artifacts_dir

logger = logging.getLogger("ai_forge.localization.engine")


def _publish_artifact(src: Path, evidence_id: str, filename: str) -> str:
    """Copy artifact to vault and analysis artifacts dir."""
    if not src.is_file():
        return ""
    src = src.resolve()
    vault = get_evidence_artifacts_dir(evidence_id) / filename
    analysis_art = get_analysis_artifacts_dir(evidence_id) / filename
    for dest in (vault, analysis_art):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest = dest.resolve()
        if dest == src:
            continue
        shutil.copy2(src, dest)
    return str(vault.resolve())


def _regions_from_segmentation(
    mask: np.ndarray,
    heatmap: np.ndarray,
    min_area: int = 350,
) -> List[Dict[str, Any]]:
    """Extract regions from AI segmentation mask."""
    binary = (mask >= 128).astype(np.uint8) * 255
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h, w = mask.shape[:2]
    regions = []
    for i, cnt in enumerate(contours):
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        x, y, bw, bh = cv2.boundingRect(cnt)
        roi = heatmap[y : y + bh, x : x + bw] if bh > 0 and bw > 0 else heatmap
        score = float(roi.mean()) if roi.size else 0.0
        epsilon = 0.01 * cv2.arcLength(cnt, True)
        poly = cv2.approxPolyDP(cnt, epsilon, True)
        polygon = [[int(p[0][0]), int(p[0][1])] for p in poly]
        # Always use canonical width/height keys — never w/h shorthand
        _canon_bbox = {"x": int(x), "y": int(y), "width": int(bw), "height": int(bh)}
        regions.append({
            "id": f"SEG-{i + 1:03d}",
            "index": i + 1,
            "bbox": _canon_bbox,
            "bounding_box": _canon_bbox,
            "coordinates": [int(x), int(y), int(x + bw), int(y + bh)],
            "polygon": polygon,
            "score": round(score, 4),
            "confidence": round(min(99.0, score * 100), 2),
            "type": "segmentation",
            "label": "AI-detected manipulation",
            "reason": "AI segmentation model flagged this region as manipulated.",
        })
    regions.sort(key=lambda r: r["score"], reverse=True)
    return regions[:30]


def run_phase6_localization(
    evidence_id: str,
    image_path: str,
    analysis_dir: Path,
    analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute Phase 6 localization pipeline.
    Returns enrichment dict merged into localization.json.
    """
    analysis_dir = Path(analysis_dir)
    loc_dir = analysis_dir / "phase6"
    loc_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir = get_analysis_artifacts_dir(evidence_id)

    result: Dict[str, Any] = {
        "phase": 6,
        "engine": "ai_guided_localization",
        "segmentation_provider": None,
        "artifacts": {},
    }

    # ── 1. AI Segmentation (parallel tasks below use worker pool) ──
    provider = get_active_provider()
    result["segmentation_provider"] = provider.name

    from backend.utils.worker_pool import get_worker_pool

    pool = get_worker_pool()
    futures = {
        pool.submit(provider.segment, image_path, str(loc_dir)): "segmentation",
        pool.submit(localize_copy_move, image_path, analysis_dir, analysis.get("copy_move")): "copymove",
        pool.submit(localize_signatures, image_path, analysis, loc_dir): "signature",
    }

    seg_output = None
    copymove_data: Dict[str, Any] = {}
    signature_data: Dict[str, Any] = {}

    for future in as_completed(futures):
        key = futures[future]
        try:
            out = future.result()
            if key == "segmentation":
                seg_output = out
            elif key == "copymove":
                copymove_data = out
            elif key == "signature":
                signature_data = out
        except Exception as exc:
            logger.warning("[%s] Phase6 %s failed: %s", evidence_id, key, exc)

    # Publish segmentation artifacts
    segmentation_layer: Optional[np.ndarray] = None
    if seg_output and seg_output.available:
        heatmap = seg_output.confidence_heatmap
        mask = seg_output.binary_mask
        segmentation_layer = heatmap.astype(np.float32)
        if heatmap.max() > 1:
            segmentation_layer = heatmap.astype(np.float32) / 255.0

        original = cv2.imread(image_path)
        if original is not None:
            h, w = original.shape[:2]
            if segmentation_layer.shape != (h, w):
                segmentation_layer = cv2.resize(segmentation_layer, (w, h))
            mask_resized = mask
            if mask.shape != (h, w):
                mask_resized = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)

            heat_colored = cv2.applyColorMap(
                (np.clip(segmentation_layer, 0, 1) * 255).astype(np.uint8),
                cv2.COLORMAP_JET,
            )
            overlay = cv2.addWeighted(original, 0.5, heat_colored, 0.5, 0)
            mask_path = artifacts_dir / "segmentation_mask.png"
            heat_path = artifacts_dir / "segmentation_heatmap.png"
            overlay_path = artifacts_dir / "segmentation_overlay.png"
            cv2.imwrite(str(mask_path), mask_resized)
            cv2.imwrite(str(heat_path), heat_colored)
            cv2.imwrite(str(overlay_path), overlay)

            for fname, path in (
                ("segmentation_mask", mask_path),
                ("segmentation_heatmap", heat_path),
                ("segmentation_overlay", overlay_path),
            ):
                published = _publish_artifact(path, evidence_id, f"{fname}.png")
                result["artifacts"][fname] = published
                logger.info("Generated: %s -> saved", fname.replace("_", " ").title())

        result["segmentation"] = {
            "provider": seg_output.provider,
            "score": seg_output.score,
            "confidence": seg_output.confidence,
            "explanation": seg_output.explanation,
            "available": True,
        }

    # ── 2. OCR diff report ──
    ocr_report = build_ocr_diff_report(analysis)
    result["text_modification_report"] = ocr_report
    ocr_report_path = loc_dir / "text_modification_report.json"
    with open(ocr_report_path, "w", encoding="utf-8") as f:
        json.dump(ocr_report, f, indent=2, default=str)
    _publish_artifact(ocr_report_path, evidence_id, "text_modification_report.json")

    # ── 3. Copy-move localization ──
    result["copy_move_localization"] = copymove_data
    if copymove_data.get("overlay_path"):
        _publish_artifact(Path(copymove_data["overlay_path"]), evidence_id, "copymove_localization.png")

    # ── 4. Signature localization ──
    result["signature_localization"] = signature_data
    if signature_data.get("overlay_path"):
        _publish_artifact(Path(signature_data["overlay_path"]), evidence_id, "signature_localization.png")

    # ── 5. Video timeline ──
    video_loc = build_video_localization(analysis)
    result["video_localization"] = video_loc

    # ── 6. Smart regions from segmentation + signature ──
    raw_regions: List[Dict[str, Any]] = []
    if seg_output and seg_output.available:
        heatmap_for_regions = (
            segmentation_layer if segmentation_layer is not None else seg_output.binary_mask
        )
        raw_regions.extend(_regions_from_segmentation(seg_output.binary_mask, heatmap_for_regions))
    raw_regions.extend(signature_data.get("regions") or [])

    layers = {"segmentation": segmentation_layer} if segmentation_layer is not None else {}
    smart = build_smart_regions(raw_regions, analysis, layers)
    smart = attach_region_explanations(smart, analysis)
    result["smart_regions"] = smart

    # Save phase6 bundle
    bundle_path = analysis_dir / "phase6_localization.json"
    with open(bundle_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    _publish_artifact(bundle_path, evidence_id, "phase6_localization.json")

    logger.info(
        "[%s] Phase6 complete | provider=%s regions=%d",
        evidence_id,
        result.get("segmentation_provider"),
        len(smart),
    )
    return result
