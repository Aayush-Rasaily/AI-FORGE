"""Dossier-driven visual localization for existing forensic findings."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

import cv2
import numpy as np

from backend.services.signature_service import update_forensic_dossier

_COLORS = {
    "CRITICAL": (0, 0, 255),
    "HIGH": (0, 165, 255),
    "MEDIUM": (0, 255, 255),
    "LOW": (255, 0, 0),
}


def _confidence(row: Mapping[str, Any]) -> Optional[float]:
    value = row.get("confidence")
    if value is None:
        value = row.get("confidence_pct")
    if value is None:
        value = row.get("score")
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if value > 1:
        value /= 100.0
    return round(max(0.0, min(1.0, value)), 4)


def _bbox(raw: Any) -> Optional[List[float]]:
    if isinstance(raw, dict):
        values = (
            raw.get("x", raw.get("left")),
            raw.get("y", raw.get("top")),
            raw.get("width", raw.get("w")),
            raw.get("height", raw.get("h")),
        )
    elif isinstance(raw, (list, tuple)) and len(raw) >= 4:
        if isinstance(raw[0], (list, tuple)):
            points = [point for point in raw if len(point) >= 2]
            if len(points) < 3:
                return None
            xs = [float(point[0]) for point in points]
            ys = [float(point[1]) for point in points]
            values = (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
        else:
            values = raw[:4]
    else:
        return None
    try:
        x, y, width, height = (float(value) for value in values)
    except (TypeError, ValueError):
        return None
    if width <= 0 or height <= 0:
        return None
    return [x, y, width, height]


def _polygon(
    row: Mapping[str, Any],
    bbox: List[int],
    image_width: int,
    image_height: int,
) -> List[List[int]]:
    raw = row.get("polygon") or row.get("points")
    if isinstance(raw, list):
        points = [
            [float(point[0]), float(point[1])]
            for point in raw
            if isinstance(point, (list, tuple)) and len(point) >= 2
        ]
        if len(points) >= 3:
            if all(
                abs(point[0]) <= 1.5 and abs(point[1]) <= 1.5
                for point in points
            ):
                points = [
                    [
                        int(round(point[0] * image_width)),
                        int(round(point[1] * image_height)),
                    ]
                    for point in points
                ]
            return [
                [int(round(point[0])), int(round(point[1]))]
                for point in points
            ]
    x, y, width, height = bbox
    return [[x, y], [x + width, y], [x + width, y + height], [x, y + height]]


def _iou(a: List[int], b: List[int]) -> float:
    ax1, ay1, aw, ah = a
    bx1, by1, bw, bh = b
    x1, y1 = max(ax1, bx1), max(ay1, by1)
    x2, y2 = min(ax1 + aw, bx1 + bw), min(ay1 + ah, by1 + bh)
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    union = aw * ah + bw * bh - intersection
    return intersection / union if union else 0.0


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")[:48] or "region"


def _source_rows(
    dossier: Mapping[str, Any],
    analysis: Optional[Mapping[str, Any]],
) -> Iterable[Tuple[Mapping[str, Any], Optional[int]]]:
    for section_name in (
        "document_tampering",
        "signature_analysis",
        "signature_verification",
    ):
        section = dossier.get(section_name)
        if not isinstance(section, Mapping):
            continue
        rows = section.get("findings") or section.get("signature_regions") or []
        if section_name == "signature_verification" and not rows:
            questioned = section.get("questioned_bbox")
            if questioned:
                rows = [{
                    "id": section.get("id") or "signature-verification",
                    "finding_id": section.get("id") or "signature-verification",
                    "type": "signature_verification",
                    "category": "signature",
                    "bbox": questioned,
                    "confidence": section.get("confidence"),
                    "severity": "high" if section.get("verdict") in {
                        "Forgery Suspected", "Different Writer",
                    } else "medium",
                    "human_summary": section.get("reason"),
                    "technical_reason": section.get("reason"),
                }]
        for row in rows:
            if isinstance(row, Mapping):
                yield row, row.get("page") or row.get("page_number") or 1

    for row in dossier.get("findings") or []:
        if isinstance(row, Mapping):
            yield row, row.get("page") or row.get("page_number") or 1

    localization = (analysis or {}).get("localization") or {}
    for row in localization.get("regions") or []:
        if isinstance(row, Mapping):
            yield row, row.get("page") or row.get("page_number") or 1

    for section_name in ("document_tampering", "signature_analysis"):
        section = (analysis or {}).get(section_name)
        if not isinstance(section, Mapping):
            continue
        rows = section.get("findings") or section.get("signature_regions") or []
        for row in rows:
            if isinstance(row, Mapping):
                yield row, row.get("page") or row.get("page_number") or 1


def _normalize_regions(
    dossier: Mapping[str, Any],
    analysis: Optional[Mapping[str, Any]],
    image_paths: Mapping[int, Path],
) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    for raw, page in _source_rows(dossier, analysis):
        try:
            page_number = int(page or 1)
        except (TypeError, ValueError):
            page_number = 1
        path = image_paths.get(page_number)
        image = cv2.imread(str(path), cv2.IMREAD_COLOR) if path else None
        if image is None:
            continue
        height, width = image.shape[:2]
        bbox = _bbox(raw.get("bbox") or raw.get("bounding_box") or raw.get("location"))
        confidence = _confidence(raw)
        if bbox is None or confidence is None:
            continue
        x, y, bw, bh = bbox
        if max(abs(x), abs(y), abs(bw), abs(bh)) <= 1.5:
            x = int(round(x * width))
            y = int(round(y * height))
            bw = int(round(bw * width))
            bh = int(round(bh * height))
        x = max(0, min(x, width - 1))
        y = max(0, min(y, height - 1))
        bw = min(bw, width - x)
        bh = min(bh, height - y)
        if bw <= 0 or bh <= 0:
            continue
        bbox = [int(round(x)), int(round(y)), int(round(bw)), int(round(bh))]
        x, y, bw, bh = bbox
        if bw <= 0 or bh <= 0:
            continue
        severity = str(raw.get("severity") or "LOW").upper()
        if severity not in _COLORS:
            severity = "LOW"
        item_id = str(raw.get("id") or raw.get("finding_id") or f"region-{len(candidates) + 1:03d}")
        category = str(raw.get("category") or raw.get("field_category") or raw.get("type") or "forensic")
        candidates.append({
            "id": item_id,
            "finding_id": str(raw.get("finding_id") or item_id),
            "category": category,
            "type": str(raw.get("type") or category),
            "severity": severity,
            "page": page_number,
            "bbox": bbox,
            "polygon": _polygon(raw, bbox, width, height),
            "center": [round(x + bw / 2, 2), round(y + bh / 2, 2)],
            "confidence": confidence,
            "human_summary": str(
                raw.get("human_summary")
                or raw.get("plain_english_explanation")
                or raw.get("description")
                or raw.get("reason")
                or "Localized forensic observation."
            ),
            "technical_reason": str(
                raw.get("technical_reason")
                or raw.get("technical_explanation")
                or raw.get("reason")
                or raw.get("description")
                or "Detector output was localized to this region."
            ),
            "overlay_color": _COLORS[severity],
            "_path": path,
        })

    candidates.sort(key=lambda row: row["confidence"], reverse=True)
    merged: List[Dict[str, Any]] = []
    for candidate in candidates:
        duplicate = next(
            (
                item for item in merged
                if item["page"] == candidate["page"]
                and _iou(item["bbox"], candidate["bbox"]) >= 0.3
            ),
            None,
        )
        if duplicate is None:
            merged.append(candidate)
        else:
            dx, dy, dw, dh = duplicate["bbox"]
            cx, cy, cw, ch = candidate["bbox"]
            union_x = min(dx, cx)
            union_y = min(dy, cy)
            union_x2 = max(dx + dw, cx + cw)
            union_y2 = max(dy + dh, cy + ch)
            union_bbox = [union_x, union_y, union_x2 - union_x, union_y2 - union_y]
            duplicate["bbox"] = union_bbox
            duplicate["polygon"] = _polygon(
                {}, union_bbox, union_x2, union_y2
            )
            duplicate["center"] = [
                round(union_x + union_bbox[2] / 2, 2),
                round(union_y + union_bbox[3] / 2, 2),
            ]
            if candidate["confidence"] > duplicate["confidence"]:
                duplicate.update({
                    key: candidate[key]
                    for key in (
                        "id", "finding_id", "category", "type", "severity",
                        "confidence", "human_summary", "technical_reason",
                        "overlay_color",
                    )
                })
                duplicate["bbox"] = union_bbox
                duplicate["polygon"] = _polygon(
                    {}, union_bbox, union_x2, union_y2
                )
                duplicate["center"] = [
                    round(union_x + union_bbox[2] / 2, 2),
                    round(union_y + union_bbox[3] / 2, 2),
                ]
    return merged


def _render_page(
    page_regions: List[Dict[str, Any]],
    image_path: Path,
    output_dir: Path,
) -> Dict[str, str]:
    original = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if original is None:
        return {}
    height, width = original.shape[:2]
    mask = np.zeros((height, width), dtype=np.uint8)
    heat = np.zeros((height, width), dtype=np.float32)
    line_overlay = original.copy()
    combined = original.copy()
    for index, region in enumerate(page_regions, start=1):
        polygon = np.array(region["polygon"], dtype=np.int32)
        cv2.fillPoly(mask, [polygon], 255)
        cv2.fillPoly(heat, [polygon], float(region["confidence"]))
        color = region["overlay_color"]
        x, y, bw, bh = region["bbox"]
        cv2.rectangle(line_overlay, (x, y), (x + bw, y + bh), color, 2)
        cv2.fillPoly(combined, [polygon], color)
        cv2.rectangle(combined, (x, y), (x + bw, y + bh), color, 2)
        cv2.putText(
            line_overlay,
            f"{region['type']} ({region['severity']})",
            (x, max(16, y - 5)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            color,
            1,
            cv2.LINE_AA,
        )
        mask_name = f"mask_{index:03d}_{_safe_name(region['id'])}.png"
        region_mask = np.zeros_like(mask)
        cv2.fillPoly(region_mask, [polygon], 255)
        cv2.imwrite(str(output_dir / mask_name), region_mask)
        region["mask"] = mask_name
        region["heatmap_layer"] = "forensic_heatmap.png"
    combined = cv2.addWeighted(original, 0.65, combined, 0.35, 0)
    heatmap = cv2.applyColorMap((np.clip(heat, 0, 1) * 255).astype(np.uint8), cv2.COLORMAP_JET)
    paths = {
        "localization_overlay": "localization_overlay.png",
        "localization_mask": "localization_mask.png",
        "forensic_heatmap": "forensic_heatmap.png",
        "combined_overlay": "combined_overlay.png",
    }
    cv2.imwrite(str(output_dir / paths["localization_overlay"]), line_overlay)
    cv2.imwrite(str(output_dir / paths["localization_mask"]), mask)
    cv2.imwrite(str(output_dir / paths["forensic_heatmap"]), heatmap)
    cv2.imwrite(str(output_dir / paths["combined_overlay"]), combined)
    return paths


def build_professional_localization(
    evidence_id: str,
    analysis_dir: str | Path,
    *,
    image_paths: Mapping[int, str | Path],
    dossier: Optional[Dict[str, Any]] = None,
    analysis: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generate localized evidence artifacts from actual detector outputs."""
    analysis_dir = Path(analysis_dir)
    analysis_dir.mkdir(parents=True, exist_ok=True)
    if dossier is None:
        try:
            raw_dossier = json.loads((analysis_dir / "forensic_dossier.json").read_text(encoding="utf-8"))
            dossier = raw_dossier if isinstance(raw_dossier, dict) else {"findings": raw_dossier}
        except (OSError, json.JSONDecodeError):
            dossier = {}
    normalized_paths = {int(page): Path(path) for page, path in image_paths.items()}
    regions = _normalize_regions(dossier, analysis, normalized_paths)
    page_artifacts: Dict[str, Dict[str, str]] = {}
    for page in sorted({region["page"] for region in regions}):
        page_regions = [region for region in regions if region["page"] == page]
        page_dir = analysis_dir / "pages" / f"page_{page}"
        page_dir.mkdir(parents=True, exist_ok=True)
        paths = _render_page(page_regions, normalized_paths[page], page_dir)
        if paths:
            page_artifacts[str(page)] = {
                key: str(Path("pages") / f"page_{page}" / value)
                for key, value in paths.items()
            }
            for region in page_regions:
                if region.get("mask"):
                    region["mask"] = str(
                        Path("pages") / f"page_{page}" / region["mask"]
                    )
                region["heatmap_layer"] = str(
                    Path("pages") / f"page_{page}" / "forensic_heatmap.png"
                )

    root_paths: Dict[str, str] = {}
    if normalized_paths:
        first_page = min(normalized_paths)
        first_regions = [region for region in regions if region["page"] == first_page]
        root_paths = _render_page(first_regions, normalized_paths[first_page], analysis_dir)

    severity_counts = {level.lower(): sum(1 for r in regions if r["severity"] == level) for level in _COLORS}
    largest = max(regions, key=lambda r: r["bbox"][2] * r["bbox"][3], default=None)
    primary = max(regions, key=lambda r: r["confidence"], default=None)
    summary = {
        "total_regions": len(regions),
        **severity_counts,
        "largest_region": largest["type"] if largest else None,
        "primary_manipulation": primary["type"] if primary else None,
    }
    for region in regions:
        region.pop("_path", None)
        region["overlay_color"] = {
            "CRITICAL": "red",
            "HIGH": "orange",
            "MEDIUM": "yellow",
            "LOW": "blue",
        }[region["severity"]]

    output = {
        "schema_version": "1.0",
        "evidence_id": evidence_id,
        "region_count": len(regions),
        "regions": regions,
        "summary": summary,
        "page_artifacts": page_artifacts,
        "overlay_files": root_paths,
    }
    (analysis_dir / "evidence_localization.json").write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (analysis_dir / "localization_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    update_forensic_dossier(
        analysis_dir,
        {
            "regions": regions,
            "summary": summary,
            "overlay_files": root_paths,
            "page_artifacts": page_artifacts,
        },
        section="localized_regions",
    )
    try:
        dossier_path = analysis_dir / "forensic_dossier.json"
        persisted = json.loads(dossier_path.read_text(encoding="utf-8"))
        if not isinstance(persisted, dict):
            persisted = {}
        persisted["localized_regions"] = regions
        persisted["localization_summary"] = summary
        persisted["overlay_files"] = root_paths
        temporary = dossier_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(persisted, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temporary.replace(dossier_path)
    except (OSError, TypeError, ValueError) as exc:
        raise RuntimeError(f"Could not persist localization dossier: {exc}") from exc
    return output


__all__ = ["build_professional_localization"]
