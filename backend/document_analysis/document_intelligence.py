"""
Document intelligence engine — LayoutLMv3 + Donut + tampering detectors.

Detects: header inconsistency, signature mismatch, fake stamps, logo manipulation,
wrong fonts, spacing anomalies, tampered paragraphs.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

from backend.document_analysis.models.donut_analyzer import analyze_donut
from backend.document_analysis.models.layoutlmv3_analyzer import analyze_layoutlmv3

logger = logging.getLogger("ai_forge.document_intelligence")

ISSUE_WEIGHTS = {
    "header_inconsistency": 0.12,
    "signature_mismatch": 0.15,
    "fake_stamp": 0.14,
    "logo_manipulation": 0.13,
    "wrong_font": 0.11,
    "spacing_anomaly": 0.10,
    "tampered_paragraph": 0.15,
    "layout_anomaly": 0.10,
}


def _issue(
    issue_type: str,
    severity: str,
    score: float,
    description: str,
    bbox: Optional[List] = None,
    extra: Optional[Dict] = None,
) -> Dict[str, Any]:
    return {
        "type": issue_type,
        "severity": severity,
        "score": round(float(score), 4),
        "description": description,
        "bbox": bbox,
        **(extra or {}),
    }


def _severity(score: float) -> str:
    if score >= 0.7:
        return "critical"
    if score >= 0.45:
        return "high"
    if score >= 0.25:
        return "medium"
    return "low"


def detect_header_inconsistency(
    layout_data: Dict[str, Any],
    layoutlm_result: Dict[str, Any],
    image_shape: tuple,
) -> List[Dict[str, Any]]:
    issues = []
    h = image_shape[0]
    lines = layout_data.get("lines", [])
    header_lines = [ln for ln in lines if ln.get("words") and min(w.get("top", h) for w in ln["words"]) < h * 0.15]
    body_lines = [ln for ln in lines if ln.get("words") and min(w.get("top", 0) for w in ln["words"]) >= h * 0.15]

    score = float(layoutlm_result.get("layout_anomaly_score", 0))
    if header_lines and body_lines:
        h_sizes = [np.mean([w.get("height", 0) for w in ln["words"]]) for ln in header_lines]
        b_sizes = [np.mean([w.get("height", 0) for w in ln["words"]]) for ln in body_lines]
        if h_sizes and b_sizes:
            ratio = abs(np.mean(h_sizes) - np.mean(b_sizes)) / (np.mean(b_sizes) + 1e-6)
            score = max(score, min(1.0, ratio * 0.9))

    if score >= 0.25:
        bbox = None
        if header_lines and header_lines[0].get("words"):
            ws = header_lines[0]["words"]
            bbox = [
                [min(w.get("left", 0) for w in ws), min(w.get("top", 0) for w in ws)],
                [max(w.get("right", 0) for w in ws), min(w.get("top", 0) for w in ws)],
                [max(w.get("right", 0) for w in ws), max(w.get("bottom", 0) for w in ws)],
                [min(w.get("left", 0) for w in ws), max(w.get("bottom", 0) for w in ws)],
            ]
        issues.append(_issue(
            "header_inconsistency", _severity(score), score,
            "Header region shows font size or layout inconsistent with document body.",
            bbox=bbox,
        ))
    return issues


def detect_signature_mismatch(image_path: str) -> List[Dict[str, Any]]:
    issues = []
    img = cv2.imread(str(image_path))
    if img is None:
        return issues

    h, w = img.shape[:2]
    lower = img[int(h * 0.65):, :]
    gray = cv2.cvtColor(lower, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 40, 120)
    ink_ratio = float(np.count_nonzero(edges)) / edges.size

    # Signature-like ink blob in lower region
    if ink_ratio > 0.02:
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        sig_contours = [c for c in contours if 500 < cv2.contourArea(c) < w * h * 0.08]
        if sig_contours:
            largest = max(sig_contours, key=cv2.contourArea)
            x, y, cw, ch = cv2.boundingRect(largest)
            roi = lower[y: y + ch, x: x + cw]
            lap = cv2.Laplacian(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), cv2.CV_64F)
            texture = float(lap.var())
            score = min(1.0, texture / 1200.0) if texture > 400 else 0.35
            if score >= 0.3:
                issues.append(_issue(
                    "signature_mismatch", _severity(score), score,
                    "Signature region shows texture/compression anomalies — possible pasted signature.",
                    bbox=[[x, y + int(h * 0.65)], [x + cw, y + int(h * 0.65)],
                          [x + cw, y + ch + int(h * 0.65)], [x, y + ch + int(h * 0.65)]],
                ))
    return issues


def detect_fake_stamps(image_path: str) -> List[Dict[str, Any]]:
    issues = []
    img = cv2.imread(str(image_path))
    if img is None:
        return issues

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    # Red stamp hues
    mask1 = cv2.inRange(hsv, np.array([0, 80, 80]), np.array([12, 255, 255]))
    mask2 = cv2.inRange(hsv, np.array([165, 80, 80]), np.array([180, 255, 255]))
    red_mask = cv2.bitwise_or(mask1, mask2)
    red_ratio = float(np.count_nonzero(red_mask)) / red_mask.size

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    circles = cv2.HoughCircles(
        gray, cv2.HOUGH_GRADIENT, dp=1.2, minDist=40,
        param1=80, param2=35, minRadius=15, maxRadius=min(img.shape[:2]) // 4,
    )

    score = 0.0
    bbox = None
    if circles is not None and red_ratio > 0.001:
        circles = np.uint16(np.around(circles))
        cx, cy, r = circles[0][0]
        score = min(1.0, red_ratio * 80 + 0.3)
        bbox = [
            [cx - r, cy - r], [cx + r, cy - r],
            [cx + r, cy + r], [cx - r, cy + r],
        ]
    elif red_ratio > 0.005:
        score = min(1.0, red_ratio * 50)
        ys, xs = np.where(red_mask > 0)
        if len(xs) > 0:
            bbox = [[int(xs.min()), int(ys.min())], [int(xs.max()), int(ys.min())],
                    [int(xs.max()), int(ys.max())], [int(xs.min()), int(ys.max())]]

    if score >= 0.35:
        issues.append(_issue(
            "fake_stamp", _severity(score), score,
            "Circular red stamp/seal region detected — verify authenticity (possible fake stamp).",
            bbox=bbox,
        ))
    return issues


def detect_logo_manipulation(image_path: str, analysis_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    issues = []
    img = cv2.imread(str(image_path))
    if img is None:
        return issues

    h, w = img.shape[:2]
    logo_roi = img[0: int(h * 0.2), 0: int(w * 0.25)]
    if logo_roi.size == 0:
        return issues

    gray = cv2.cvtColor(logo_roi, cv2.COLOR_BGR2GRAY)
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    edge_var = float(lap.var())
    rest = img[int(h * 0.2):, int(w * 0.25):]
    rest_gray = cv2.cvtColor(rest, cv2.COLOR_BGR2GRAY) if rest.size else gray
    rest_var = float(cv2.Laplacian(rest_gray, cv2.CV_64F).var()) + 1e-6
    ratio = edge_var / rest_var
    score = min(1.0, max(0.0, (ratio - 1.2) / 2.0))

    if score >= 0.3:
        issues.append(_issue(
            "logo_manipulation", _severity(score), score,
            "Logo/header area shows compression or edge anomalies — possible logo replacement.",
            bbox=[[0, 0], [int(w * 0.25), 0], [int(w * 0.25), int(h * 0.2)], [0, int(h * 0.2)]],
        ))
    return issues


def detect_wrong_fonts(font_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues = []
    suspicious = font_result.get("suspicious_words", []) or []
    if not suspicious:
        return issues
    count = len(suspicious)
    score = min(1.0, count / max(5, font_result.get("total_words", 1) * 0.1))
    worst = max(suspicious, key=lambda w: w.get("score", 0))
    bbox = worst.get("bbox")
    if score >= 0.2:
        issues.append(_issue(
            "wrong_font", _severity(score), score,
            f"{count} word(s) show font/style inconsistency vs document baseline.",
            bbox=bbox,
            extra={"suspicious_count": count},
        ))
    return issues


def detect_spacing_anomalies(spacing_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues = []
    risk = float(spacing_result.get("risk_score", 0)) / 100.0
    if risk >= 0.2:
        issues.append(_issue(
            "spacing_anomaly", _severity(risk), risk,
            spacing_result.get("verdict", "Spacing or alignment anomaly detected."),
        ))
    return issues


def detect_tampered_paragraphs(
    region_result: Dict[str, Any],
    donut_result: Dict[str, Any],
    layoutlm_result: Dict[str, Any],
) -> List[Dict[str, Any]]:
    issues = []
    regions = region_result.get("high_risk_regions", []) or region_result.get("regions", [])
    parse_score = float(donut_result.get("parse_anomaly_score", 0))
    layout_score = float(layoutlm_result.get("layout_anomaly_score", 0))

    for region in regions[:5]:
        rscore = float(region.get("score", region.get("risk_score", 0)))
        if rscore >= 40:
            norm = rscore / 100.0
            issues.append(_issue(
                "tampered_paragraph", _severity(norm), norm,
                "; ".join(region.get("reasons", ["Regional forensic anomaly detected."])),
                bbox=region.get("bbox"),
            ))

    combined = max(parse_score, layout_score * 0.8)
    if combined >= 0.45 and not issues:
        issues.append(_issue(
            "tampered_paragraph", _severity(combined), combined,
            "Donut/LayoutLMv3 detected structural parsing inconsistency — possible paragraph tampering.",
        ))
    return issues


def compute_page_confidence(issues: List[Dict[str, Any]]) -> float:
    if not issues:
        return 0.95
    weighted = sum(
        float(i.get("score", 0)) * ISSUE_WEIGHTS.get(i.get("type", ""), 0.1)
        for i in issues
    )
    authenticity = max(0.0, 1.0 - min(1.0, weighted * 2.5))
    return round(authenticity, 4)


def analyze_page_intelligence(
    image_path: str,
    ocr_result: Dict[str, Any],
    risk_result: Dict[str, Any],
    analysis_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Run full document intelligence pipeline on one page."""
    raw = risk_result.get("raw_analysis", {}) or {}
    layout_data = raw.get("layout", {}) or {}
    font_result = raw.get("font", {}) or {}
    spacing_result = raw.get("spacing", {}) or {}
    region_result = raw.get("regions", {}) or {}
    ocr_detections = ocr_result.get("detections", []) or []
    ocr_text = ocr_result.get("full_text") or ocr_result.get("text") or ""

    img = cv2.imread(str(image_path))
    shape = img.shape[:2] if img is not None else (1000, 800)

    layoutlm = analyze_layoutlmv3(image_path, ocr_detections)
    donut = analyze_donut(image_path, ocr_text)

    issues: List[Dict[str, Any]] = []
    issues.extend(detect_header_inconsistency(layout_data, layoutlm, shape))
    issues.extend(detect_signature_mismatch(image_path))
    issues.extend(detect_fake_stamps(image_path))
    issues.extend(detect_logo_manipulation(image_path, analysis_dir))
    issues.extend(detect_wrong_fonts(font_result))
    issues.extend(detect_spacing_anomalies(spacing_result))
    issues.extend(detect_tampered_paragraphs(region_result, donut, layoutlm))

    page_confidence = compute_page_confidence(issues)
    tamper_risk = round(1.0 - page_confidence, 4)

    return {
        "page_confidence": page_confidence,
        "tamper_risk": tamper_risk,
        "page_confidence_pct": round(page_confidence * 100, 2),
        "issues": issues,
        "issue_count": len(issues),
        "layoutlmv3": layoutlm,
        "donut": donut,
        "models": {
            "layoutlmv3": layoutlm.get("model", "layoutlmv3"),
            "donut": donut.get("model", "donut"),
        },
    }


