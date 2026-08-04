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
    analysis_dir
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

    # ========================================================
    # 1. IMAGE FORENSICS
    # ========================================================

    print(
        "[1/8] Running ELA / Edge / Wavelet analysis..."
    )

    forensic_result = analyze_image(
        str(image_path),
        str(analysis_dir)
    )

    if not isinstance(
        forensic_result,
        dict
    ):
        forensic_result = {}

    forensic_signals = forensic_result.get(
        "signals",
        {}
    )

    if not isinstance(
        forensic_signals,
        dict
    ):
        forensic_signals = {}

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
    # 2. COPY-MOVE DETECTION
    # ========================================================

    print()

    print(
        "[2/8] Running copy-move detection..."
    )

    copy_move_result = detect_copy_move(
        str(image_path),
        analysis_dir
    )

    if not isinstance(
        copy_move_result,
        dict
    ):
        copy_move_result = {}

    copy_move_detected = safe_bool(
        copy_move_result.get(
            "copy_move_detected",
            copy_move_result.get(
                "detected",
                False
            )
        )
    )

    copy_move_score = safe_float(
        copy_move_result.get(
            "copy_move_score",
            copy_move_result.get(
                "score",
                0.0
            )
        )
    )

    matched_points = safe_int(
        copy_move_result.get(
            "matched_points",
            copy_move_result.get(
                "matches",
                0
            )
        )
    )

    ransac_inliers = safe_int(
        copy_move_result.get(
            "ransac_inliers",
            copy_move_result.get(
                "inliers",
                0
            )
        )
    )

    print(
        "    Copy-Move Detected:",
        copy_move_detected
    )

    print(
        "    Copy-Move Score:",
        copy_move_score
    )

    print(
        "    Matched Points:",
        matched_points
    )

    print(
        "    RANSAC Inliers:",
        ransac_inliers
    )

    # ========================================================
    # 3. METADATA ANALYSIS
    # ========================================================

    print()

    print(
        "[3/8] Running metadata analysis..."
    )

    metadata_result = analyze_metadata(
        str(image_path)
    )

    if not isinstance(
        metadata_result,
        dict
    ):
        metadata_result = {}

    metadata_suspicious = safe_bool(
        metadata_result.get(
            "suspicious",
            False
        )
    )

    software_detected = safe_bool(
        metadata_result.get(
            "software_detected",
            False
        )
    )

    software = metadata_result.get(
        "software",
        None
    )

    print(
        "    Metadata Suspicious:",
        metadata_suspicious
    )

    print(
        "    Software:",
        software
    )

    # ========================================================
    # 4. NOISE ANALYSIS
    # ========================================================

    print()

    print(
        "[4/8] Running noise consistency analysis..."
    )

    noise_result = analyze_noise(
        str(image_path)
    )

    if not isinstance(
        noise_result,
        dict
    ):
        noise_result = {}

    noise_score = safe_float(
        noise_result.get(
            "noise_score",
            0.0
        )
    )

    noise_inconsistency = safe_float(
        noise_result.get(
            "noise_inconsistency",
            0.0
        )
    )

    print(
        "    Noise Score:",
        noise_score
    )

    print(
        "    Noise Inconsistency:",
        noise_inconsistency
    )

    # ========================================================
    # 5. FONT CONSISTENCY
    # ========================================================

    print()

    print(
        "[5/8] Running font consistency analysis..."
    )

    font_result = analyze_font_consistency(
        str(image_path)
    )

    if not isinstance(
        font_result,
        dict
    ):
        font_result = {}

    suspicious_words = font_result.get(
        "suspicious_words",
        []
    )

    if not isinstance(
        suspicious_words,
        list
    ):
        suspicious_words = []

    font_anomaly_count = len(
        suspicious_words
    )

    print(
        "    Suspicious Font Regions:",
        font_anomaly_count
    )

    # ========================================================
    # 6. SPACING + REGION ANALYSIS
    # ========================================================

    print()

    print(
        "[6/8] Running layout and region analysis..."
    )

    spacing_result = analyze_spacing(
        str(image_path)
    )

    if not isinstance(
        spacing_result,
        dict
    ):
        spacing_result = {}

    spacing_risk = safe_float(
        spacing_result.get(
            "risk_score",
            0.0
        )
    )

    region_result = analyze_region_anomaly(
        str(image_path)
    )

    if not isinstance(
        region_result,
        dict
    ):
        region_result = {}

    high_risk_regions = region_result.get(
        "high_risk_regions",
        []
    )

    if not isinstance(
        high_risk_regions,
        list
    ):
        high_risk_regions = []

    region_anomaly_count = len(
        high_risk_regions
    )

    print(
        "    Spacing Risk:",
        spacing_risk
    )

    print(
        "    High Risk Regions:",
        region_anomaly_count
    )

    # ========================================================
    # 7. DEDICATED TAMPERING ANALYSIS
    # ========================================================

    print()

    print(
        "[7/8] Running dedicated tampering analysis..."
    )

    try:
        tampering_result = analyze_tampering(
            str(image_path)
        )

    except Exception as exc:
        print(
            "    Tampering analysis failed:",
            exc
        )

        tampering_result = {
            "success": False,
            "module": "tampering_detection",
            "verdict": "ANALYSIS_FAILED",
            "severity": "LOW",
            "tampering_score": 0.0,
            "tampering_percentage": 0.0,
            "confidence": 0.0,
            "signals": [
                f"Tampering analysis failed: {str(exc)}"
            ],
            "analysis": {}
        }

    if not isinstance(
        tampering_result,
        dict
    ):
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
            score=(
                1.0
                if metadata_suspicious
                else 0.0
            ),
            confidence=0.80,
            severity=(
                "High"
                if metadata_suspicious
                else "Low"
            ),
            reason=(
                f"Potential image editing software "
                f"metadata detected: {software}."
                if metadata_suspicious
                else
                "No suspicious editing software metadata detected."
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
    # FINAL VERDICT
    # ========================================================

    if risk_score >= 70:
        verdict = (
            "HIGH RISK - LIKELY FORGED"
        )

        recommendation = (
            "Strong forensic indicators of image "
            "manipulation detected. Manual forensic "
            "verification is strongly recommended."
        )

    elif risk_score >= 45:
        verdict = (
            "MEDIUM RISK - SUSPICIOUS"
        )

        recommendation = (
            "Multiple suspicious signals detected. "
            "The evidence should be manually reviewed."
        )

    elif risk_score >= 20:
        verdict = (
            "LOW RISK - MINOR ANOMALIES"
        )

        recommendation = (
            "Some weak forensic anomalies were detected, "
            "but the available evidence is not sufficient "
            "to confirm manipulation."
        )

    else:
        verdict = (
            "NO SIGNIFICANT ANOMALY DETECTED"
        )

        recommendation = (
            "No strong forensic evidence of manipulation "
            "was detected by the available analysis modules."
        )

    # ========================================================
    # CONFIDENCE
    # ========================================================

    active_modules = sum(
        1
        for ev in evidence
        if safe_float(
            ev.score
        ) > 0.20
    )

    confidence = (
        55
        + min(
            40,
            active_modules * 5
        )
    )

    if risk_score >= 70:
        confidence += 3

    confidence = min(
        99.9,
        round(
            confidence,
            2
        )
    )

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

        "software_detected": software_detected,

        "software": software,

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

        "tampering_signals": tampering_signals
    }

    # ========================================================
    # ARTIFACT PATHS
    # ========================================================

    evidence_id = image_path.stem

    artifacts = {
        "ela": (
            f"/api/evidence/artifacts/"
            f"{evidence_id}/ela"
        ),

        "edges": (
            f"/api/evidence/artifacts/"
            f"{evidence_id}/edges"
        ),

        "wavelet": (
            f"/api/evidence/artifacts/"
            f"{evidence_id}/wavelet"
        ),

        "copy_move": (
            f"/api/evidence/artifacts/"
            f"{evidence_id}/copy_move"
        )
    }

    # ========================================================
    # FINAL RESULT
    # ========================================================

    result = {
        "evidence_id": evidence_id,

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

        "artifacts": artifacts
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

    return result