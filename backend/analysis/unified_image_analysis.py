from pathlib import Path
from unittest import result

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
    # Create analysis directory
    # -----------------------------------------

    analysis_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # -----------------------------------------
    # Run ELA / Edge / Wavelet Analysis
    # -----------------------------------------

    forensic_result = analyze_image(
        str(image_path)
    )

    # -----------------------------------------
    # Run Copy-Move Detection
    # -----------------------------------------

    copy_move_result = detect_copy_move(
        str(image_path),
        output_dir=analysis_dir
    )

    # -----------------------------------------
    # Safety check
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
    # Extract ELA score
    # -----------------------------------------

    ela_score = float(
        forensic_signals.get(
            "ela_score",
            0.0
        )
    )

    # -----------------------------------------
    # Extract Edge Density
    # -----------------------------------------

    edge_density = float(
        forensic_signals.get(
            "edge_density",
            0.0
        )
    )

    # -----------------------------------------
    # Extract Wavelet Score
    # -----------------------------------------

    wavelet_score = float(
        forensic_signals.get(
            "wavelet_score",
            0.0
        )
    )

    # -----------------------------------------
    # Extract Copy-Move Score
    #
    # Supports both:
    #
    # "copy_move_score"
    #
    # and older:
    #
    # "score"
    # -----------------------------------------

    copy_move_score = float(
        copy_move_result.get(
            "copy_move_score",
            copy_move_result.get(
                "score",
                0.0
            )
        )
    )

    # -----------------------------------------
    # Extract Copy-Move Detection Status
    # -----------------------------------------

    copy_move_detected = bool(
        copy_move_result.get(
            "copy_move_detected",
            copy_move_result.get(
                "detected",
                False
            )
        )
    )

    # -----------------------------------------
    # Extract Matched Points
    # -----------------------------------------

    matched_points = int(
        copy_move_result.get(
            "matched_points",
            copy_move_result.get(
                "matches",
                0
            )
        )
    )

    # -----------------------------------------
    # Extract RANSAC Inliers
    # -----------------------------------------

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
        "ela_score": forensic_signals.get(
            "ela_score",
            0
        ),

        "edge_density": forensic_signals.get(
            "edge_density",
            0
        ),

        "wavelet_score": forensic_signals.get(
            "wavelet_score",
            0
        ),

        "copy_move_score": copy_move_result.get(
            "copy_move_score",
            copy_move_result.get(
                "score",
                0
            )
        ),

        "copy_move_detected": copy_move_result.get(
            "copy_move_detected",
            False
        ),

        "matched_points": copy_move_result.get(
            "matched_points",
            0
        ),

        "ransac_inliers": copy_move_result.get(
            "inliers",
            0
        )
    }

    

    # -----------------------------------------
    # Calculate Unified Forensic Score
    #
    # Currently using:
    #
    # ELA
    # Wavelet
    # Copy-Move
    #
    # Edge density is reported as a signal
    # but is not currently included in the
    # overall score.
    # -----------------------------------------

    forensic_score = (

        signals[
            "ela_score"
        ]

        +

        signals[
            "wavelet_score"
        ]

        +

        signals[
            "copy_move_score"
        ]

    ) / 3

    forensic_score = round(
        float(
            forensic_score
        ),
        4
    )

    # -----------------------------------------
    # Determine Final Verdict
    # -----------------------------------------

    if (
        signals[
            "copy_move_detected"
        ]
    ):

        verdict = (
            "Potential Forgery"
        )

    elif (
        forensic_score >= 0.5
    ):

        verdict = (
            "Potential Forgery"
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
    # Final Unified Result
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
    # Debug Output
    # -----------------------------------------

    print(
        "\n========== IMAGE FORENSIC RESULT =========="
    )

    print(
        "Image:",
        image_path
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
        "Copy-Move Result:",
        copy_move_result
    )

    print(
        "Final Signals:",
        signals
    )

    print(
        "============================================\n"
    )

# -----------------------------------------
# Return Final Result
# -----------------------------------------

    return result
