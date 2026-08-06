from __future__ import annotations

from pathlib import Path

from backend.analysis.image_forensics import (
    analyze_image
)

from backend.analysis.copy_move import (
    detect_copy_move
)

from backend.analysis.metadata_analysis import (
    analyze_metadata
)

from backend.analysis.noise_analysis import (
    analyze_noise
)

from backend.document_analysis.font_consistency import (
    analyze_font_consistency
)

from backend.document_analysis.spacing_analysis import (
    analyze_spacing
)

from backend.document_analysis.region_anomaly import (
    analyze_region_anomaly
)

from backend.document_analysis.evidence import (
    Evidence
)

from backend.document_analysis.evidence_fusion import (
    fuse_evidence
)

from backend.tampering.tampering_detector import (
    analyze_tampering
)

from backend.analysis.parallel_runner import run_parallel_modules
from backend.analysis.ensemble_scoring import compute_ensemble_risk
from backend.analysis.risk_fusion_engine import compute_fusion_risk
from backend.analysis.ai_generated_detector import detect_ai_generated_image
from backend.analysis.forensic_explanation import generate_forensic_explanation
from backend.utils.performance_config import DEFER_EXPLAINABILITY, IMAGE_PARALLEL_WORKERS
from backend.analysis.multispectral_runner import fuse_detector_results
from backend.analysis.detectors.rgb_analysis import analyze_rgb
from backend.analysis.detectors.hsv_analysis import analyze_hsv
from backend.analysis.detectors.lab_analysis import analyze_lab
from backend.analysis.detectors.ycbcr_analysis import analyze_ycbcr
from backend.analysis.detectors.frequency_analysis import analyze_frequency
from backend.analysis.detectors.jpeg_block_analysis import analyze_jpeg_blocks
from backend.analysis.face_forensics.engine import analyze_face_forensics
from backend.document_analysis.text_layout_analysis import analyze_text_layout
from backend.utils.artifact_paths import artifact_api_urls
from backend.utils.module_registry import classify_image_profile, likely_contains_text, modules_for_image
from backend.utils.timing import ModuleTimer, format_timing_dashboard
from backend.utils.analysis_dedup import dedup_context, get_dedup


# ============================================================
# SAFE FLOAT
# ============================================================

def safe_float(value, default=0.0):
    try:
        return float(value)

    except (
        TypeError,
        ValueError
    ):
        return default


# ============================================================
# SAFE INT
# ============================================================

def safe_int(value, default=0):
    try:
        return int(value)

    except (
        TypeError,
        ValueError
    ):
        return default


# ============================================================
# SAFE BOOL
# ============================================================

def safe_bool(value):
    if isinstance(
        value,
        bool
    ):
        return value

    if isinstance(
        value,
        str
    ):
        return value.lower() in [
            "true",
            "1",
            "yes",
            "detected"
        ]

    return bool(value)


# ============================================================
# NORMALIZE SCORE
# ============================================================

def normalize_score(
    value,
    maximum=1.0
):
    value = safe_float(
        value
    )

    if maximum <= 0:
        return 0.0

    score = value / maximum

    return max(
        0.0,
        min(
            1.0,
            score
        )
    )


# ============================================================
# ANALYZE IMAGE UNIFIED
# ============================================================

def analyze_image_unified(
    image_path,
    analysis_dir,
    progress: ProgressTracker | None = None,
    evidence_id: str | None = None,
):
    # ========================================================
    # PATHS
    # ========================================================

    image_path = Path(
        image_path
    )

    analysis_dir = Path(
        analysis_dir
    )

    # ========================================================
    # VALIDATE IMAGE
    # ========================================================

    if not image_path.exists():
        raise FileNotFoundError(
            f"Image not found: {image_path}"
        )

    # ========================================================
    # CREATE ANALYSIS DIRECTORY
    # ========================================================

    analysis_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    print()

    print(
        "=================================================="
    )

    print(
        "        AI-FORGE UNIFIED IMAGE ANALYSIS"
    )

    print(
        "=================================================="
    )

    print(
        f"Evidence: {image_path.name}"
    )

    print(
        f"Analysis Directory: {analysis_dir}"
    )

    print()

    timer = ModuleTimer("Unified Image Analysis")
    img_str = str(image_path)

    with dedup_context():
        return _run_unified_analysis(
            image_path, analysis_dir, progress, evidence_id,
            timer, img_str,
        )


