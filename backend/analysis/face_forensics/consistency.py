"""
Face consistency checks — blink, pose, skin, lighting, reflection, emotion.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import cv2
import numpy as np

FACE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)
EYE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_eye.xml"
)
SMILE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_smile.xml"
)


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def detect_faces(image_bgr: np.ndarray) -> List[Tuple[int, int, int, int]]:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    faces = FACE_CASCADE.detectMultiScale(gray, 1.15, 5, minSize=(48, 48))
    return [(int(x), int(y), int(w), int(h)) for x, y, w, h in faces]


def check_eye_blink(face_gray: np.ndarray) -> Dict[str, Any]:
    eyes = EYE_CASCADE.detectMultiScale(face_gray, 1.1, 3, minSize=(12, 12))
    if len(eyes) < 2:
        return {
            "score": 0.55,
            "confidence": 0.5,
            "explanation": "Eyes not clearly detected — blink analysis inconclusive.",
            "eyes_detected": len(eyes),
        }
    ears = [eh / (ew + 1e-6) for _, _, ew, eh in eyes[:2]]
    avg_ear = float(np.mean(ears))
    # Very open or very closed in static image can indicate synthetic face
    score = _clamp(abs(avg_ear - 0.28) * 2.5)
    return {
        "score": round(score, 4),
        "confidence": 0.62,
        "explanation": (
            "Abnormal eye openness detected — deepfakes often show unnatural blink state."
            if score >= 0.4
            else "Eye openness appears within natural range."
        ),
        "eyes_detected": len(eyes),
        "eye_aspect_ratio": round(avg_ear, 4),
    }


def check_head_pose(image_bgr: np.ndarray, face_rect: Tuple[int, int, int, int]) -> Dict[str, Any]:
    x, y, w, h = face_rect
    face = image_bgr[y: y + h, x: x + w]
    gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
    left_half = gray[:, : w // 2]
    right_half = cv2.flip(gray[:, w // 2:], 1)
    min_w = min(left_half.shape[1], right_half.shape[1])
    diff = float(np.mean(np.abs(left_half[:, :min_w].astype(float) - right_half[:, :min_w].astype(float))))
    score = _clamp(diff / 35.0)
    return {
        "score": round(score, 4),
        "confidence": 0.65,
        "explanation": (
            "Head pose / facial symmetry inconsistency suggests possible face swap."
            if score >= 0.4
            else "Head pose and facial symmetry appear consistent."
        ),
    }


def check_skin_texture(face_bgr: np.ndarray) -> Dict[str, Any]:
    gray = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    lap = cv2.Laplacian(gray, cv2.CV_32F)
    center = lap[gray.shape[0] // 4: 3 * gray.shape[0] // 4, gray.shape[1] // 4: 3 * gray.shape[1] // 4]
    periphery = lap.copy()
    periphery[gray.shape[0] // 4: 3 * gray.shape[0] // 4, gray.shape[1] // 4: 3 * gray.shape[1] // 4] = 0
    c_var = float(np.var(center))
    p_var = float(np.var(periphery[periphery != 0])) if np.any(periphery != 0) else 1.0
    score = _clamp((c_var / (p_var + 1e-6) - 0.6) / 1.5)
    return {
        "score": round(score, 4),
        "confidence": 0.7,
        "explanation": (
            "Skin texture shows unnatural center-periphery noise — common in GAN faces."
            if score >= 0.4
            else "Skin micro-texture appears natural."
        ),
    }


def check_lighting_consistency(image_bgr: np.ndarray, face_rect: Tuple[int, int, int, int]) -> Dict[str, Any]:
    x, y, w, h = face_rect
    face = image_bgr[y: y + h, x: x + w]
    bg_mask = np.ones(image_bgr.shape[:2], dtype=np.uint8)
    cv2.rectangle(bg_mask, (x, y), (x + w, y + h), 0, -1)
    lab_face = cv2.cvtColor(face, cv2.COLOR_BGR2LAB).astype(np.float32)
    lab_bg = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    face_l = float(np.mean(lab_face[:, :, 0]))
    bg_l = float(np.mean(lab_bg[bg_mask > 0, 0])) if np.any(bg_mask > 0) else face_l
    diff = abs(face_l - bg_l) / 128.0
    score = _clamp(diff * 1.8)
    return {
        "score": round(score, 4),
        "confidence": 0.66,
        "explanation": (
            "Face lighting direction inconsistent with background — possible compositing."
            if score >= 0.4
            else "Face and background lighting appear coherent."
        ),
    }


def check_reflection_consistency(face_bgr: np.ndarray) -> Dict[str, Any]:
    gray = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY)
    _, bright = cv2.threshold(gray, 220, 255, cv2.THRESH_BINARY)
    left = bright[:, : gray.shape[1] // 2]
    right = cv2.flip(bright[:, gray.shape[1] // 2:], 1)
    min_w = min(left.shape[1], right.shape[1])
    overlap = float(np.sum(left[:, :min_w] & right[:, :min_w])) / (float(np.sum(bright > 0)) + 1e-6)
    score = _clamp(1.0 - overlap * 2.5) if np.sum(bright > 0) > 50 else 0.1
    return {
        "score": round(score, 4),
        "confidence": 0.58,
        "explanation": (
            "Specular highlights asymmetric across face — reflection inconsistency detected."
            if score >= 0.4
            else "Eye/skin reflections appear symmetric."
        ),
    }


def check_emotion_consistency(face_gray: np.ndarray) -> Dict[str, Any]:
    smiles = SMILE_CASCADE.detectMultiScale(face_gray, 1.7, 12)
    eyes = EYE_CASCADE.detectMultiScale(face_gray, 1.1, 3)
    # Emotion proxy: smile detected but tense eyes
    smile_present = len(smiles) > 0
    eye_tension = 0.0
    if eyes:
        eye_tension = float(np.mean([eh / (ew + 1e-6) for _, _, ew, eh in eyes]))
    score = 0.0
    if smile_present and eye_tension < 0.15:
        score = 0.55
    elif smile_present and eye_tension > 0.35:
        score = 0.35
    return {
        "score": round(score, 4),
        "confidence": 0.55,
        "explanation": (
            "Facial expression components (eyes vs mouth) appear emotionally inconsistent."
            if score >= 0.4
            else "Emotional expression appears internally consistent."
        ),
    }


def run_consistency_checks(image_bgr: np.ndarray, face_rect: Tuple[int, int, int, int]) -> Dict[str, Any]:
    x, y, w, h = face_rect
    face_bgr = image_bgr[y: y + h, x: x + w]
    face_gray = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY)

    checks = {
        "eye_blink": check_eye_blink(face_gray),
        "head_pose": check_head_pose(image_bgr, face_rect),
        "skin_texture": check_skin_texture(face_bgr),
        "lighting": check_lighting_consistency(image_bgr, face_rect),
        "reflection": check_reflection_consistency(face_bgr),
        "emotion": check_emotion_consistency(face_gray),
    }

    weights = {
        "eye_blink": 0.15,
        "head_pose": 0.18,
        "skin_texture": 0.20,
        "lighting": 0.18,
        "reflection": 0.14,
        "emotion": 0.15,
    }
    total = sum(
        float(checks[k]["score"]) * weights[k] * float(checks[k].get("confidence", 0.5))
        for k in checks
    )
    w_sum = sum(weights[k] * float(checks[k].get("confidence", 0.5)) for k in checks)
    score = total / w_sum if w_sum > 0 else 0.0

    return {
        "score": round(score, 4),
        "confidence": round(np.mean([checks[k].get("confidence", 0.5) for k in checks]), 4),
        "checks": checks,
        "explanation": " | ".join(
            c["explanation"] for c in checks.values() if c["score"] >= 0.4
        ) or "All consistency checks passed within normal thresholds.",
    }
