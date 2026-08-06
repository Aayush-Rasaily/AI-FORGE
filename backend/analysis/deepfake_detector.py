"""
DeepFake Detection Engine.

Delegates to FaceForensics++ multi-model engine while preserving API contract.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

import cv2
import numpy as np

from backend.analysis.face_forensics.engine import analyze_face_forensics

logger = logging.getLogger(__name__)

FACE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)
EYE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_eye.xml"
)


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _detect_blink_anomaly(frames: List[np.ndarray]) -> Dict[str, Any]:
    """Analyze eye aspect ratio across video frames for blink absence."""
    ear_values: List[float] = []
    for frame in frames:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = FACE_CASCADE.detectMultiScale(gray, 1.2, 5, minSize=(40, 40))
        if len(faces) == 0:
            continue
        fx, fy, fw, fh = faces[0]
        face_gray = gray[fy: fy + fh, fx: fx + fw]
        eyes = EYE_CASCADE.detectMultiScale(face_gray, 1.1, 3)
        if len(eyes) >= 1:
            ex, ey, ew, eh = eyes[0]
            ear = eh / (ew + 1e-6)
            ear_values.append(ear)

    if len(ear_values) < 3:
        return {"blink_anomaly_score": 0.0, "blink_detected": False, "message": "Insufficient frames for blink analysis."}

    ear_arr = np.array(ear_values)
    blinks = int(np.sum(ear_arr < 0.2))
    blink_rate = blinks / len(ear_arr)

    if len(ear_arr) >= 8 and blinks == 0:
        return {
            "blink_anomaly_score": 0.85,
            "blink_detected": False,
            "message": "No blinks detected across analyzed frames — possible deepfake.",
        }
    if blink_rate < 0.05 and len(ear_arr) >= 6:
        return {
            "blink_anomaly_score": 0.65,
            "blink_detected": blinks > 0,
            "message": "Abnormally low blink rate detected.",
        }
    return {
        "blink_anomaly_score": 0.1,
        "blink_detected": blinks > 0,
        "message": "Blink pattern appears natural.",
    }


def analyze_deepfake_image(
    image_path: str,
    output_dir: str,
) -> Dict[str, Any]:
    """Run deepfake detection on a single image via FaceForensics++ engine."""
    result = analyze_face_forensics(image_path, output_dir)
    result["media_type"] = "image"

    # Backward-compatible face_analyses shape
    face_analyses = []
    for fa in result.get("face_analyses", []):
        face_analyses.append({
            "bbox": fa.get("bbox"),
            "probability": fa.get("deepfake_score", 0),
            "signals": fa.get("signals", []),
            "models": fa.get("models", {}),
        })
    result["face_analyses"] = face_analyses
    return result


def analyze_deepfake_video(
    video_path: str,
    output_dir: str,
    max_frames: int = 12,
) -> Dict[str, Any]:
    """Run deepfake detection on video keyframes."""
    from backend.ingestion.video_processor import extract_keyframes, get_video_metadata

    video_path = Path(video_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = get_video_metadata(str(video_path))
    keyframe_dir = output_dir / "keyframes"
    frames_info = extract_keyframes(str(video_path), str(keyframe_dir), max_frames=max_frames)

    frame_results: List[Dict[str, Any]] = []
    frame_images: List[np.ndarray] = []
    probabilities: List[float] = []

    for fi in frames_info:
        frame_path = fi.get("path") or fi.get("image", "")
        if not frame_path or not Path(frame_path).exists():
            continue
        frame_bgr = cv2.imread(str(frame_path))
        if frame_bgr is None:
            continue
        frame_images.append(frame_bgr)
        result = analyze_deepfake_image(str(frame_path), str(output_dir / "frames"))
        probabilities.append(result.get("deepfake_probability", 0))
        frame_results.append({
            "frame_number": fi.get("frame_number", 0),
            "timestamp": fi.get("timestamp", 0),
            "deepfake_probability": result.get("deepfake_probability", 0),
            "faces_detected": result.get("faces_detected", 0),
            "verdict": result.get("verdict", ""),
            "heatmap": result.get("heatmap"),
        })

    blink = _detect_blink_anomaly(frame_images) if frame_images else {}

    avg_prob = float(np.mean(probabilities)) if probabilities else 0.0
    max_prob = float(np.max(probabilities)) if probabilities else 0.0
    blink_score = blink.get("blink_anomaly_score", 0)

    combined_prob = _clamp(0.7 * max_prob + 0.3 * blink_score)
    all_signals: List[Dict[str, Any]] = []
    for fr in frame_results:
        if fr.get("deepfake_probability", 0) > 0.45:
            all_signals.append({
                "type": "frame_anomaly",
                "what": f"Frame {fr['frame_number']} flagged at {fr['deepfake_probability']:.0%} deepfake probability.",
                "why": "Per-frame facial forensic analysis exceeded suspicion threshold.",
                "score": fr["deepfake_probability"],
            })

    if blink_score > 0.5:
        all_signals.append({
            "type": "blink_anomaly",
            "what": blink.get("message", "Blink anomaly detected."),
            "why": "Natural videos exhibit periodic eye blinks; absence suggests synthetic generation.",
            "score": blink_score,
        })

    if combined_prob >= 0.7:
        verdict = "Likely Deepfake"
    elif combined_prob >= 0.45:
        verdict = "Suspicious — Possible Deepfake"
    else:
        verdict = "Likely Authentic"

    confidence = _clamp(0.55 + len(frame_results) * 0.03 + len(all_signals) * 0.08)

    return {
        "success": True,
        "media_type": "video",
        "video_metadata": metadata,
        "frames_analyzed": len(frame_results),
        "deepfake_probability": round(combined_prob, 4),
        "confidence": round(confidence, 4),
        "verdict": verdict,
        "explanation": " ".join(s["what"] for s in all_signals[:3]) or "Video facial analysis did not detect strong deepfake indicators.",
        "findings": all_signals,
        "signals": [s["what"] for s in all_signals],
        "blink_analysis": blink,
        "frames": frame_results,
        "frame_probabilities": probabilities,
    }
