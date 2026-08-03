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


def analyze_image(
    image_path: str,
    analysis_dir: str
):

    image_path = Path(
        image_path
    )

    analysis_dir = Path(
        analysis_dir
    )


    # ==========================================
    # VALIDATE IMAGE
    # ==========================================

    if not image_path.exists():

        raise FileNotFoundError(

            f"Image not found: {image_path}"

        )


    # ==========================================
    # CREATE ANALYSIS DIRECTORY
    # ==========================================

    analysis_dir.mkdir(

        parents=True,

        exist_ok=True

    )


    # ==========================================
    # ARTIFACT PATHS
    # ==========================================

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


    # ==========================================
    # ELA ANALYSIS
    # ==========================================

    ela_image = generate_ela(

        str(image_path),

        str(ela_path)

    )


    ela_score = calculate_ela_score(

        ela_image

    )


    # ==========================================
    # EDGE ANALYSIS
    # ==========================================

    edge_result = analyze_edges(

        str(image_path),

        str(edge_path)

    )


    if not isinstance(

        edge_result,

        dict

    ):

        edge_result = {}


    # ==========================================
    # WAVELET ANALYSIS
    # ==========================================

    wavelet_result = analyze_wavelet(

        str(image_path),

        str(wavelet_path)

    )


    if not isinstance(

        wavelet_result,

        dict

    ):

        wavelet_result = {}


    # ==========================================
    # EXTRACT VALUES
    # ==========================================

    edge_density = float(

        edge_result.get(

            "edge_density",

            0.0

        )

    )


    wavelet_score = float(

        wavelet_result.get(

            "wavelet_score",

            0.0

        )

    )


    # ==========================================
    # RETURN RESULT
    # ==========================================

    return {

        "signals": {

            "ela_score":

                round(

                    float(

                        ela_score

                    ),

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

                )

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