"""
Normalize legacy detector module outputs into DetectorOutput contracts.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.engines.contracts import (
    AffectedRegion,
    DetectorOutput,
    failed_detector,
    make_detector_output,
    skipped_detector,
)


def _f(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _regions_from_boxes(boxes: Any, label: str = "anomaly") -> List[AffectedRegion]:
    out: List[AffectedRegion] = []
    if not boxes:
        return out
    for i, box in enumerate(boxes if isinstance(boxes, list) else []):
        if not isinstance(box, dict):
            continue
        bbox = box.get("bbox") or box.get("box") or box
        if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
            x, y, w, h = map(int, bbox[:4])
        elif isinstance(bbox, dict):
            x = int(bbox.get("x", bbox.get("left", 0)))
            y = int(bbox.get("y", bbox.get("top", 0)))
            w = int(bbox.get("w", bbox.get("width", 0)))
            h = int(bbox.get("h", bbox.get("height", 0)))
        else:
            continue
        out.append({
            "id": str(box.get("id") or f"{label}-{i + 1}"),
            "x": x,
            "y": y,
            "width": w,
            "height": h,
            "score": _f(box.get("score", box.get("confidence", 0.5))),
            "label": str(box.get("label") or box.get("text") or label),
        })
    return out[:40]


def adapt_ela(forensics: Dict[str, Any]) -> DetectorOutput:
    if not forensics:
        return skipped_detector("ela", "ELA module not executed")
    ela = forensics.get("ela") or forensics
    signals = forensics.get("signals") or {}
    score = _f(
        ela.get("score")
        or forensics.get("ela_score")
        or signals.get("ela_score")
        or 0
    )
    if score > 1:
        score /= 100.0
    reason = (
        ela.get("explanation")
        or ela.get("reason")
        or signals.get("ela_reason")
        or (
            f"Error Level Analysis score={score:.2f} indicates "
            f"{'localized recompression' if score >= 0.35 else 'consistent compression'}."
        )
    )
    return make_detector_output(
        "ela",
        score=score,
        confidence=max(0.45, min(0.95, 0.5 + score * 0.4)),
        technical_reason=str(reason),
        metrics={"ela_score": score, "mean_error": ela.get("mean_error")},
        affected_regions=_regions_from_boxes(ela.get("regions") or ela.get("hotspots"), "ela"),
    )


def adapt_wavelet(forensics: Dict[str, Any]) -> DetectorOutput:
    if not forensics:
        return skipped_detector("wavelet", "Wavelet module not executed")
    wav = forensics.get("wavelet") or forensics
    signals = forensics.get("signals") or {}
    score = _f(
        wav.get("score")
        or forensics.get("wavelet_score")
        or signals.get("wavelet_score")
        or 0
    )
    if score > 1:
        score /= 100.0
    reason = wav.get("explanation") or (
        f"Wavelet high-frequency energy score={score:.2f}."
    )
    return make_detector_output(
        "wavelet",
        score=score,
        confidence=max(0.4, min(0.92, 0.48 + score * 0.4)),
        technical_reason=str(reason),
        metrics={"wavelet_score": score},
    )


def adapt_copy_move(result: Dict[str, Any]) -> DetectorOutput:
    if not result:
        return skipped_detector("copy_move", "Copy-move module not executed")
    detected = bool(result.get("detected") or result.get("copy_move_detected"))
    score = _f(result.get("score", result.get("copy_move_score", 0.85 if detected else 0)))
    if score > 1:
        score /= 100.0
    if detected and score < 0.4:
        score = 0.85
    reason = result.get("explanation") or result.get("reason") or (
        f"Copy-move {'detected' if detected else 'not detected'}; "
        f"matched_points={result.get('matched_points', result.get('matches', 'n/a'))}."
    )
    return make_detector_output(
        "copy_move",
        score=score,
        confidence=max(0.5, min(0.97, 0.55 + score * 0.4)),
        technical_reason=str(reason),
        metrics={
            "detected": detected,
            "matched_points": result.get("matched_points"),
            "ransac_inliers": result.get("ransac_inliers"),
        },
        affected_regions=_regions_from_boxes(result.get("regions") or result.get("matches"), "copy_move"),
    )


def adapt_noise(result: Dict[str, Any]) -> DetectorOutput:
    if not result:
        return skipped_detector("noise", "Noise module not executed")
    score = _f(
        result.get("noise_inconsistency")
        or result.get("score")
        or result.get("inconsistency")
        or 0
    )
    if score > 1:
        score /= 100.0
    reason = result.get("explanation") or (
        f"Noise residual inconsistency={score:.2f}."
    )
    return make_detector_output(
        "noise",
        score=score,
        confidence=max(0.4, min(0.9, 0.45 + score * 0.4)),
        technical_reason=str(reason),
        metrics={"noise_inconsistency": score},
    )


def adapt_metadata(result: Dict[str, Any]) -> DetectorOutput:
    if not result:
        return skipped_detector("metadata", "Metadata module not executed")
    suspicious = bool(result.get("suspicious") or result.get("metadata_suspicious"))
    score = _f(result.get("risk_score", result.get("score", 0.7 if suspicious else 0)))
    if score > 1:
        score /= 100.0
    software = result.get("software") or result.get("editing_software")
    reason = result.get("explanation") or (
        f"Metadata {'flags editing software' if suspicious else 'appears consistent'}"
        + (f" ({software})" if software else "")
        + "."
    )
    return make_detector_output(
        "metadata",
        score=score,
        confidence=max(0.4, min(0.9, 0.5 + (0.3 if suspicious else 0))),
        technical_reason=str(reason),
        metrics={
            "suspicious": suspicious,
            "software": software,
            "keys": list((result.get("exif") or result.get("metadata") or {}).keys())[:20]
            if isinstance(result.get("exif") or result.get("metadata"), dict)
            else [],
        },
    )


def adapt_edge(forensics: Dict[str, Any]) -> DetectorOutput:
    if not forensics:
        return skipped_detector("edge", "Edge module not executed")
    edges = forensics.get("edges") or forensics
    score = _f(edges.get("edge_density", forensics.get("edge_density", edges.get("score", 0))))
    if score > 1:
        score /= 100.0
    # edge density alone is weak — only elevate when high
    manip = score if score >= 0.55 else score * 0.35
    return make_detector_output(
        "edge",
        score=manip,
        confidence=0.55,
        technical_reason=f"Edge density={score:.2f}.",
        metrics={"edge_density": score},
    )


def adapt_generic(
    name: str,
    result: Dict[str, Any],
    *,
    score_keys: Optional[List[str]] = None,
    reason_key: str = "explanation",
) -> DetectorOutput:
    if not result or result.get("skipped"):
        return skipped_detector(name, f"{name} module not executed")
    if result.get("error") and not any(k in result for k in (score_keys or ["score"])):
        return failed_detector(name, str(result.get("error")))
    score_keys = score_keys or ["score", "risk", "probability", "anomaly_score"]
    score = 0.0
    for k in score_keys:
        if k in result and result[k] is not None:
            score = _f(result[k])
            break
    if score > 1:
        score /= 100.0
    reason = result.get(reason_key) or result.get("reason") or result.get("technical_reason") or (
        f"{name} score={score:.2f}."
    )
    conf = _f(result.get("confidence"), 0.5 + score * 0.3)
    if conf > 1:
        conf /= 100.0
    return make_detector_output(
        name,
        score=score,
        confidence=conf,
        technical_reason=str(reason),
        metrics={k: result.get(k) for k in list(result.keys())[:24] if k not in ("regions",)},
        affected_regions=_regions_from_boxes(result.get("regions") or result.get("anomalies"), name),
    )


def collect_detector_outputs(analysis: Dict[str, Any]) -> List[DetectorOutput]:
    """Build DetectorOutput list from a unified analysis payload."""
    signals = analysis.get("signals") or {}
    forensics = analysis.get("forensics") or analysis.get("image_forensics") or {}
    outputs: List[DetectorOutput] = []

    # Prefer nested modules; fall back to signals
    cm = analysis.get("copy_move") or {}
    outputs.append(adapt_copy_move(cm if cm else {
        "score": signals.get("copy_move_score"),
        "detected": signals.get("copy_move_detected"),
        "matched_points": signals.get("matched_points"),
    }))
    forensics_payload = forensics if forensics else {}
    if signals:
        # Merge top-level signals so ELA/wavelet adapters see scores
        merged = dict(forensics_payload)
        merged_signals = dict(forensics_payload.get("signals") or {})
        merged_signals.update({k: v for k, v in signals.items() if v is not None})
        merged["signals"] = merged_signals
        forensics_payload = merged
    outputs.append(adapt_ela(forensics_payload if forensics_payload else {"ela_score": signals.get("ela_score")}))
    outputs.append(adapt_wavelet(forensics_payload if forensics_payload else {"wavelet_score": signals.get("wavelet_score")}))
    outputs.append(adapt_noise(analysis.get("noise") or {
        "noise_inconsistency": signals.get("noise_inconsistency"),
        "score": signals.get("noise_score"),
    }))
    outputs.append(adapt_metadata(analysis.get("metadata") or analysis.get("metadata_forensics") or {
        "suspicious": signals.get("metadata_suspicious"),
        "risk_score": signals.get("metadata_risk_score") or signals.get("metadata_score"),
        "software": signals.get("software"),
    }))
    outputs.append(adapt_edge(forensics if forensics else {"edge_density": signals.get("edge_density")}))

    outputs.append(adapt_generic("tampering", analysis.get("tampering_detection") or analysis.get("tampering") or {
        "score": signals.get("tampering_score"),
    }, score_keys=["tampering_score", "score"]))

    gan = analysis.get("gan_detection") or analysis.get("ai_generation") or {}
    outputs.append(adapt_generic(
        "gan",
        gan if isinstance(gan, dict) else {},
        score_keys=["ai_generated_score", "ai_generated_probability", "score"],
    ))
    face = analysis.get("face_forensics") or {}
    outputs.append(adapt_generic(
        "deepfake",
        face if isinstance(face, dict) else {},
        score_keys=["deepfake_probability", "score"],
    ))

    for name, key in (
        ("font", "font_consistency"),
        ("spacing", "spacing_analysis"),
        ("region_anomaly", "region_anomaly"),
        ("ocr", "ocr"),
        ("jpeg_block", "jpeg_block"),
        ("frequency", "frequency"),
        ("rgb", "rgb"),
        ("hsv", "hsv"),
        ("lab", "lab"),
        ("ycbcr", "ycbcr"),
    ):
        block = analysis.get(key) or {}
        if not block and name in (analysis.get("multispectral") or {}).get("detectors", {}):
            block = (analysis.get("multispectral") or {}).get("detectors", {}).get(name) or {}
        outputs.append(adapt_generic(name, block if isinstance(block, dict) else {}))

    # Deduplicate by detector_name (keep highest score)
    by_name: Dict[str, DetectorOutput] = {}
    for d in outputs:
        n = d["detector_name"]
        if n not in by_name or _f(d.get("score")) > _f(by_name[n].get("score")):
            by_name[n] = d
    return list(by_name.values())
