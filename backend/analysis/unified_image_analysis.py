from pathlib import Path

from backend.analysis.image_forensics import (
    analyze_image
)

from backend.analysis.copy_move import (
    detect_copy_move
)


def analyze_image_unified(
    image_path,
    analysis_dir
):

    # -----------------------------------------
    # Convert paths
    # -----------------------------------------

    image_path = Path(
        image_path
    )

    analysis_dir = Path(
        analysis_dir
    )

    # -----------------------------------------
    # Validate image
    # -----------------------------------------

    if not image_path.exists():

        raise FileNotFoundError(
            f"Image not found: {image_path}"
        )

    # -----------------------------------------
    # Create analysis directory
    # -----------------------------------------

    analysis_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # -----------------------------------------
    # Run ELA / Edge / Wavelet
    # -----------------------------------------

    forensic_result = analyze_image(
        str(image_path),
        str(analysis_dir)
    )

    # -----------------------------------------
    # Run Copy-Move
    # -----------------------------------------

    copy_move_result = detect_copy_move(
        str(image_path),
        output_dir=analysis_dir
    )

    # -----------------------------------------
    # Safety checks
    # -----------------------------------------

    if not isinstance(
        forensic_result,
        dict
    ):
        forensic_result = {}

    if not isinstance(
        copy_move_result,
        dict
    ):
        copy_move_result = {}

    # -----------------------------------------
    # Get forensic signals
    # -----------------------------------------

    forensic_signals = forensic_result.get(
        "signals",
        {}
    )

    if not isinstance(
        forensic_signals,
        dict
    ):
        forensic_signals = {}

    # -----------------------------------------
    # Extract signals
    # -----------------------------------------

    ela_score = float(
        forensic_signals.get(
            "ela_score",
            0.0
        )
    )

    edge_density = float(
        forensic_signals.get(
            "edge_density",
            0.0
        )
    )

    wavelet_score = float(
        forensic_signals.get(
            "wavelet_score",
            0.0
        )
    )

    copy_move_score = float(
        copy_move_result.get(
            "copy_move_score",
            copy_move_result.get(
                "score",
                0.0
            )
        )
    )

    copy_move_detected = bool(
        copy_move_result.get(
            "copy_move_detected",
            copy_move_result.get(
                "detected",
                False
            )
        )
    )

    matched_points = int(
        copy_move_result.get(
            "matched_points",
            copy_move_result.get(
                "matches",
                0
            )
        )
    )

    ransac_inliers = int(
        copy_move_result.get(
            "ransac_inliers",
            copy_move_result.get(
                "inliers",
                0
            )
        )
    )

    # -----------------------------------------
    # Combined Signals
    # -----------------------------------------

    signals = {

        "ela_score":
            round(
                ela_score,
                4
            ),

        "edge_density":
            round(
                edge_density,
                4
            ),

        "wavelet_score":
            round(
                wavelet_score,
                4
            ),

        "copy_move_score":
            round(
                copy_move_score,
                4
            ),

        "copy_move_detected":
            copy_move_detected,

        "matched_points":
            matched_points,

        "ransac_inliers":
            ransac_inliers

    }

    # -----------------------------------------
    # Unified Forensic Score
    # -----------------------------------------

    forensic_score = (

        0.30 * ela_score

        +

        0.20 * wavelet_score

        +

        0.20 * edge_density

        +

        0.30 * copy_move_score

    )

    forensic_score = round(
        float(
            forensic_score
        ),
        4
    )

    # -----------------------------------------
    # Determine Verdict
    # -----------------------------------------

    if copy_move_detected:

        verdict = (
            "Potential Forgery"
        )

    elif forensic_score >= 0.60:

        verdict = (
            "Likely Forged"
        )

    elif forensic_score >= 0.30:

        verdict = (
            "Suspicious"
        )

    else:

        verdict = (
            "Authentic"
        )

    # -----------------------------------------
    # Evidence ID
    # -----------------------------------------

    evidence_id = (
        image_path.stem
    )

    # -----------------------------------------
    # Artifact API Paths
    # -----------------------------------------

    artifacts = {

        "ela":
            f"/api/evidence/artifacts/"
            f"{evidence_id}/ela",

        "edges":
            f"/api/evidence/artifacts/"
            f"{evidence_id}/edges",

        "wavelet":
            f"/api/evidence/artifacts/"
            f"{evidence_id}/wavelet",

        "copy_move":
            f"/api/evidence/artifacts/"
            f"{evidence_id}/copy_move"

    }

    # -----------------------------------------
    # Final Result
    # -----------------------------------------

    result = {

        "verdict":
            verdict,

        "forensic_score":
            forensic_score,

        "signals":
            signals,

        "artifacts":
            artifacts

    }

    # -----------------------------------------
    # Debug
    # -----------------------------------------

    print(
        "\n========== IMAGE FORENSIC RESULT =========="
    )

    print(
        "Image:",
        image_path
    )

    print(
        "Analysis Directory:",
        analysis_dir
    )

    print(
        "Verdict:",
        verdict
    )

    print(
        "Forensic Score:",
        forensic_score
    )

    print(
        "Signals:",
        signals
    )

    print(
        "Artifacts:",
        artifacts
    )

    print(
        "============================================\n"
    )

    return result