def _run_unified_analysis(
    image_path: Path,
    analysis_dir: Path,
    progress: ProgressTracker | None,
    evidence_id: str | None,
    timer: ModuleTimer,
    img_str: str,
):
    dedup = get_dedup()
    ocr_applicable = likely_contains_text(img_str)
    profile = classify_image_profile(img_str)
    enabled = modules_for_image(image_path, ocr_applicable, profile)
    analysis_dir_str = str(analysis_dir)

    shared_layout = None
    if "font" in enabled or "spacing" in enabled or "region" in enabled:
        try:
            shared_layout = dedup.get_or_compute(
                "text_layout",
                lambda: analyze_text_layout(img_str, analysis_dir=analysis_dir_str),
            )
        except Exception:
            shared_layout = None

    def _font():
        return analyze_font_consistency(img_str, layout_data=shared_layout, analysis_dir=analysis_dir_str)

    def _spacing():
        return analyze_spacing(img_str, layout_data=shared_layout, analysis_dir=analysis_dir_str)

    def _region():
        return analyze_region_anomaly(img_str, layout_data=shared_layout, analysis_dir=analysis_dir_str)

    def _noop():
        return {}

    def _progress_cb(module: str, status: str, elapsed: float):
        if progress:
            progress.emit(module, status, elapsed=elapsed)

    print(f"[PARALLEL] Profile={profile} Modules={sorted(enabled)} OCR={ocr_applicable}")

    parallel_results = run_parallel_modules(
        {
            "forensics": lambda: analyze_image(img_str, analysis_dir_str, save_artifacts=False),
            "copy_move": lambda: detect_copy_move(img_str, analysis_dir),
            "metadata": lambda: analyze_metadata(img_str),
            "noise": lambda: analyze_noise(img_str),
            "rgb": lambda: analyze_rgb(img_str),
            "hsv": lambda: analyze_hsv(img_str),
            "lab": lambda: analyze_lab(img_str),
            "ycbcr": lambda: analyze_ycbcr(img_str),
            "frequency": lambda: analyze_frequency(img_str),
            "jpeg_block": lambda: analyze_jpeg_blocks(img_str),
            "ai_generation": lambda: detect_ai_generated_image(img_str),
            "face_forensics": lambda: analyze_face_forensics(img_str, analysis_dir_str, progress=_progress_cb),
            "font": _font if "font" in enabled else _noop,
            "spacing": _spacing if "spacing" in enabled else _noop,
            "region": _region if "region" in enabled else _noop,
            "tampering": lambda: analyze_tampering(img_str),
        },
        max_workers=IMAGE_PARALLEL_WORKERS,
        timer=timer,
        progress=_progress_cb,
        enabled_modules=enabled,
    )

    forensic_result = parallel_results.get("forensics") or {}
    copy_move_result = parallel_results.get("copy_move") or {}
    metadata_result = parallel_results.get("metadata") or {}
    noise_result = parallel_results.get("noise") or {}
    font_result = parallel_results.get("font") or {}
    spacing_result = parallel_results.get("spacing") or {}
    region_result = parallel_results.get("region") or {}
    tampering_result = parallel_results.get("tampering") or {}

    # Multi-spectral detector fusion
    spectral_results = {
        k: parallel_results.get(k) or {}
        for k in ("rgb", "hsv", "lab", "ycbcr", "frequency", "jpeg_block")
    }
    multispectral_fusion = fuse_detector_results(spectral_results)

    gan_result = parallel_results.get("ai_generation") or parallel_results.get("gan_detection") or {}
    gan_fusion = gan_result.get("fusion") or gan_result
    ai_generation = gan_result if gan_result.get("ai_generated_probability") is not None else {
        "ai_generated_probability": safe_float(gan_fusion.get("ai_generated_score", 0)),
        "human_photo_probability": 1.0 - safe_float(gan_fusion.get("ai_generated_score", 0)),
        "synthetic_artifact_confidence": safe_float(gan_fusion.get("ai_generated_score", 0)),
        "generator_prediction": gan_fusion.get("generator_prediction", "Unknown"),
        "reasoning": gan_fusion.get("reasoning", ""),
        "detectors": gan_result.get("detectors", {}),
    }
    face_result = parallel_results.get("face_forensics") or {}
    face_fusion = face_result.get("fusion") or {}

    if not tampering_result:
        tampering_result = {
            "success": False,
            "module": "tampering_detection",
            "verdict": "ANALYSIS_FAILED",
            "severity": "LOW",
            "tampering_score": 0.0,
            "tampering_percentage": 0.0,
            "confidence": 0.0,
            "signals": ["Tampering analysis returned no result."],
            "analysis": {},
        }

    # ========================================================
    # EXTRACT FORENSIC SIGNALS
    # ========================================================

    if not isinstance(forensic_result, dict):
        forensic_result = {}

    forensic_signals = forensic_result.get("signals", {}) or {}

    ela_score = safe_float(
        forensic_signals.get(
            "ela_score",
            0.0
        )
    )

    edge_density = safe_float(
        forensic_signals.get(
            "edge_density",
            0.0
        )
    )

    wavelet_score = safe_float(
        forensic_signals.get(
            "wavelet_score",
            0.0
        )
    )

    print(
        "    ELA Score:",
        ela_score
    )

    print(
        "    Edge Density:",
        edge_density
    )

    print(
        "    Wavelet Score:",
        wavelet_score
    )

    # ========================================================
    # EXTRACT PARALLEL MODULE RESULTS
    # ========================================================

    if not isinstance(copy_move_result, dict):
        copy_move_result = {}

    copy_move_detected = safe_bool(
        copy_move_result.get(
            "copy_move_detected",
            copy_move_result.get("detected", False),
        )
    )

    copy_move_score = safe_float(
        copy_move_result.get(
            "copy_move_score",
            copy_move_result.get("score", 0.0),
        )
    )

    matched_points = safe_int(
        copy_move_result.get(
            "matched_points",
            copy_move_result.get("matches", 0),
        )
    )

    ransac_inliers = safe_int(
        copy_move_result.get(
            "ransac_inliers",
            copy_move_result.get("inliers", 0),
        )
    )

    if not isinstance(metadata_result, dict):
        metadata_result = {}

    metadata_suspicious = safe_bool(metadata_result.get("suspicious", False))
    software_detected = safe_bool(metadata_result.get("software_detected", False))
    software = metadata_result.get("software", None)
    metadata_risk_score = safe_float(metadata_result.get("metadata_risk_score", 0.0))
    metadata_forensics = metadata_result if isinstance(metadata_result, dict) else {}

    if not isinstance(noise_result, dict):
        noise_result = {}

    noise_score = safe_float(noise_result.get("noise_score", 0.0))
    noise_inconsistency = safe_float(noise_result.get("noise_inconsistency", 0.0))

    if not isinstance(font_result, dict):
        font_result = {}

    suspicious_words = font_result.get("suspicious_words", [])
    if not isinstance(suspicious_words, list):
        suspicious_words = []

    font_anomaly_count = len(suspicious_words)

    if not isinstance(spacing_result, dict):
        spacing_result = {}

    spacing_risk = safe_float(spacing_result.get("risk_score", 0.0))

    if not isinstance(region_result, dict):
        region_result = {}

    high_risk_regions = region_result.get("high_risk_regions", [])
    if not isinstance(high_risk_regions, list):
        high_risk_regions = []

    region_anomaly_count = len(high_risk_regions)

    if not isinstance(tampering_result, dict):
        tampering_result = {}

    tampering_score = safe_float(
        tampering_result.get(
            "tampering_score",
            0.0
        )
    )

    tampering_score = max(
        0.0,
        min(
            1.0,
            tampering_score
        )
    )

    tampering_percentage = safe_float(
        tampering_result.get(
            "tampering_percentage",
            tampering_score * 100
        )
    )

    tampering_confidence = safe_float(
        tampering_result.get(
            "confidence",
            0.0
        )
    )

    tampering_verdict = str(
        tampering_result.get(
            "verdict",
            "UNKNOWN"
        )
    )

    tampering_severity = str(
        tampering_result.get(
            "severity",
            "LOW"
        )
    ).upper()

    tampering_signals = tampering_result.get(
        "signals",
        []
    )

    if not isinstance(
        tampering_signals,
        list
    ):
        tampering_signals = [
            str(tampering_signals)
        ]

    tampering_analysis = tampering_result.get(
        "analysis",
        {}
    )

    if not isinstance(
        tampering_analysis,
        dict
    ):
        tampering_analysis = {}

    print(
        "    Tampering Score:",
        tampering_score
    )

    print(
        "    Tampering Percentage:",
        tampering_percentage
    )

    print(
        "    Tampering Verdict:",
        tampering_verdict
    )

    print(
        "    Tampering Severity:",
        tampering_severity
    )

    print(
        "    Tampering Confidence:",
        tampering_confidence
    )

    print(
        "    Tampering Signals:",
        tampering_signals
    )

    # ========================================================
    # 8. EVIDENCE FUSION
    # ========================================================

    print()

    print(
        "[8/8] Fusing forensic evidence..."
    )

    evidence = []

    # ========================================================
    # ELA EVIDENCE
    # ========================================================

    evidence.append(
        Evidence(
            module="ELA",
            score=normalize_score(
                ela_score
            ),
            confidence=0.75,
            severity=(
                "High"
                if ela_score >= 0.60
                else "Medium"
                if ela_score >= 0.30
                else "Low"
            ),
            reason=(
                "Abnormal JPEG error-level "
                "analysis pattern detected."
                if ela_score >= 0.30
                else
                "ELA pattern appears relatively consistent."
            )
        )
    )

    # ========================================================
    # WAVELET EVIDENCE
    # ========================================================

    evidence.append(
        Evidence(
            module="Wavelet",
            score=normalize_score(
                wavelet_score
            ),
            confidence=0.75,
            severity=(
                "High"
                if wavelet_score >= 0.60
                else "Medium"
                if wavelet_score >= 0.30
                else "Low"
            ),
            reason=(
                "Wavelet-based texture anomaly detected."
                if wavelet_score >= 0.30
                else
                "Wavelet texture appears consistent."
            )
        )
    )

    # ========================================================
    # COPY-MOVE EVIDENCE
    # ========================================================

    evidence.append(
        Evidence(
            module="CopyMove",
            score=(
                1.0
                if copy_move_detected
                else normalize_score(
                    copy_move_score
                )
            ),
            confidence=(
                0.95
                if copy_move_detected
                else 0.70
            ),
            severity=(
                "Critical"
                if copy_move_detected
                else "Low"
            ),
            reason=(
                "Duplicated image content detected "
                "using copy-move analysis."
                if copy_move_detected
                else
                "No strong copy-move duplication detected."
            )
        )
    )

    # ========================================================
    # METADATA EVIDENCE
    # ========================================================

    evidence.append(
        Evidence(
            module="Metadata",
            score=max(
                metadata_risk_score,
                1.0 if metadata_suspicious else 0.0,
            ),
            confidence=0.85,
            severity=(
                "Critical" if metadata_risk_score >= 0.7
                else "High" if metadata_suspicious or metadata_risk_score >= 0.45
                else "Medium" if metadata_risk_score >= 0.25
                else "Low"
            ),
            reason=(
                metadata_forensics.get("forensic_report", {}).get("summary")
                or (
                    f"Potential image editing software metadata detected: {software}."
                    if metadata_suspicious
                    else "No suspicious editing software metadata detected."
                )
            )
        )
    )

    # ========================================================
    # NOISE EVIDENCE
    # ========================================================

    evidence.append(
        Evidence(
            module="Noise",
            score=normalize_score(
                noise_inconsistency,
                maximum=1.0
            ),
            confidence=0.65,
            severity=(
                "High"
                if noise_inconsistency >= 0.60
                else "Medium"
                if noise_inconsistency >= 0.30
                else "Low"
            ),
            reason=(
                "Inconsistent noise distribution detected."
                if noise_inconsistency >= 0.30
                else
                "Noise distribution appears relatively consistent."
            )
        )
    )

    # ========================================================
    # FONT EVIDENCE
    # ========================================================

    font_score = min(
        1.0,
        font_anomaly_count / 10
    )

    evidence.append(
        Evidence(
            module="Font",
            score=font_score,
            confidence=0.65,
            severity=(
                "High"
                if font_anomaly_count >= 5
                else "Medium"
                if font_anomaly_count >= 2
                else "Low"
            ),
            reason=(
                f"{font_anomaly_count} suspicious "
                f"font/text regions detected."
                if font_anomaly_count > 0
                else
                "No significant font inconsistency detected."
            )
        )
    )

    # ========================================================
    # SPACING EVIDENCE
    # ========================================================

    spacing_score = min(
        1.0,
        spacing_risk / 100
    )

    evidence.append(
        Evidence(
            module="Spacing",
            score=spacing_score,
            confidence=0.70,
            severity=(
                "High"
                if spacing_risk >= 70
                else "Medium"
                if spacing_risk >= 40
                else "Low"
            ),
            reason=(
                "Abnormal document text spacing or alignment detected."
                if spacing_risk >= 40
                else
                "Text spacing and alignment appear consistent."
            )
        )
    )

    # ========================================================
    # REGION EVIDENCE
    # ========================================================

    region_score = min(
        1.0,
        region_anomaly_count / 10
    )

    evidence.append(
        Evidence(
            module="Region",
            score=region_score,
            confidence=0.70,
            severity=(
                "High"
                if region_anomaly_count >= 5
                else "Medium"
                if region_anomaly_count >= 2
                else "Low"
            ),
            reason=(
                f"{region_anomaly_count} high-risk "
                f"regions identified."
                if region_anomaly_count > 0
                else
                "No significant high-risk regions identified."
            )
        )
    )

    # ========================================================
    # TAMPERING DETECTION EVIDENCE
    # ========================================================

    tampering_evidence_confidence = (
        tampering_confidence / 100
        if tampering_confidence > 1
        else tampering_confidence
    )

    tampering_evidence_confidence = max(
        0.0,
        min(
            1.0,
            tampering_evidence_confidence
        )
    )

    evidence.append(
        Evidence(
            module="TamperingDetection",
            score=tampering_score,
            confidence=tampering_evidence_confidence,
            severity=tampering_severity,
            reason=(
                " | ".join(
                    str(signal)
                    for signal in tampering_signals
                )
                if tampering_signals
                else
                f"Dedicated tampering analysis result: "
                f"{tampering_verdict}."
            )
        )
    )

    # ========================================================
    # FUSE EVIDENCE
    # ========================================================

    fusion_result = fuse_evidence(
        evidence
    )

    if not isinstance(
        fusion_result,
        dict
    ):
        fusion_result = {}

    risk_score = safe_float(
        fusion_result.get(
            "risk_score",
            0.0
        )
    )

    risk_score = max(
        0.0,
        min(
            100.0,
            risk_score
        )
    )

    findings = fusion_result.get(
        "findings",
        []
    )

    if not isinstance(
        findings,
        list
    ):
        findings = []

    # ========================================================
    # SIGNALS
    # ========================================================

    signals = {
        "ela_score": round(
            ela_score,
            4
        ),

        "edge_density": round(
            edge_density,
            4
        ),

        "wavelet_score": round(
            wavelet_score,
            4
        ),

        "copy_move_score": round(
            copy_move_score,
            4
        ),

        "copy_move_detected": copy_move_detected,

        "matched_points": matched_points,

        "ransac_inliers": ransac_inliers,

        "noise_score": round(
            noise_score,
            4
        ),

        "noise_inconsistency": round(
            noise_inconsistency,
            4
        ),

        "metadata_suspicious": metadata_suspicious,

        "metadata_risk_score": round(metadata_risk_score, 4),

        "metadata_risk_pct": round(metadata_risk_score * 100, 2),

        "software_detected": software_detected,

        "software": software,

        "fake_metadata_detected": safe_bool(metadata_result.get("fake_metadata_detected", False)),

        "edited_metadata_detected": safe_bool(metadata_result.get("edited_metadata_detected", False)),

        "removed_metadata_detected": safe_bool(metadata_result.get("removed_metadata_detected", False)),

        "font_anomaly_count": font_anomaly_count,

        "spacing_risk": round(
            spacing_risk,
            2
        ),

        "region_anomaly_count": region_anomaly_count,

        # ----------------------------------------------------
        # DEDICATED TAMPERING SIGNALS
        # ----------------------------------------------------

        "tampering_score": round(
            tampering_score,
            4
        ),

        "tampering_percentage": round(
            tampering_percentage,
            2
        ),

        "tampering_verdict": tampering_verdict,

        "tampering_severity": tampering_severity,

        "tampering_confidence": round(
            tampering_confidence,
            2
        ),

        "tampering_signals": tampering_signals,

        "multispectral_score": multispectral_fusion.get("overall_score", 0),
        "rgb_score": safe_float((spectral_results.get("rgb") or {}).get("score", 0)),
        "hsv_score": safe_float((spectral_results.get("hsv") or {}).get("score", 0)),
        "lab_score": safe_float((spectral_results.get("lab") or {}).get("score", 0)),
        "ycbcr_score": safe_float((spectral_results.get("ycbcr") or {}).get("score", 0)),
        "frequency_score": safe_float((spectral_results.get("frequency") or {}).get("score", 0)),
        "jpeg_block_score": safe_float((spectral_results.get("jpeg_block") or {}).get("score", 0)),

        "gan_ai_score": safe_float(gan_fusion.get("ai_generated_score", gan_result.get("ai_generated_score", 0))),
        "generator_prediction": gan_fusion.get("generator_prediction", gan_result.get("generator_prediction", "Unknown")),
        "deepfake_probability": safe_float(face_fusion.get("deepfake_probability", face_result.get("deepfake_probability", 0))),
        "face_authenticity_score": safe_float(face_fusion.get("face_authenticity_score", face_result.get("face_authenticity_score", 1.0))),
    }

    # ========================================================
    # WEIGHTED FUSION RISK ENGINE
    # ========================================================

    ocr_risk = max(spacing_risk / 100.0 if spacing_risk > 1 else spacing_risk, font_anomaly_count * 0.08)
    doc_consistency = max(
        spacing_risk / 100.0 if spacing_risk > 1 else spacing_risk,
        region_anomaly_count * 0.1,
        font_anomaly_count * 0.06,
    )

    fusion = compute_fusion_risk(
        {
            **signals,
            "metadata_score": max(metadata_risk_score, 1.0 if metadata_suspicious else 0.0),
            "matched_points": matched_points,
            "ransac_inliers": ransac_inliers,
        },
        profile=profile,
        ai_generation=ai_generation,
        tampering_score=tampering_score,
        deepfake_probability=float(face_fusion.get("deepfake_probability", face_result.get("deepfake_probability", 0))),
        face_authenticity_score=float(face_fusion.get("face_authenticity_score", face_result.get("face_authenticity_score", 1.0))),
        ocr_risk=ocr_risk,
        document_consistency=doc_consistency,
        multispectral_score=float(multispectral_fusion.get("overall_score", 0)),
    )

    ensemble = compute_ensemble_risk(
        {
            **signals,
            "metadata_score": max(metadata_risk_score, 1.0 if metadata_suspicious else 0.0),
        },
        profile=profile,
        tampering_score=tampering_score,
        noise_inconsistency=noise_inconsistency,
        multispectral_score=float(multispectral_fusion.get("overall_score", 0)),
        multispectral_confidence=float(multispectral_fusion.get("confidence", 0)),
        gan_ai_score=float(ai_generation.get("ai_generated_probability", gan_fusion.get("ai_generated_score", 0))),
        gan_confidence=float(ai_generation.get("confidence", gan_fusion.get("confidence", 0))),
        deepfake_probability=float(face_fusion.get("deepfake_probability", face_result.get("deepfake_probability", 0))),
        face_authenticity_score=float(face_fusion.get("face_authenticity_score", face_result.get("face_authenticity_score", 1.0))),
    )

    risk_score = fusion["overall_fraud_risk"]
    verdict = fusion["verdict"]
    confidence = fusion["confidence"]
    explanation_parts = fusion.get("explainability", [])
    explanation = " ".join(explanation_parts[:4]) if explanation_parts else generate_forensic_explanation(verdict, signals, findings)
    if multispectral_fusion.get("reasoning"):
        explanation = f"{explanation} {multispectral_fusion['reasoning']}"
    if gan_fusion.get("reasoning") or gan_result.get("reasoning"):
        explanation = f"{explanation} {gan_fusion.get('reasoning') or gan_result.get('reasoning', '')}"
    if face_fusion.get("reasoning") or face_result.get("reasoning"):
        explanation = f"{explanation} {face_fusion.get('reasoning') or face_result.get('reasoning', '')}"

    if risk_score >= 70:
        recommendation = (
            "Strong forensic indicators of image manipulation detected. "
            "Manual forensic verification is strongly recommended."
        )
    elif risk_score >= 45:
        recommendation = "Multiple suspicious signals detected. The evidence should be manually reviewed."
    elif risk_score >= 20:
        recommendation = (
            "Some weak forensic anomalies were detected, but insufficient to confirm manipulation."
        )
    else:
        recommendation = (
            "No strong forensic evidence of manipulation was detected by the available analysis modules."
        )

    active_modules = sum(1 for ev in evidence if safe_float(ev.score) > 0.20)
    if confidence < 55:
        confidence = min(99.9, round(55 + min(40, active_modules * 5) + (3 if risk_score >= 70 else 0), 2))

    # ========================================================
    # EXPLAINABILITY — GradCAM, SHAP, LIME, Attention, Report
    # ========================================================

    evidence_dicts = [
        {
            "module": ev.module,
            "score": safe_float(ev.score),
            "confidence": safe_float(ev.confidence),
            "severity": str(ev.severity),
            "reason": str(ev.reason),
            "location": ev.location,
        }
        for ev in evidence
    ]

    explainability_result: Dict[str, Any] = {}
    if DEFER_EXPLAINABILITY:
        explainability_result = {
            "success": True,
            "deferred": True,
            "pending": True,
            "message": "Explainability scheduled in background for faster response.",
        }
    else:
        from backend.analysis.explainability.engine import run_explainability
        try:
            with timer.track("explainability"):
                if progress:
                    progress.emit("explainability", "running")
                explainability_result = run_explainability(
                    str(image_path),
                    str(analysis_dir),
                    context={
                        "verdict": verdict,
                        "risk_score": risk_score,
                        "confidence": confidence,
                        "signals": signals,
                        "evidence": evidence_dicts,
                    },
                    tampering_result=tampering_result,
                )
                if progress:
                    progress.emit("explainability", "completed")
        except Exception as exc:
            explainability_result = {"success": False, "error": str(exc)}

    if not DEFER_EXPLAINABILITY and explainability_result.get("ai_explanation"):
        explanation = explainability_result["ai_explanation"].replace("**", "")
    elif explainability_result.get("human_readable_report"):
        report_lines = explainability_result["human_readable_report"].split("\n")
        explanation = " ".join(report_lines[:6])

    # ========================================================
    # ARTIFACT PATHS
    # ========================================================

    eid = evidence_id or image_path.stem
    artifacts = artifact_api_urls(eid)

    # ========================================================
    # FINAL RESULT
    # ========================================================

    timing_summary = timer.log_summary()

    result = {
        "evidence_id": eid,

        "verdict": verdict,

        "forensic_score": round(
            risk_score / 100,
            4
        ),

        "risk_score": round(
            risk_score,
            2
        ),

        "confidence": confidence,

        "recommendation": recommendation,

        "explanation": explanation,

        "ensemble": ensemble,
        "risk_fusion": fusion,
        "ai_generation": ai_generation,

        "multispectral": {
            "fusion": multispectral_fusion,
            "detectors": spectral_results,
        },

        "gan_detection": gan_result,
        "face_forensics": face_result,
        "metadata_forensics": metadata_forensics,
        "explainability": explainability_result,
        "explainability_pending": bool(DEFER_EXPLAINABILITY),

        "signals": signals,

        "findings": findings,

        # ----------------------------------------------------
        # DEDICATED TAMPERING RESULT
        # ----------------------------------------------------

        "tampering_detection": {
            "success": tampering_result.get(
                "success",
                False
            ),

            "verdict": tampering_verdict,

            "severity": tampering_severity,

            "tampering_score": round(
                tampering_score,
                4
            ),

            "tampering_percentage": round(
                tampering_percentage,
                2
            ),

            "confidence": round(
                tampering_confidence,
                2
            ),

            "signals": tampering_signals,

            "analysis": tampering_analysis
        },

        # ----------------------------------------------------
        # ALL EVIDENCE MODULES
        # ----------------------------------------------------

        "evidence": [
            {
                "module": ev.module,

                "score": round(
                    safe_float(
                        ev.score
                    ),
                    4
                ),

                "confidence": round(
                    safe_float(
                        ev.confidence
                    ),
                    4
                ),

                "severity": str(
                    ev.severity
                ),

                "reason": str(
                    ev.reason
                ),

                "location": ev.location
            }

            for ev in evidence
        ],

        "artifacts": artifacts,
        "profile": profile,
        "timing": timing_summary,
        "timing_dashboard": format_timing_dashboard(timing_summary),
    }

    # ========================================================
    # DEBUG OUTPUT
    # ========================================================

    print()

    print(
        "=================================================="
    )

    print(
        "          FINAL IMAGE FORENSIC RESULT"
    )

    print(
        "=================================================="
    )

    print(
        "Evidence ID:",
        evidence_id
    )

    print(
        "Risk Score:",
        f"{risk_score}%"
    )

    print(
        "Verdict:",
        verdict
    )

    print(
        "Confidence:",
        f"{confidence}%"
    )

    print()

    print(
        "Dedicated Tampering Score:",
        f"{tampering_score * 100:.2f}%"
    )

    print(
        "Dedicated Tampering Verdict:",
        tampering_verdict
    )

    print()

    print(
        "Active Evidence Modules:",
        active_modules
    )

    print()

    print(
        "Findings:"
    )

    for finding in findings:
        print(
            " -",
            finding
        )

    print()

    print(
        "=================================================="
    )

    if progress:
        progress.emit("fusion", "completed")

    return result