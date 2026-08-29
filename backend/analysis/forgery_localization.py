"""
Forgery Localization Engine — fuse forensic artifacts into pixel-level masks.

Does NOT re-run heavy detectors when artifacts already exist.
Produces:
  localization_heatmap.png  — fused overlay
  forgery_mask.png          — binary / soft mask
  localization_diff.png     — difference-style view
  localization.json         — regions + explanations
"""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from backend.evidence.paths import find_evidence_file, get_analysis_dir, get_analysis_artifacts_dir
from backend.utils.artifact_paths import artifact_api_urls
try:
    from backend.ocr.ocr_comparison import analyze_ocr_inconsistencies
except ImportError:
    def analyze_ocr_inconsistencies(data): return []

logger = logging.getLogger("ai_forge.localization")

# Fusion weights for 10-detector pixel-level localization map
LOC_WEIGHTS = {
    "ela": 0.15,
    "noise": 0.12,
    "copy_move": 0.15,
    "frequency": 0.10,
    "wavelet": 0.10,
    "jpeg_block": 0.10,
    "gan": 0.08,
    "shadow": 0.07,
    "reflection": 0.07,
    "edge": 0.06,
    "segmentation": 0.0,
    "metadata": 0.0,
    "ocr": 0.0,
    "vit_attention": 0.0,
}

PIXEL_LEVEL_VERSION = 4


def _read_gray(path: Path, shape: Tuple[int, int]) -> Optional[np.ndarray]:
    if not path.is_file() or path.stat().st_size < 50:
        return None
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        color = cv2.imread(str(path))
        if color is None:
            return None
        img = cv2.cvtColor(color, cv2.COLOR_BGR2GRAY)
    h, w = shape
    if img.shape[:2] != (h, w):
        img = cv2.resize(img, (w, h), interpolation=cv2.INTER_LINEAR)
    return img.astype(np.float32) / 255.0


def _normalize(m: np.ndarray) -> np.ndarray:
    m = np.nan_to_num(m, nan=0.0, posinf=0.0, neginf=0.0)
    lo, hi = float(m.min()), float(m.max())
    if hi - lo < 1e-6:
        return np.zeros_like(m)
    return (m - lo) / (hi - lo)


def _overlay(original_bgr: np.ndarray, heat: np.ndarray, alpha: float = 0.45) -> np.ndarray:
    heat_u8 = (np.clip(heat, 0, 1) * 255).astype(np.uint8)
    colored = cv2.applyColorMap(heat_u8, cv2.COLORMAP_JET)
    return cv2.addWeighted(original_bgr, 1.0 - alpha, colored, alpha, 0)


def _spatial_quadrant(x: int, y: int, w: int, h: int, img_w: int, img_h: int) -> str:
    cx, cy = x + w / 2.0, y + h / 2.0
    vert = "Top" if cy < img_h / 2.0 else "Bottom"
    horiz = "Left" if cx < img_w / 2.0 else "Right"
    if abs(cx - img_w / 2.0) < img_w * 0.15 and abs(cy - img_h / 2.0) < img_h * 0.15:
        return "Center"
    return f"{vert} {horiz}"


def _regions_from_mask(
    mask: np.ndarray,
    fused: np.ndarray,
    *,
    min_area: int = 400,
) -> List[Dict[str, Any]]:
    """Extract pixel-level regions with polygon, bbox, quadrant location, and mask stats from fused map."""
    binary = (mask >= 0.42).astype(np.uint8) * 255
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    regions = []
    h, w = mask.shape[:2]
    for i, cnt in enumerate(contours):
        area = float(cv2.contourArea(cnt))
        if area < min_area:
            continue
        bx, by, bw, bh = cv2.boundingRect(cnt)
        roi = fused[by : by + bh, bx : bx + bw] if bh > 0 and bw > 0 else fused
        score = float(roi.mean()) if roi.size else 0.0

        epsilon = 0.01 * cv2.arcLength(cnt, True)
        poly = cv2.approxPolyDP(cnt, epsilon, True)
        polygon = [[int(p[0][0]), int(p[0][1])] for p in poly]
        if len(polygon) < 3:
            polygon = [
                [bx, by], [bx + bw, by], [bx + bw, by + bh], [bx, by + bh],
            ]

        region_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.drawContours(region_mask, [cnt], -1, 255, thickness=cv2.FILLED)
        pixel_count = int(np.count_nonzero(region_mask))
        mask_coverage = round(pixel_count / float(h * w), 6)

        roi_mask = region_mask[by : by + bh, bx : bx + bw] if bh > 0 and bw > 0 else region_mask
        ok, buf = cv2.imencode(".png", roi_mask)
        mask_b64 = base64.b64encode(buf).decode("ascii") if ok else ""

        quadrant = _spatial_quadrant(bx, by, bw, bh, w, h)

        regions.append({
            "id": f"region-{i + 1}",
            "index": i + 1,
            "location": quadrant,
            "quadrant": quadrant,
            "bbox": {"x": int(bx), "y": int(by), "w": int(bw), "h": int(bh)},
            "bounding_box": {"x": int(bx), "y": int(by), "width": int(bw), "height": int(bh)},
            "polygon": polygon,
            "normalized_polygon": [
                [round(px / w, 4), round(py / h, 4)] for px, py in polygon
            ],
            "mask": mask_b64,
            "mask_format": "png_base64_crop",
            "mask_pixel_count": pixel_count,
            "mask_coverage": mask_coverage,
            "area": round(area, 1),
            "score": round(score, 4),
            "normalized_bbox": {
                "x": round(bx / w, 4),
                "y": round(by / h, 4),
                "w": round(bw / w, 4),
                "h": round(bh / h, 4),
            },
            "reason": _reason_for_score(score),
        })
    regions.sort(key=lambda r: r["score"], reverse=True)
    return regions[:40]



