"""
bbox_schema.py — Universal Bounding-Box Schema Normalizer
==========================================================
Single source-of-truth for all bbox/coordinate formats used in AI-FORGE.

Standard canonical format
--------------------------
{
    "x":      int | float,
    "y":      int | float,
    "width":  int | float,
    "height": int | float
}

Universal localization result schema
-------------------------------------
{
    "bbox":       {"x": ..., "y": ..., "width": ..., "height": ...},
    "polygon":    [[x,y], ...],
    "page":       1,
    "confidence": 0.96,
    "severity":   "High"
}

Also produced:
    "coordinates": [x, y, x2, y2]  — xyxy list used by IoU math
    "polygon":     [[x,y], ...]     — optional polygon mask

Supported input formats (all automatically converted)
------------------------------------------------------
- Dict {x,y,w,h}  /  {x,y,width,height}  /  {left,top,right,bottom}
- List [x, y, w, h]                       (xywh)
- List [x1, y1, x2, y2]                   (xyxy — x2>x1+1 and y2>y1+1 heuristic)
- List [[x1,y1],[x2,y2]]                   (two-point form)
- List [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]  (quad polygon)
- None / empty / 0-size fallback to {"x":0,"y":0,"width":0,"height":0}
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def normalize_bbox(raw: Any) -> Dict[str, float]:
    """
    Convert *any* bbox representation into the canonical dict.

    Returns
    -------
    {"x": float, "y": float, "width": float, "height": float}

    Never raises; worst case returns a zero box.
    """
    try:
        return _normalize(raw)
    except Exception:
        return _zero()


def safe_bbox_from_list(lst: Any) -> Dict[str, float]:
    """
    Safely convert a raw list [x,y,w,h] or [x1,y1,x2,y2] into canonical dict.
    Alias for normalize_bbox — never raises.
    """
    return normalize_bbox(lst)


def bbox_to_xyxy(bbox: Dict[str, float]) -> List[float]:
    """Canonical dict → [x, y, x2, y2] (xyxy)."""
    x = float(bbox.get("x") or bbox.get("left") or 0)
    y = float(bbox.get("y") or bbox.get("top") or 0)
    w = float(bbox.get("width") or bbox.get("w") or 0)
    h = float(bbox.get("height") or bbox.get("h") or 0)
    return [x, y, x + w, y + h]


def xyxy_to_bbox(xyxy: Sequence[float]) -> Dict[str, float]:
    """[x1, y1, x2, y2] → canonical dict."""
    x1, y1, x2, y2 = (float(v) for v in xyxy[:4])
    return {"x": x1, "y": y1, "width": max(0.0, x2 - x1), "height": max(0.0, y2 - y1)}


def compat_bbox(raw: Any) -> Dict[str, float]:
    """
    Read a bbox that may use 'w'/'h' OR 'width'/'height' keys, OR be a raw list.
    Always returns canonical {'x','y','width','height'}.
    Never raises.
    """
    return normalize_bbox(raw)


def region_bbox(region: Dict[str, Any]) -> Dict[str, float]:
    """
    Extract a canonical bbox from a region/finding dict.
    Tries 'bbox', 'bounding_box', 'coordinates', 'bounds' keys in order.
    Never crashes.
    """
    for key in ("bbox", "bounding_box", "coordinates", "bounds", "box"):
        raw = region.get(key)
        if raw is not None:
            return normalize_bbox(raw)
    return _zero()


def region_xyxy(region: Dict[str, Any]) -> List[float]:
    """Return the xyxy list for a region dict (for IoU math etc.)."""
    return bbox_to_xyxy(region_bbox(region))


def coords_string(bbox: Dict[str, float]) -> str:
    """Human-readable string: '(x=12, y=34, w=56, h=78)'."""
    return (
        f"(x={int(bbox.get('x',0))}, y={int(bbox.get('y',0))}, "
        f"w={int(bbox.get('width',0))}, h={int(bbox.get('height',0))})"
    )


def bbox_iou(a: Dict[str, float], b: Dict[str, float]) -> float:
    """IoU between two canonical bbox dicts. Always safe."""
    try:
        a1, b1 = bbox_to_xyxy(a), bbox_to_xyxy(b)
        ix1, iy1 = max(a1[0], b1[0]), max(a1[1], b1[1])
        ix2, iy2 = min(a1[2], b1[2]), min(a1[3], b1[3])
        inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
        if inter <= 0:
            return 0.0
        area_a = (a1[2] - a1[0]) * (a1[3] - a1[1])
        area_b = (b1[2] - b1[0]) * (b1[3] - b1[1])
        union = area_a + area_b - inter
        return inter / union if union > 0 else 0.0
    except Exception:
        return 0.0


def attach_standard_bbox(region: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return a *copy* of region with all bbox keys normalised.

    Sets:
        region['bbox']         — canonical dict {x,y,width,height}
        region['bounding_box'] — same
        region['coordinates']  — xyxy list [x,y,x2,y2]
    """
    canon = region_bbox(region)
    xyxy = bbox_to_xyxy(canon)
    return {
        **region,
        "bbox": canon,
        "bounding_box": canon,
        "coordinates": xyxy,
    }


