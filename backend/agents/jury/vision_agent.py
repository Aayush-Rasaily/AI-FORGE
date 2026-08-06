"""
Vision Agent — synthesizes ELA, Copy-Move, Wavelet, Edge, and OCR signals
from the unified forensic analysis pipeline.
"""

from typing import Any, Dict, List, Optional

from backend.agents.jury.utils import (
    build_finding,
    clamp,
    safe_float,
    verdict_from_score,
)


def run_vision_agent(
    analysis: Optional[Dict[str, Any]] = None,
    tampering: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    analysis = analysis or {}
    tampering = tampering or {}
    signals = analysis.get("signals") or {}
    tampering_analysis = tampering.get("analysis") or {}

    findings: List[Dict[str, Any]] = []
    scores: Dict[str, float] = {}

    # ELA
    ela_score = safe_float(signals.get("ela_score", 0))
    if ela_score > 0:
        scores["ela"] = ela_score
        if ela_score >= 0.5:
            findings.append(build_finding(
                "ela",
                "High JPEG compression inconsistency detected around object boundaries.",
                "Error Level Analysis shows regions with abnormal recompression artifacts, "
                "which often appear when image content has been inserted or altered.",
                ela_score,
            ))
        elif ela_score >= 0.25:
            findings.append(build_finding(
                "ela",
                "Moderate compression level inconsistencies observed.",
                "ELA detected uneven error levels that may indicate localized editing.",
                ela_score,
            ))

    # Copy-Move
    copy_score = safe_float(signals.get("copy_move_score", 0))
    copy_detected = bool(signals.get("copy_move_detected", False))
    if copy_score > 0 or copy_detected:
        scores["copy_move"] = max(copy_score, 0.7 if copy_detected else 0)
        if copy_detected or copy_score >= 0.4:
            matched = signals.get("matched_points", 0)
            findings.append(build_finding(
                "copy_move",
                "Copy-move detector found duplicated regions within the image.",
                f"ORB feature matching identified {matched} matched point(s) with RANSAC "
                "inliers suggesting cloned content.",
                max(copy_score, 0.75 if copy_detected else copy_score),
            ))

    # Wavelet
    wavelet_score = safe_float(signals.get("wavelet_score", 0))
    if wavelet_score > 0:
        scores["wavelet"] = wavelet_score
        if wavelet_score >= 0.4:
            findings.append(build_finding(
                "wavelet",
                "Wavelet artifacts indicate localized editing in high-frequency bands.",
                "Multi-resolution wavelet decomposition revealed anomalous energy "
                "distribution inconsistent with a single-capture photograph.",
                wavelet_score,
            ))

    # Edge
    edge_density = safe_float(signals.get("edge_density", 0))
    if edge_density > 0:
        scores["edge"] = edge_density
        if edge_density >= 0.5:
            findings.append(build_finding(
                "edge",
                "Edge density anomalies detected at structural boundaries.",
                "Inconsistent edge patterns suggest possible splicing or object insertion.",
                edge_density,
            ))

    # OCR text from tampering pipeline (if available)
    ocr_data = tampering_analysis.get("ocr") or {}
    if ocr_data.get("text_detected"):
        scores["ocr"] = safe_float(ocr_data.get("confidence", 0.5))
        findings.append(build_finding(
            "ocr",
            f"OCR extracted {ocr_data.get('word_count', 0)} text region(s) from the image.",
            "Embedded text was analyzed for consistency with surrounding forensic signals.",
            scores["ocr"],
        ))

    # Compute aggregate risk
    if scores:
        risk_score = sum(scores.values()) / len(scores)
    else:
        risk_score = safe_float(analysis.get("forensic_score", 0))

    risk_score = clamp(risk_score)
    verdict = verdict_from_score(risk_score)

    if not findings:
        findings.append(build_finding(
            "vision",
            "No strong visual manipulation indicators detected.",
            "ELA, wavelet, copy-move, and edge modules did not flag significant anomalies.",
            1.0 - risk_score,
        ))

    explanation_parts = [f["what"] for f in findings[:4]]
    explanation = " ".join(explanation_parts)

    return {
        "agent_id": "vision",
        "agent_name": "Vision Agent",
        "verdict": verdict,
        "confidence": round(clamp(max(scores.values()) if scores else 1 - risk_score), 4),
        "risk_score": round(risk_score, 4),
        "findings": findings,
        "explanation": explanation,
        "signals": [f["what"] for f in findings],
        "raw_scores": {k: round(v, 4) for k, v in scores.items()},
        "vote": "risk" if risk_score >= 0.45 else "authentic",
    }
