"""
Face forensics engine — FaceForensics++ inspired multi-model parallel analysis.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import cv2
import numpy as np

from backend.analysis.face_forensics.consistency import detect_faces, run_consistency_checks
from backend.analysis.face_forensics.mesonet_detector import detect_mesonet
from backend.analysis.face_forensics.xception_detector import detect_xception
from backend.utils.hardware import get_device_info

logger = logging.getLogger("ai_forge.face_forensics")

MODEL_WEIGHTS = {
    "xception": 0.30,
    "mesonet": 0.28,
    "consistency": 0.42,
}


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


def _generate_heatmap(
    image_bgr: np.ndarray,
    face_results: List[Dict[str, Any]],
    output_path: Path,
) -> str:
    h, w = image_bgr.shape[:2]
    heatmap = np.zeros((h, w), dtype=np.float32)
    for fr in face_results:
        x, y, fw, fh = fr["bbox"]
        prob = fr["deepfake_score"]
        cv2.ellipse(heatmap, (x + fw // 2, y + fh // 2), (fw // 2, fh // 2), 0, 0, 360, prob, -1)
    heatmap = cv2.GaussianBlur(heatmap, (51, 51), 0)
    if heatmap.max() > heatmap.min():
        heatmap = (heatmap - heatmap.min()) / (heatmap.max() - heatmap.min())

    colored = np.zeros((h, w, 3), dtype=np.uint8)
    colored[heatmap < 0.33] = [34, 197, 94]
    colored[(heatmap >= 0.33) & (heatmap < 0.66)] = [249, 115, 22]
    colored[heatmap >= 0.66] = [239, 68, 68]
    overlay = cv2.addWeighted(image_bgr, 0.5, colored, 0.5, 0)
    cv2.imwrite(str(output_path), overlay)
    return str(output_path)


def _analyze_face(
    image_bgr: np.ndarray,
    face_rect: Tuple[int, int, int, int],
) -> Dict[str, Any]:
    x, y, w, h = face_rect
    face_bgr = image_bgr[y: y + h, x: x + w]

    with ThreadPoolExecutor(max_workers=3) as executor:
        f_xception = executor.submit(detect_xception, face_bgr)
        f_mesonet = executor.submit(detect_mesonet, face_bgr)
        f_consistency = executor.submit(run_consistency_checks, image_bgr, face_rect)
        xception = f_xception.result()
        mesonet = f_mesonet.result()
        consistency = f_consistency.result()

    models = {"xception": xception, "mesonet": mesonet, "consistency": consistency}
    weighted = sum(
        float(models[k]["score"]) * MODEL_WEIGHTS[k] * float(models[k].get("confidence", 0.5))
        for k in MODEL_WEIGHTS
    )
    w_total = sum(MODEL_WEIGHTS[k] * float(models[k].get("confidence", 0.5)) for k in MODEL_WEIGHTS)
    deepfake_score = weighted / w_total if w_total > 0 else 0.0
    authenticity = 1.0 - deepfake_score

    signals = []
    for name, result in models.items():
        if result.get("score", 0) >= 0.4:
            signals.append({
                "type": name,
                "what": result.get("explanation", ""),
                "why": f"{name} forensic score: {result.get('score', 0):.0%}",
                "score": result.get("score", 0),
            })
    if consistency.get("checks"):
        for ck, cv in consistency["checks"].items():
            if cv.get("score", 0) >= 0.45:
                signals.append({
                    "type": ck,
                    "what": cv.get("explanation", ""),
                    "why": f"Consistency check failed: {ck}",
                    "score": cv.get("score", 0),
                })

    return {
        "bbox": [x, y, w, h],
        "deepfake_score": round(_clamp(deepfake_score), 4),
        "face_authenticity_score": round(_clamp(authenticity), 4),
        "models": models,
        "signals": signals,
    }


def fuse_face_results(face_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not face_results:
        return {
            "deepfake_probability": 0.0,
            "face_authenticity_score": 1.0,
            "confidence": 0.5,
            "verdict": "No Face Detected",
            "reasoning": "No faces detected for forensic analysis.",
        }

    max_deepfake = max(fr["deepfake_score"] for fr in face_results)
    avg_auth = float(np.mean([fr["face_authenticity_score"] for fr in face_results]))
    all_signals = [s for fr in face_results for s in fr.get("signals", [])]
    confidence = _clamp(0.55 + len(all_signals) * 0.06 + len(face_results) * 0.05)

    if max_deepfake >= 0.7:
        verdict = "Likely Deepfake"
    elif max_deepfake >= 0.45:
        verdict = "Suspicious — Possible Deepfake"
    else:
        verdict = "Likely Authentic"

    reasoning_parts = [s["what"] for s in all_signals[:4]]
    reasoning = (
        " ".join(reasoning_parts)
        if reasoning_parts
        else "FaceForensics++ multi-model analysis found no strong deepfake indicators."
    )

    return {
        "deepfake_probability": round(max_deepfake, 4),
        "face_authenticity_score": round(avg_auth, 4),
        "face_authenticity_pct": round(avg_auth * 100, 2),
        "confidence": round(confidence, 4),
        "verdict": verdict,
        "reasoning": reasoning,
        "models_used": ["xception", "mesonet", "faceforensics_consistency"],
    }


def analyze_face_forensics(
    image_path: str,
    output_dir: Optional[str] = None,
    progress: Optional[Callable[[str, str, float], None]] = None,
) -> Dict[str, Any]:
    """Run FaceForensics++ inspired analysis on all detected faces."""
    image_path = Path(image_path)
    image_bgr = cv2.imread(str(image_path))
    if image_bgr is None:
        raise ValueError(f"Cannot read image: {image_path}")

    if progress:
        progress("face_forensics", "running")

    device_info = get_device_info()
    faces = detect_faces(image_bgr)

    if not faces:
        if progress:
            progress("face_forensics", "completed")
        return {
            "success": True,
            "faces_detected": 0,
            "deepfake_probability": 0.0,
            "face_authenticity_score": 1.0,
            "face_authenticity_pct": 100.0,
            "confidence": 0.5,
            "verdict": "No Face Detected",
            "reasoning": "No faces detected. Face forensics requires visible facial regions.",
            "explanation": "No faces detected. Face forensics requires visible facial regions.",
            "findings": [],
            "signals": [],
            "face_analyses": [],
            "heatmap": None,
            "device": device_info.get("device", "cpu"),
        }

    face_results: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(4, len(faces))) as executor:
        futures = [executor.submit(_analyze_face, image_bgr, f) for f in faces]
        for future in as_completed(futures):
            try:
                face_results.append(future.result())
            except Exception as exc:
                logger.warning("Face analysis failed: %s", exc)

    fusion = fuse_face_results(face_results)
    heatmap = None
    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        heatmap = _generate_heatmap(
            image_bgr, face_results, out / f"{image_path.stem}_face_forensics_heatmap.jpg"
        )

    if progress:
        progress("face_forensics", "completed")

    return {
        "success": True,
        "faces_detected": len(faces),
        "deepfake_probability": fusion["deepfake_probability"],
        "face_authenticity_score": fusion["face_authenticity_score"],
        "face_authenticity_pct": fusion["face_authenticity_pct"],
        "confidence": fusion["confidence"],
        "verdict": fusion["verdict"],
        "reasoning": fusion["reasoning"],
        "explanation": fusion["reasoning"],
        "findings": [s for fr in face_results for s in fr.get("signals", [])],
        "signals": [s["what"] for fr in face_results for s in fr.get("signals", [])],
        "face_analyses": face_results,
        "fusion": fusion,
        "heatmap": heatmap,
        "artifacts": {"heatmap": heatmap} if heatmap else {},
        "device": device_info.get("device", "cpu"),
    }