def _build_ocr_layer(h: int, w: int, analysis: Dict[str, Any]) -> Optional[np.ndarray]:
    """Rasterize OCR mismatch / suspicious text boxes into a spatial layer."""
    layer = np.zeros((h, w), dtype=np.float32)
    count = 0
    sources = []
    for key in ("ocr", "text_layout", "font_consistency"):
        block = analysis.get(key) or {}
        if isinstance(block, dict):
            sources.append(block)

    def _rasterize_bbox(bbox: Any, weight: float) -> None:
        nonlocal count
        if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
            if isinstance(bbox[0], (list, tuple)):
                xs = [float(p[0]) for p in bbox[:4]]
                ys = [float(p[1]) for p in bbox[:4]]
                x, y = int(min(xs)), int(min(ys))
                bw = int(max(xs) - min(xs))
                bh = int(max(ys) - min(ys))
            else:
                x, y, bw, bh = map(int, map(float, bbox[:4]))
        elif isinstance(bbox, dict):
            x = int(float(bbox.get("x", bbox.get("left", 0))))
            y = int(float(bbox.get("y", bbox.get("top", 0))))
            bw = int(float(bbox.get("w", bbox.get("width", 0))))
            bh = int(float(bbox.get("h", bbox.get("height", 0))))
        else:
            return
        if max(x, y, bw, bh) <= 1.5:
            x, y, bw, bh = int(x * w), int(y * h), int(bw * w), int(bh * h)
        x2, y2 = min(w, x + bw), min(h, y + bh)
        x, y = max(0, x), max(0, y)
        if x2 > x and y2 > y:
            layer[y:y2, x:x2] = np.maximum(layer[y:y2, x:x2], weight)
            count += 1

    for block in sources:
        for item in block.get("mismatch_regions") or block.get("suspicious_words") or block.get("detections") or []:
            if not isinstance(item, dict):
                continue
            bbox = item.get("bbox") or item.get("box") or item.get("bounding_box")
            if bbox:
                conf = float(item.get("score") or item.get("confidence") or 0.65)
                _rasterize_bbox(bbox, min(1.0, conf))

    if count == 0:
        return None
    return _normalize(layer)


def _build_metadata_layer(
    h: int, w: int, analysis: Dict[str, Any], fused: np.ndarray,
) -> Optional[np.ndarray]:
    """Spatial metadata layer — artifact heatmap or elevated fused edges when metadata flags."""
    analysis_dir_hint = analysis.get("_analysis_dir")
    if analysis_dir_hint:
        for fname in ("metadata_heatmap.png", "metadata_forensics.png"):
            p = Path(analysis_dir_hint) / fname
            layer = _read_gray(p, (h, w))
            if layer is not None:
                return _normalize(layer)

    meta = analysis.get("metadata") or analysis.get("metadata_forensics") or {}
    signals = analysis.get("signals") or {}
    suspicious = bool(
        meta.get("suspicious")
        or meta.get("metadata_suspicious")
        or signals.get("metadata_suspicious")
    )
    if not suspicious:
        return None

    # Metadata has no raster — amplify high-response boundaries on fused map
    gray = (fused * 255).astype(np.uint8)
    edges = cv2.Canny(gray, 50, 150).astype(np.float32) / 255.0
    layer = _normalize(fused * 0.6 + edges * 0.4)
    return layer


def _technical_explanation(votes: Dict[str, bool], evidence: List[str], score: float) -> str:
    fired = [k for k, v in votes.items() if v]
    parts = [
        f"Pixel-level fusion score {score:.2f}.",
        f"Active detectors: {', '.join(fired) if fired else 'none above threshold'}.",
    ]
    for e in evidence[:4]:
        parts.append(e)
    return " ".join(parts)


def _plain_english_explanation(
    label: str, manipulation: str, votes: Dict[str, bool], confidence: float,
) -> str:
    fired = [k for k, v in votes.items() if v]
    if confidence >= 85:
        strength = "strong evidence suggests"
    elif confidence >= 65:
        strength = "there are probable indications that"
    else:
        strength = "there are possible signs that"
        
    det_map = {
        "ELA": "compression artifacts",
        "Wavelet": "frequency inconsistencies",
        "Copy Move": "cloned pixel regions",
        "Noise": "noise residual anomalies",
        "Metadata": "digital footprint inconsistencies",
        "OCR": "typographical alignment and font variations",
        "Deep Learning": "AI-detected synthetic patterns"
    }
    
    mapped_evidence = [det_map.get(k, "digital anomalies") for k in fired]
    evidence_str = ", ".join(mapped_evidence[:3]) if mapped_evidence else "multiple forensic artifacts"
    
    return (
        f"Forensic analysis of the '{label}' area indicates {manipulation.lower()}. "
        f"Specifically, {strength} the content was altered post-creation. "
        f"This conclusion is supported by the presence of {evidence_str}."
    )


def _reason_for_score(score: float) -> str:
    if score >= 0.7:
        return "Strong multi-layered localization — pixel variance indicates localized manipulation."
    if score >= 0.5:
        return "Elevated forensic signals localized to this specific region."
    return "Moderate forensic inconsistency detected here."


def _region_layer_score(layer: np.ndarray, bbox: Dict[str, int]) -> float:
    x  = int(bbox.get("x", 0))
    y  = int(bbox.get("y", 0))
    bw = int(bbox.get("w", bbox.get("width", 0)))
    bh = int(bbox.get("h", bbox.get("height", 0)))
    h, w = layer.shape[:2]
    x2, y2 = min(w, x + bw), min(h, y + bh)
    x, y = max(0, x), max(0, y)
    if x2 <= x or y2 <= y:
        return 0.0
    return float(layer[y:y2, x:x2].mean())