def _extract_footer_page_numbers(text: str) -> List[int]:
    import re
    nums: List[int] = []
    patterns = [
        r"page\s+(\d+)\s+of\s+(\d+)",
        r"(\d+)\s*/\s*(\d+)",
        r"^\s*(\d+)\s*$",
        r"page\s+(\d+)",
    ]
    lower = (text or "").lower()
    for pat in patterns:
        for match in re.finditer(pat, lower, re.MULTILINE):
            groups = match.groups()
            if groups:
                try:
                    nums.append(int(groups[0]))
                except ValueError:
                    pass
    return nums


def detect_missing_pages(
    page_count: int,
    expected_count: Optional[int] = None,
    page_numbers: Optional[List[int]] = None,
    page_texts: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Detect gaps in page sequence or count mismatch."""
    page_numbers = page_numbers or list(range(1, page_count + 1))
    expected = expected_count or (max(page_numbers) if page_numbers else page_count)
    missing: List[int] = []

    if expected > page_count:
        present = set(page_numbers)
        for i in range(1, expected + 1):
            if i not in present:
                missing.append(i)

    # Footer / header page-number sequence gaps (e.g. Page 1, Page 2, Page 4)
    detected_nums: List[int] = []
    if page_texts:
        for text in page_texts:
            detected_nums.extend(_extract_footer_page_numbers(text[-400:] if text else ""))
        if detected_nums:
            max_declared = max(detected_nums)
            expected = max(expected, max_declared)
            present_footer = set(detected_nums)
            for i in range(1, max_declared + 1):
                if i not in present_footer and i not in missing:
                    missing.append(i)

    missing = sorted(set(missing))
    return {
        "expected_pages": expected,
        "rendered_pages": page_count,
        "missing_pages": missing,
        "missing_page_detected": len(missing) > 0,
        "confidence": 0.85 if missing else 0.95,
        "detected_page_numbers": sorted(set(detected_nums)) if detected_nums else [],
    }
