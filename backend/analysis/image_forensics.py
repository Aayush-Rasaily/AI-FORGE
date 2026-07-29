from pathlib import Path

from backend.analysis.ela import (
    generate_ela,
    calculate_ela_score
)

from backend.analysis.edge_detection import (
    analyze_edges
)

from backend.analysis.wavelet_analysis import (
    analyze_wavelet
)

from backend.analysis.copy_move import (
    detect_copy_move
)


def analyze_image(
    image_path: str
):

    image_path = Path(
        image_path
    )


    if not image_path.exists():

        raise FileNotFoundError(
            f"Image not found: {image_path}"
        )


    # --------------------------------
    # Create analysis directory
    # --------------------------------

    analysis_dir = (
        image_path.parent /
        "analysis"
    )


    analysis_dir.mkdir(
        exist_ok=True
    )


    # --------------------------------
    # Generate artifact paths
    # --------------------------------

    ela_path = (
        analysis_dir /
        f"{image_path.stem}_ela.jpg"
    )


    edge_path = (
        analysis_dir /
        f"{image_path.stem}_edges.jpg"
    )


    wavelet_path = (
        analysis_dir /
        f"{image_path.stem}_wavelet.jpg"
    )


    # --------------------------------
    # ELA
    # --------------------------------

    ela_image = generate_ela(

        str(image_path),

        str(ela_path)

    )


    ela_score = calculate_ela_score(
        ela_image
    )


    # --------------------------------
    # Edge Analysis
    # --------------------------------

    edge_result = analyze_edges(

        str(image_path),

        str(edge_path)

    )


    # --------------------------------
    # Wavelet Analysis
    # --------------------------------

    wavelet_result = analyze_wavelet(

        str(image_path),

        str(wavelet_path)

    )


    # --------------------------------
    # Copy-Move
    # --------------------------------

    copy_move_result = detect_copy_move(

        str(image_path)

    )


    # --------------------------------
    # Score Fusion
    # --------------------------------

    forensic_score = (

        0.30 * ela_score

        +

        0.20 *
        wavelet_result[
            "wavelet_score"
        ]

        +

        0.20 *
        edge_result[
            "edge_density"
        ]

        +

        0.30 *
        copy_move_result[
            "copy_move_score"
        ]

    )


    # --------------------------------
    # Verdict
    # --------------------------------

    if forensic_score < 0.30:

        verdict = "Authentic"


    elif forensic_score < 0.60:

        verdict = "Suspicious"


    else:

        verdict = "Likely Forged"


    # --------------------------------
    # Return Result
    # --------------------------------

    return {

        "verdict":
            verdict,


        "forensic_score":
            round(
                forensic_score,
                4
            ),


        "signals": {

            "ela_score":
                round(
                    ela_score,
                    4
                ),


            "edge_density":
                round(
                    edge_result[
                        "edge_density"
                    ],
                    4
                ),


            "wavelet_score":
                round(
                    wavelet_result[
                        "wavelet_score"
                    ],
                    4
                ),


            "copy_move_score":
                copy_move_result[
                    "copy_move_score"
                ],


            "copy_move_detected":
                copy_move_result[
                    "copy_move_detected"
                ]

        },


        "artifacts": {

            "ela":
                str(
                    ela_path
                ),


            "edges":
                str(
                    edge_path
                ),


            "wavelet":
                str(
                    wavelet_path
                )

        }

    }