def _enrich_regions(
    regions: List[Dict[str, Any]],
    layers: Dict[str, np.ndarray],
    analysis: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Attach detector votes, evidence bullets, and confidence for Evidence Inspector."""
    detector_keys = [
        ("ela", "ELA"),
        ("wavelet", "Wavelet"),
        ("copy_move", "Copy Move"),
        ("noise", "Noise"),
        ("metadata", "Metadata"),
        ("ocr", "OCR"),
        ("vit_attention", "ViT Attention"),
        ("gradcam", "ViT Attention"),
        ("deepfake", "Deep Learning"),
    ]
    risk = analysis.get("risk_fusion") or analysis.get("risk") or {}
    ocr_flag = bool(analysis.get("ocr") or analysis.get("text_layout") or analysis.get("font_consistency"))
    meta_flag = bool(analysis.get("metadata") or analysis.get("exif") or risk.get("metadata_score"))

    enriched = []
    for i, reg in enumerate(regions):
        bbox = reg.get("bbox") or {"x": 0, "y": 0, "w": 0, "h": 0}
        votes = {}
        evidence = []
        for key, label in detector_keys:
            if key not in layers:
                votes[label] = False
                continue
            score = _region_layer_score(layers[key], bbox)
            fired = score >= 0.42
            votes[label] = fired
            if fired:
                evidence.append(f"{label} response elevated in this region ({score:.2f})")

        # Document / OCR / metadata heuristics
        rtype = str(reg.get("type") or "").lower()
        if ocr_flag or "ocr" in rtype or "font" in rtype or "date" in rtype or "number" in rtype:
            votes["OCR"] = True
            evidence.append("OCR / text layout signals differ from surrounding content")
        else:
            votes.setdefault("OCR", False)

        if meta_flag or "metadata" in rtype:
            votes["Metadata"] = True
            evidence.append("Metadata inconsistency relative to claimed creation timeline")
        else:
            votes.setdefault("Metadata", False)

        evidence = [e for e in evidence if e]
        if not evidence and reg.get("reason"):
            evidence.append(str(reg["reason"]))

        score = float(reg.get("score") or 0)
        conf = min(99.5, max(40.0, score * 100 + sum(1 for v in votes.values() if v) * 4.5))
        label = reg.get("label") or f"Region {i + 1}"
        manipulation = (
            reg.get("manipulation")
            or ("Edited text / amount" if any(t in rtype for t in ("number", "date", "font", "ocr")) else None)
            or ("Document anomaly" if rtype and rtype != "image_region" else "Localized pixel manipulation")
        )

        narrative = (
            f"The content at {label} appears modified.\n\n"
            f"Evidence:\n"
            + "".join(f"• {e}\n" for e in evidence[:8])
            + f"\nConclusion\n"
            + (
                "Very likely edited after original creation.\n"
                if conf >= 85
                else "Suspicious — recommend investigator review.\n"
                if conf >= 65
                else "Low-to-moderate anomaly; corroborate with additional modules.\n"
            )
            + f"\nConfidence\n{conf:.1f}%"
        )

        active_detectors = [lbl for lbl, fired in votes.items() if fired]
        if not active_detectors:
            active_detectors = ["Ensemble Localization"]

        # Always produce a canonical bbox dict — normalise whatever the region has
        from backend.utils.bbox_schema import normalize_bbox as _nb, bbox_to_xyxy as _bte  # local import
        raw_box = reg.get("bbox") or reg.get("bounding_box") or {}
        canon_box = _nb(raw_box)
        bx  = int(canon_box["x"])
        by  = int(canon_box["y"])
        bw  = int(canon_box["width"])
        bh  = int(canon_box["height"])
        coords_xyxy = _bte(canon_box)

        edit_type = "Text Modification"
        
        # High Precision Manipulation Types requested
        if "signature" in rtype:
            edit_type = "Pasted Signature"
        elif "stamp" in rtype:
            edit_type = "Pasted Stamp"
        elif "seal" in rtype:
            edit_type = "Pasted Seal"
        elif "logo" in rtype or (bw * bh < 0.08 * (bw * bh + 1) and "OCR" not in active_detectors and "metadata" not in rtype):
            edit_type = "Copied Logo"
        elif "currency" in rtype or "amount" in rtype:
            edit_type = "Edited Currency Values"
        elif "number" in rtype:
            edit_type = "Changed Numbers"
        elif "date" in rtype:
            edit_type = "Modified Dates"
        elif "OCR" in active_detectors or any(t in rtype for t in ("font", "text", "ocr", "overlay")):
            if "ELA" in active_detectors or "Noise" in active_detectors:
                edit_type = "Inserted Text"
            else:
                edit_type = "Replaced Text"
        elif "Copy Move" in active_detectors:
            edit_type = "Copied Content"
        elif "ELA" in active_detectors or "Noise" in active_detectors or "metadata" in rtype:
            edit_type = "Digitally Inserted Object"

        reason_str  = evidence[0] if evidence else f"Forensic inconsistency localized at {reg.get('location', 'region')}"
        severity_str = "Critical" if conf >= 75 else "High" if conf >= 55 else "Medium" if conf >= 40 else "Low"

        enriched.append({
            **reg,
            "finding_id": f"finding-{i + 1}",
            "region_id": i + 1,
            "id": reg.get("id") or f"region-{i + 1}",
            "index": i + 1,
            "type": edit_type.lower().replace(" ", "_"),
            "edit_type": edit_type,
            "page": int(reg.get("page") or reg.get("page_number") or 1),
            "label": label,
            "manipulation": manipulation,
            "detector_votes": votes,
            "detector": ", ".join(active_detectors),
            "detectors": active_detectors,
            "reason": reason_str,
            "severity": severity_str,
            "evidence": evidence[:10],
            "confidence": round(conf / 100.0, 4) if conf <= 100 else round(conf, 1),
            "confidence_pct": round(conf, 1),
            "investigation": narrative,
            "technical_explanation": _technical_explanation(votes, evidence, score),
            "plain_english_explanation": _plain_english_explanation(
                label, manipulation, votes, conf,
            ),
            # ── canonical bbox dict (never a raw list) ──────────────────────
            "bbox": canon_box,
            "bounding_box": canon_box,
            # ── xyxy list kept for IoU math & frontend pixel coordinates ─────
            "coordinates": coords_xyxy,
            "polygon": reg.get("polygon", []),
            "normalized_polygon": reg.get("normalized_polygon", []),
            "mask_pixel_count": reg.get("mask_pixel_count", 0),
            "mask_coverage": reg.get("mask_coverage", 0),
        })

    return _merge_overlapping_regions(enriched)


def _bbox_iou(box1: List[int], box2: List[int]) -> float:
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    inter = max(0, x2 - x1) * max(0, y2 - y1)
    if inter <= 0:
        return 0.0

    area1 = max(0, box1[2] - box1[0]) * max(0, box1[3] - box1[1])
    area2 = max(0, box2[2] - box2[0]) * max(0, box2[3] - box2[1])
    union = area1 + area2 - inter
    return inter / float(union) if union > 0 else 0.0


def _merge_overlapping_regions(items: List[Dict[str, Any]], iou_thresh: float = 0.30) -> List[Dict[str, Any]]:
    """Merge overlapping detector regions into single unified findings and filter low-confidence noise."""
    from backend.utils.bbox_schema import normalize_bbox, bbox_to_xyxy, attach_standard_bbox  # local import avoids circular

    if not items:
        return []

    valid = [item for item in items if (item.get("confidence_pct", 0) >= 40.0 or item.get("confidence", 0) >= 0.40)]
    if not valid:
        valid = items[:1]

    # Ensure every item has a canonical bbox dict before IoU comparison
    valid = [attach_standard_bbox(item) for item in valid]

    merged: List[Dict[str, Any]] = []
    used = [False] * len(valid)

    for i in range(len(valid)):
        if used[i]:
            continue
        base = dict(valid[i])
        used[i] = True

        b1_xyxy = base["coordinates"]  # guaranteed xyxy list from attach_standard_bbox

        for j in range(i + 1, len(valid)):
            if used[j]:
                continue
            curr = valid[j]
            b2_xyxy = curr["coordinates"]

            # IoU using xyxy lists
            ix1, iy1 = max(b1_xyxy[0], b2_xyxy[0]), max(b1_xyxy[1], b2_xyxy[1])
            ix2, iy2 = min(b1_xyxy[2], b2_xyxy[2]), min(b1_xyxy[3], b2_xyxy[3])
            inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
            if inter > 0:
                a1 = (b1_xyxy[2] - b1_xyxy[0]) * (b1_xyxy[3] - b1_xyxy[1])
                a2 = (b2_xyxy[2] - b2_xyxy[0]) * (b2_xyxy[3] - b2_xyxy[1])
                iou = inter / (a1 + a2 - inter) if (a1 + a2 - inter) > 0 else 0.0
            else:
                iou = 0.0

            if iou >= iou_thresh:
                used[j] = True
                nx1 = min(b1_xyxy[0], b2_xyxy[0])
                ny1 = min(b1_xyxy[1], b2_xyxy[1])
                nx2 = max(b1_xyxy[2], b2_xyxy[2])
                ny2 = max(b1_xyxy[3], b2_xyxy[3])

                # Always store canonical dict — never a raw list
                merged_canon = {"x": nx1, "y": ny1, "width": max(0.0, nx2 - nx1), "height": max(0.0, ny2 - ny1)}
                merged_xyxy  = [nx1, ny1, nx2, ny2]
                base["bbox"]         = merged_canon
                base["bounding_box"] = merged_canon
                base["coordinates"]  = merged_xyxy   # keep xyxy list for IoU bookkeeping
                b1_xyxy = merged_xyxy  # update for subsequent iterations

                dets = list(set(base.get("detectors", [])) | set(curr.get("detectors", [])))
                base["detectors"] = dets
                base["detector"]  = ", ".join(dets)

                c1 = base.get("confidence_pct", 50)
                c2 = curr.get("confidence_pct", 50)
                new_conf = min(99.5, max(c1, c2) + len(dets) * 3.0)
                base["confidence_pct"] = round(new_conf, 1)
                base["confidence"]     = round(new_conf / 100.0, 4)

                ev1 = base.get("evidence", [])
                ev2 = curr.get("evidence", [])
                base["evidence"] = list(dict.fromkeys(ev1 + ev2))

        merged.append(base)

    for idx, item in enumerate(merged, 1):
        # Final safety: guarantee canonical bbox
        canon = normalize_bbox(item.get("bbox") or item.get("bounding_box") or item.get("coordinates"))
        bx, by, bw, bh = canon.get("x", 0), canon.get("y", 0), canon.get("width", canon.get("w", 0)), canon.get("height", canon.get("h", 0))
        
        conf = float(item.get("confidence", item.get("confidence_pct", 50) / 100.0))
        severity = "Critical" if conf >= 0.75 else "High" if conf >= 0.55 else "Medium" if conf >= 0.40 else "Low"
        
        # Determine exact type and label if not provided by specific engines (like OCR)
        type_str = item.get("type") or "pixel_anomaly"
        label_str = item.get("label") or f"Region {idx}"
        reason_str = item.get("reason") or "Localized pixel variations indicate post-creation editing."
        
        # Build the exact requested Evidence Object
        item["id"] = item.get("id") or f"region_{idx:03d}"
        item["page"] = item.get("page", 1)
        item["type"] = type_str
        item["label"] = label_str
        item["bbox"] = [bx, by, bw, bh]  # Array format requested by user
        item["confidence"] = round(conf, 4)
        item["reason"] = reason_str
        item["severity"] = severity
        item["recommendation"] = item.get("recommendation", "Manual verification recommended.")
        
        # Cleanup legacy fields that clutter the JSON
        for k in ["confidence_pct", "coordinates", "bounding_box", "region_id", "finding_id", "index", "detectors"]:
            item.pop(k, None)

    return merged


def _investigation_panel(analysis: Dict[str, Any], regions: List[Dict], layers: Dict) -> Dict[str, Any]:
    faces = analysis.get("faces") or analysis.get("face_detections") or []
    objects = analysis.get("objects") or analysis.get("detections") or []
    text_blocks = analysis.get("ocr") or analysis.get("text_blocks") or {}
    if isinstance(text_blocks, dict):
        text_items = text_blocks.get("words") or text_blocks.get("blocks") or text_blocks.get("lines") or []
    else:
        text_items = text_blocks if isinstance(text_blocks, list) else []

    risk = analysis.get("risk_fusion") or {}
    forgery_prob = float(
        risk.get("manipulation_score")
        or risk.get("overall_fraud_risk")
        or analysis.get("risk_score")
        or 0
    )
    if forgery_prob <= 1:
        forgery_prob *= 100

    return {
        "detected_objects": len(objects) if isinstance(objects, list) else int(objects or 0),
        "detected_faces": len(faces) if isinstance(faces, list) else int(faces or 0),
        "detected_text_regions": len(text_items) if isinstance(text_items, list) else 0,
        "modified_areas": len(regions),
        "metadata_changes": bool(analysis.get("metadata") or risk.get("metadata_score")),
        "forgery_probability": round(forgery_prob, 1),
        "detector_confidence": round(float(risk.get("confidence") or analysis.get("confidence") or 75), 1),
        "layers_active": list(layers.keys()),
        "objects_sample": (objects[:8] if isinstance(objects, list) else []),
        "faces_sample": (faces[:8] if isinstance(faces, list) else []),
    }


def _detailed_investigation(
    analysis: Dict[str, Any],
    regions: List[Dict[str, Any]],
    layers: Dict[str, np.ndarray],
) -> str:
    if regions:
        top = regions[0]
        if top.get("investigation"):
            return top["investigation"]
    layer_list = ", ".join(layers.keys()) or "edge fallback"
    n = len(regions)
    risk = analysis.get("risk_fusion") or {}
    conf = float(risk.get("confidence") or analysis.get("confidence") or 75)
    if conf <= 1:
        conf *= 100
    verdict = analysis.get("verdict") or risk.get("verdict") or "Reviewed"
    return (
        f"Detailed Investigation\n\n"
        f"Fused forensic localization across {layer_list}. "
        f"{n} suspicious region(s) localized for investigator review.\n\n"
        f"Conclusion\n{verdict}\n\n"
        f"Confidence\n{conf:.1f}%"
    )


def _document_regions(analysis: Dict[str, Any], shape: Tuple[int, int]) -> List[Dict[str, Any]]:
    """Extract clickable OCR / layout anomaly boxes from cached analysis."""
    h, w = shape
    regions: List[Dict[str, Any]] = []
    sources = []
    for key in ("font_consistency", "spacing_analysis", "region_anomaly", "text_layout", "ocr"):
        block = analysis.get(key) or {}
        if isinstance(block, dict):
            sources.append(block)

    # OCR Comparison check
    ocr_data = analysis.get("ocr") or {}
    if isinstance(ocr_data, dict):
        ocr_findings = analyze_ocr_inconsistencies(ocr_data)
        if ocr_findings:
            sources.append({"regions": ocr_findings})

    # Also scan page findings from document analysis
    for page in analysis.get("pages") or []:
        if isinstance(page, dict):
            for finding in page.get("findings") or page.get("anomalies") or []:
                if isinstance(finding, dict):
                    sources.append({"anomalies": [finding]})

    type_map = {
        "amount": "number",
        "number": "number",
        "date": "date",
        "name": "name",
        "logo": "logo",
        "stamp": "stamp",
        "font": "font",
        "spacing": "spacing",
        "signature": "signature",
        "overlay": "overlayed_text",
        "hidden": "hidden_text",
        "ocr": "ocr_mismatch",
    }

    for block in sources:
        for item in block.get("suspicious_words") or block.get("anomalies") or block.get("regions") or []:
            if not isinstance(item, dict):
                continue
            bbox = item.get("bbox") or item.get("box") or item.get("bounding_box")
            if not bbox:
                continue
            if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
                x, y, bw, bh = map(float, bbox[:4])
            elif isinstance(bbox, dict):
                x = float(bbox.get("x", bbox.get("left", 0)))
                y = float(bbox.get("y", bbox.get("top", 0)))
                bw = float(bbox.get("w", bbox.get("width", 0)))
                bh = float(bbox.get("h", bbox.get("height", 0)))
            else:
                continue
            if max(x, y, bw, bh) <= 1.5:
                x, y, bw, bh = x * w, y * h, bw * w, bh * h
            raw_type = str(item.get("type") or item.get("category") or "document_anomaly").lower()
            mapped = type_map.get(raw_type, raw_type)
            regions.append({
                "id": f"doc-{len(regions) + 1}",
                "type": mapped,
                "label": item.get("text") or item.get("label") or mapped.replace("_", " ").title(),
                "bbox": {"x": int(x), "y": int(y), "w": int(bw), "h": int(bh)},
                "score": float(item.get("score") or item.get("confidence") or 0.55),
                "reason": item.get("reason") or item.get("explanation") or "Document forensic anomaly.",
                "manipulation": item.get("manipulation") or f"Edited {mapped.replace('_', ' ')}",
            })
    return regions[:50]


def _video_timeline(analysis: Dict[str, Any]) -> Dict[str, Any]:
    frames = analysis.get("frames") or analysis.get("keyframes") or []
    intervals = []
    for fr in frames:
        if not isinstance(fr, dict):
            continue
        signals = fr.get("signals") or {}
        risk = float(fr.get("risk") or signals.get("edge_density") or 0)
        # Heuristic: high edge density + low blur can indicate splice; normalize loosely
        if risk > 0.12 or float(signals.get("blur_score") or 999) < 40:
            ts = float(fr.get("timestamp") or 0)
            intervals.append({
                "timestamp": ts,
                "frame_number": fr.get("frame_number"),
                "frame_index": fr.get("frame_index"),
                "score": round(min(1.0, risk * 4), 3),
                "reason": "Keyframe forensic signals suggest possible manipulation interval.",
                "image": fr.get("image") or fr.get("path"),
            })
    return {
        "suspicious_intervals": intervals[:30],
        "frame_count": len(frames),
    }


def build_forgery_localization(
    evidence_id: str,
    *,
    image_path: Optional[Path] = None,
    analysis_dir: Optional[Path] = None,
    analysis: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    analysis_dir = Path(analysis_dir or get_analysis_dir(evidence_id, create=True))
    analysis_dir.mkdir(parents=True, exist_ok=True)
    analysis = analysis or {}

    # Load cached analysis if needed
    if not analysis:
        for name in ("analysis.json", "document_analysis.json", "video_analysis.json"):
            p = analysis_dir / name
            if p.is_file():
                try:
                    with open(p, encoding="utf-8") as f:
                        analysis = json.load(f)
                    break
                except (json.JSONDecodeError, OSError):
                    pass

    path = Path(image_path) if image_path else find_evidence_file(evidence_id)
    original = None
    if path and Path(path).is_file():
        original = cv2.imread(str(path))

    # Document / video without raster — still emit region metadata
    media_hint = str(analysis.get("media_type") or analysis.get("type") or "")
    if original is None:
        # Try page preview / keyframe
        for candidate in (
            analysis_dir / "page_0.png",
            analysis_dir / "preview.jpg",
            analysis_dir / "_working.jpg",
        ):
            if candidate.is_file():
                original = cv2.imread(str(candidate))
                if original is not None:
                    break

    result: Dict[str, Any] = {
        "evidence_id": evidence_id,
        "success": True,
        "views": {},
        "regions": [],
        "video_timeline": {},
        "explanation": "",
        "weights": LOC_WEIGHTS,
    }

    if original is None:
        # Pure metadata localization for documents without preview
        regions = _enrich_regions(_document_regions(analysis, (1000, 1000)), {}, analysis)
        result["regions"] = regions
        result["video_timeline"] = _video_timeline(analysis)
        result["investigation_panel"] = _investigation_panel(analysis, regions, {})
        result["detailed_investigation"] = _detailed_investigation(analysis, regions, {})
        result["explanation"] = result["detailed_investigation"]
        _save_json(analysis_dir / "localization.json", result)
        return result

    h, w = original.shape[:2]
    analysis["_analysis_dir"] = str(analysis_dir)

    # Phase 6 — AI-guided segmentation + smart regions
    phase6: Dict[str, Any] = {}
    try:
        from backend.analysis.localization.engine import run_phase6_localization

        evidence_file = find_evidence_file(evidence_id)
        img_path = str(evidence_file) if evidence_file else str(analysis_dir / "_working.jpg")
        if Path(img_path).is_file():
            phase6 = run_phase6_localization(evidence_id, img_path, analysis_dir, analysis)
    except Exception as exc:
        logger.warning("phase6_localization_failed | %s | %s", evidence_id, exc)

    layers = {}
    for key, fname in (
        ("ela", "ela.png"),
        ("wavelet", "wavelet.png"),
        ("copy_move", "copymove.png"),
        ("noise", "noise.png"),
        ("deepfake", "face_forensics_heatmap.jpg"),
    ):
        candidates = [analysis_dir / fname]
        if key == "copy_move":
            candidates.append(analysis_dir / "copy_move.png")
        candidates += list(analysis_dir.glob(f"*{key}*.png")) + list(analysis_dir.glob(f"*{key}*.jpg"))
        if key == "copy_move":
            candidates += list(analysis_dir.glob("*copymove*"))
        layer = None
        for c in candidates:
            layer = _read_gray(c, (h, w))
            if layer is not None:
                break
        if layer is not None:
            layers[key] = _normalize(layer)

    # Phase 6 AI segmentation layer
    if (phase6.get("segmentation") or {}).get("available"):
        for seg_heat in (
            analysis_dir / "artifacts" / "segmentation_heatmap.png",
            get_analysis_artifacts_dir(evidence_id, create=False) / "segmentation_heatmap.png",
        ):
            layer = _read_gray(seg_heat, (h, w))
            if layer is not None:
                layers["segmentation"] = _normalize(layer)
                break

    # ViT / Grad-CAM attention maps
    explain_dir = analysis_dir / "explainability"
    if explain_dir.is_dir():
        for img in list(explain_dir.glob("*.png")) + list(explain_dir.glob("*.jpg")):
            layer = _read_gray(img, (h, w))
            if layer is not None:
                layers["vit_attention"] = _normalize(layer)
                break
    for cand in (analysis_dir / "attention_heatmap.png", analysis_dir / "gradcam.png"):
        if "vit_attention" in layers:
            break
        layer = _read_gray(cand, (h, w))
        if layer is not None:
            layers["vit_attention"] = _normalize(layer)

    # Preliminary fuse for metadata spatial prior
    pre_fused = np.zeros((h, w), dtype=np.float32)
    pre_w = 0.0
    for key, weight in LOC_WEIGHTS.items():
        if key in layers and key not in ("metadata", "ocr"):
            pre_fused += layers[key] * weight
            pre_w += weight
    if pre_w > 0:
        pre_fused /= pre_w
    else:
        gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
        pre_fused = _normalize(cv2.Laplacian(gray, cv2.CV_32F))

    ocr_layer = _build_ocr_layer(h, w, analysis)
    if ocr_layer is not None:
        layers["ocr"] = ocr_layer
    meta_layer = _build_metadata_layer(h, w, analysis, pre_fused)
    if meta_layer is not None:
        layers["metadata"] = meta_layer

    fused = np.zeros((h, w), dtype=np.float32)
    used_w = 0.0
    for key, weight in LOC_WEIGHTS.items():
        if key in layers:
            fused += layers[key] * weight
            used_w += weight
    if used_w > 0:
        fused /= used_w
    else:
        fused = pre_fused

    fused = cv2.GaussianBlur(fused, (0, 0), 2.0)
    fused = _normalize(fused)

    mask_binary = (fused >= 0.42).astype(np.uint8)
    mask = mask_binary.astype(np.float32)
    mask_soft = np.clip((fused - 0.25) / 0.55, 0, 1)

    heatmap = _overlay(original, fused)
    mask_vis = (mask_soft * 255).astype(np.uint8)
    mask_color = cv2.applyColorMap(mask_vis, cv2.COLORMAP_HOT)
    mask_binary_img = (mask_binary * 255).astype(np.uint8)
    highlighted = original.copy()
    highlighted[mask > 0.5] = (
        highlighted[mask > 0.5] * 0.35 + np.array([0, 0, 255]) * 0.65
    ).astype(np.uint8)
    diff = _overlay(original, np.clip(fused * 1.4, 0, 1), alpha=0.55)

    # Attention map visualization
    attention_map = original.copy()
    if "vit_attention" in layers:
        attention_map = _overlay(original, layers["vit_attention"], alpha=0.55)
    elif fused.max() > 0:
        attention_map = _overlay(original, fused * 0.85, alpha=0.45)

    heat_path = analysis_dir / "localization_heatmap.png"
    mask_path = analysis_dir / "forgery_mask.png"
    mask_bin_path = analysis_dir / "forgery_mask_binary.png"
    highlight_path = analysis_dir / "localization_highlight.png"
    diff_path = analysis_dir / "localization_diff.png"
    attention_path = analysis_dir / "localization_attention.png"
    polygon_path = analysis_dir / "localization_polygons.png"
    annotated_path = analysis_dir / "localization_annotated.png"
    alias_heat = analysis_dir / "heatmap.png"

    cv2.imwrite(str(heat_path), heatmap)
    cv2.imwrite(str(mask_path), mask_color)
    cv2.imwrite(str(mask_bin_path), mask_binary_img)
    cv2.imwrite(str(highlight_path), highlighted)
    cv2.imwrite(str(diff_path), diff)
    cv2.imwrite(str(attention_path), attention_map)
    try:
        cv2.imwrite(str(alias_heat), heatmap)
    except OSError:
        pass

    regions = _regions_from_mask(fused, fused)

    # Polygon + bounding box overlay
    poly_vis = original.copy()
    boxed = original.copy()
    for reg in regions[:20]:
        b = reg["bbox"]
        poly_pts = np.array(reg.get("polygon") or [], dtype=np.int32)
        if len(poly_pts) >= 3:
            cv2.polylines(poly_vis, [poly_pts], True, (0, 255, 255), 2)
            overlay = poly_vis.copy()
            cv2.fillPoly(overlay, [poly_pts], (0, 255, 255))
            cv2.addWeighted(overlay, 0.25, poly_vis, 0.75, 0, poly_vis)
        cv2.rectangle(boxed, (b["x"], b["y"]), (b["x"] + b["w"], b["y"] + b["h"]), (0, 255, 255), 2)
        label = f"R{reg.get('index', '')}"
        cv2.putText(
            boxed, label, (b["x"], max(14, b["y"] - 4)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA,
        )

    doc_regions = _document_regions(analysis, (h, w))
    # Colored boxes by document anomaly type
    type_colors = {
        "signature": (255, 128, 0),
        "stamp": (0, 165, 255),
        "logo": (255, 0, 255),
        "date": (0, 255, 128),
        "number": (128, 255, 0),
        "font": (255, 255, 0),
        "layout": (180, 105, 255),
    }
    for reg in doc_regions:
        b = reg["bbox"]
        color = type_colors.get(str(reg.get("type", "")).lower(), (0, 200, 255))
        cv2.rectangle(
            boxed,
            (b["x"], b["y"]),
            (b["x"] + b["w"], b["y"] + b["h"]),
            color,
            2,
        )
        label = str(reg.get("label") or reg.get("type") or "")[:24]
        if label:
            cv2.putText(
                boxed,
                label,
                (b["x"], max(12, b["y"] - 4)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                color,
                1,
                cv2.LINE_AA,
            )
    if doc_regions:
        regions = regions + doc_regions

    # Merge Phase 6 smart regions (dedupe by bbox proximity)
    for sreg in phase6.get("smart_regions") or []:
        regions.append(sreg)

    cv2.imwrite(str(polygon_path), poly_vis)
    cv2.imwrite(str(annotated_path), boxed)

    regions = _enrich_regions(regions, layers, analysis)
    regions = attach_region_explanations_safe(regions, analysis)
    
    # 9. Fallback if no reliable localization exists
    risk_fusion = analysis.get("risk_fusion") or analysis.get("risk") or {}
    forgery_prob = float(risk_fusion.get("manipulation_score") or risk_fusion.get("overall_fraud_risk") or analysis.get("risk_score") or 0)
    if forgery_prob <= 1:
        forgery_prob *= 100
        
    if not regions and forgery_prob > 60:
        regions.append({
            "id": "region_fallback_001",
            "page": 1,
            "type": "unlocalized_anomaly",
            "label": "Unlocalized Manipulation",
            "bbox": [0, 0, w, h],
            "confidence": round(forgery_prob / 100.0, 2),
            "reason": "Manipulation detected, but exact edited region could not be localized with sufficient confidence.",
            "severity": "High",
            "recommendation": "Manual verification across entire document."
        })
        
    investigation_panel = _investigation_panel(analysis, regions, layers)
    detailed = _detailed_investigation(analysis, regions, layers)

    boxed_path = analysis_dir / "localization_regions.png"
    cv2.imwrite(str(boxed_path), boxed)

    urls = artifact_api_urls(evidence_id)
    loc_base = f"/api/localization/{evidence_id}/file"

    result.update({
        "pixel_level_version": PIXEL_LEVEL_VERSION,
        "views": {
            "original": f"/api/localization/{evidence_id}/original",
            "heatmap": f"{loc_base}/localization_heatmap.png",
            "forgery_mask": f"{loc_base}/forgery_mask.png",
            "mask_binary": f"{loc_base}/forgery_mask_binary.png",
            "highlighted": f"{loc_base}/localization_highlight.png",
            "difference": f"{loc_base}/localization_diff.png",
            "regions": f"{loc_base}/localization_regions.png",
            "bounding_boxes": f"{loc_base}/localization_annotated.png",
            "polygons": f"{loc_base}/localization_polygons.png",
            "annotated": f"{loc_base}/localization_annotated.png",
            "attention": f"{loc_base}/localization_attention.png",
            "segmentation_mask": urls.get("segmentation_mask"),
            "segmentation_heatmap": urls.get("segmentation_heatmap"),
            "segmentation_overlay": urls.get("segmentation_overlay"),
            "copymove_localization": urls.get("copymove_localization"),
            "signature_localization": urls.get("signature_localization"),
            "ela": urls.get("ela"),
            "wavelet": urls.get("wavelet"),
            "copy_move": urls.get("copy_move"),
            "noise": urls.get("noise"),
        },
        "files": {
            "heatmap": str(heat_path),
            "mask": str(mask_path),
            "mask_binary": str(mask_bin_path),
            "highlight": str(highlight_path),
            "difference": str(diff_path),
            "regions": str(boxed_path),
            "bounding_boxes": str(annotated_path),
            "polygons": str(polygon_path),
            "annotated": str(annotated_path),
            "attention": str(attention_path),
        },
        "regions": regions,
        "video_timeline": phase6.get("video_localization") or _video_timeline(analysis),
        "layers_used": list(layers.keys()),
        "coverage": round(float(mask.mean()), 4),
        "explanation": detailed,
        "detailed_investigation": detailed,
        "investigation_panel": investigation_panel,
        "phase6": phase6,
        "text_modification_report": phase6.get("text_modification_report"),
        "copy_move_localization": phase6.get("copy_move_localization"),
        "signature_localization": phase6.get("signature_localization"),
        "video_localization": phase6.get("video_localization") or _video_timeline(analysis),
        "segmentation_provider": phase6.get("segmentation_provider"),
    })

    _save_json(analysis_dir / "localization.json", result)
    logger.info(
        "localization_complete | evidence=%s layers=%s regions=%s",
        evidence_id,
        list(layers.keys()),
        len(regions),
    )
    return result


def load_localization(evidence_id: str) -> Optional[Dict[str, Any]]:
    path = get_analysis_dir(evidence_id, create=False) / "localization.json"
    if not path.is_file():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def ensure_localization(evidence_id: str, analysis: Optional[Dict] = None) -> Dict[str, Any]:
    existing = load_localization(evidence_id)
    if existing and (existing.get("files") or existing.get("regions") is not None):
        version_ok = int(existing.get("pixel_level_version") or 0) >= PIXEL_LEVEL_VERSION
        has_polygons = bool(
            (existing.get("regions") or [{}])[0].get("polygon")
            if existing.get("regions")
            else False
        )
        heat = get_analysis_dir(evidence_id, create=False) / "localization_heatmap.png"
        if version_ok and has_polygons and (heat.is_file() or existing.get("regions")):
            return existing
    return build_forgery_localization(evidence_id, analysis=analysis)


def attach_region_explanations_safe(
    regions: List[Dict[str, Any]],
    analysis: Dict[str, Any],
) -> List[Dict[str, Any]]:
    try:
        from backend.analysis.localization.region_explainability import attach_region_explanations
        return attach_region_explanations(regions, analysis)
    except Exception as exc:
        logger.debug("region_explainability skipped: %s", exc)
        return regions


def _save_json(path: Path, data: Dict[str, Any]) -> None:
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    if path.exists():
        path.unlink(missing_ok=True)
    tmp.replace(path)