def normalize_localization_result(
    result: Dict[str, Any],
    *,
    page: int = 1,
    default_confidence: float = 0.0,
    default_severity: str = "Medium",
) -> Dict[str, Any]:
    """
    Wrap any localization finding dict into the universal schema:

        {
            "bbox":       {"x": ..., "y": ..., "width": ..., "height": ...},
            "polygon":    [[x,y], ...],
            "page":       1,
            "confidence": 0.96,
            "severity":   "High",
            "coordinates": [x1, y1, x2, y2],   # IoU xyxy
            ...original keys preserved...
        }

    Never raises. Safe to call on any dict, list, or None.
    """
    if not isinstance(result, dict):
        result = {}

    # Normalise the bbox — reads bbox / bounding_box / coordinates / bounds
    canon = region_bbox(result)
    xyxy = bbox_to_xyxy(canon)

    # Polygon — keep existing or empty list
    poly = result.get("polygon") or []
    if not isinstance(poly, list):
        poly = []

    # Confidence — normalise to 0-1 range
    raw_conf = result.get("confidence") or result.get("score") or default_confidence
    try:
        conf = float(raw_conf)
        if conf > 1.0:
            conf /= 100.0
    except (TypeError, ValueError):
        conf = default_confidence

    # Severity
    severity = result.get("severity") or default_severity
    if not severity:
        if conf >= 0.75:
            severity = "Critical"
        elif conf >= 0.55:
            severity = "High"
        elif conf >= 0.40:
            severity = "Medium"
        else:
            severity = "Low"

    return {
        **result,
        # Always-canonical bbox keys — never a raw list
        "bbox": canon,
        "bounding_box": canon,
        # xyxy kept for IoU math; clearly named so consumers know it's a list
        "coordinates": xyxy,
        "polygon": poly,
        "page": int(result.get("page") or result.get("page_number") or page),
        "confidence": round(conf, 4),
        "severity": severity,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _zero() -> Dict[str, float]:
    return {"x": 0.0, "y": 0.0, "width": 0.0, "height": 0.0}


def _normalize(raw: Any) -> Dict[str, float]:  # noqa: C901
    if raw is None:
        return _zero()

    # Already a dict
    if isinstance(raw, dict):
        # Already canonical (x/y keys or left/top keys)
        if "x" in raw or "y" in raw:
            x = float(raw.get("x") or raw.get("left") or 0)
            y = float(raw.get("y") or raw.get("top") or 0)
            # Support both w/h (legacy) and width/height (canonical)
            w = float(raw.get("width") or raw.get("w") or 0)
            h = float(raw.get("height") or raw.get("h") or 0)
            return {"x": x, "y": y, "width": w, "height": h}
        # {x1,y1,x2,y2} variant
        if "x1" in raw or "x2" in raw:
            x1 = float(raw.get("x1") or raw.get("left") or 0)
            y1 = float(raw.get("y1") or raw.get("top") or 0)
            x2 = float(raw.get("x2") or raw.get("right") or 0)
            y2 = float(raw.get("y2") or raw.get("bottom") or 0)
            return {"x": x1, "y": y1, "width": max(0.0, x2 - x1), "height": max(0.0, y2 - y1)}
        # {left, top, right, bottom}
        if "left" in raw or "top" in raw:
            x = float(raw.get("left") or 0)
            y = float(raw.get("top") or 0)
            w = float(raw.get("right", 0)) - x
            h = float(raw.get("bottom", 0)) - y
            return {"x": x, "y": y, "width": max(0.0, w), "height": max(0.0, h)}
        return _zero()

    # Sequence types
    if not isinstance(raw, (list, tuple)) or len(raw) == 0:
        return _zero()

    # [[x1,y1],[x2,y2]] two-point
    if len(raw) == 2 and isinstance(raw[0], (list, tuple)):
        x1, y1 = float(raw[0][0]), float(raw[0][1])
        x2, y2 = float(raw[1][0]), float(raw[1][1])
        return {"x": x1, "y": y1, "width": abs(x2 - x1), "height": abs(y2 - y1)}

    # Quad polygon [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
    if len(raw) >= 4 and isinstance(raw[0], (list, tuple)):
        xs = [float(p[0]) for p in raw]
        ys = [float(p[1]) for p in raw]
        return {
            "x": min(xs), "y": min(ys),
            "width": max(xs) - min(xs),
            "height": max(ys) - min(ys),
        }

    # Flat list: [x, y, w, h] vs [x1, y1, x2, y2]
    if len(raw) >= 4:
        a, b, c, d = float(raw[0]), float(raw[1]), float(raw[2]), float(raw[3])
        # Heuristic: if c > a + 1 and d > b + 1, treat as xyxy
        if c > a + 1 and d > b + 1:
            return {"x": a, "y": b, "width": max(0.0, c - a), "height": max(0.0, d - b)}
        # Otherwise xywh
        return {"x": a, "y": b, "width": max(0.0, c), "height": max(0.0, d)}

    if len(raw) == 2:
        a, b = float(raw[0]), float(raw[1])
        return {"x": a, "y": b, "width": 0.0, "height": 0.0}

    return _zero()
