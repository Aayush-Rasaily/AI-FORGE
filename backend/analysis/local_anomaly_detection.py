from pathlib import Path

import cv2
import numpy as np


# ============================================================
# CLAMP
# ============================================================

def clamp(
    value,
    minimum=0.0,
    maximum=1.0
):

    return max(

        minimum,

        min(

            maximum,

            value

        )

    )


# ============================================================
# LOCAL ANOMALY DETECTION
# ============================================================

def analyze_local_anomalies(
    image_path,
    grid_size=8
):

    image_path = Path(

        image_path

    )


    # ========================================================
    # VALIDATE
    # ========================================================

    if not image_path.exists():

        raise FileNotFoundError(

            f"Image not found: {image_path}"

        )


    # ========================================================
    # READ IMAGE
    # ========================================================

    image = cv2.imread(

        str(image_path),

        cv2.IMREAD_GRAYSCALE

    )


    if image is None:

        raise ValueError(

            "Unable to read image"

        )


    height, width = image.shape


    # ========================================================
    # BLUR IMAGE
    # ========================================================

    blurred = cv2.GaussianBlur(

        image,

        (5, 5),

        0

    )


    # ========================================================
    # NOISE MAP
    # ========================================================

    noise = (

        image.astype(

            np.float32

        )

        -

        blurred.astype(

            np.float32

        )

    )


    # ========================================================
    # CALCULATE LOCAL NOISE
    # ========================================================

    regions = []


    for row in range(

        grid_size

    ):

        for col in range(

            grid_size

        ):

            y1 = int(

                row *

                height /

                grid_size

            )

            y2 = int(

                (row + 1) *

                height /

                grid_size

            )

            x1 = int(

                col *

                width /

                grid_size

            )

            x2 = int(

                (col + 1) *

                width /

                grid_size

            )


            region = noise[

                y1:y2,

                x1:x2

            ]


            if region.size == 0:

                continue


            noise_std = float(

                np.std(

                    region

                )

            )


            regions.append({

                "row": row,

                "column": col,

                "x": x1,

                "y": y1,

                "width": x2 - x1,

                "height": y2 - y1,

                "noise_std": noise_std

            })


    # ========================================================
    # SAFETY
    # ========================================================

    if not regions:

        return {

            "local_anomaly_score": 0.0,

            "suspicious_regions": 0,

            "regions_analyzed": 0,

            "regions": []

        }


    # ========================================================
    # GLOBAL STATISTICS
    # ========================================================

    noise_values = np.array([

        region["noise_std"]

        for region in regions

    ])


    global_mean = float(

        np.mean(

            noise_values

        )

    )


    global_std = float(

        np.std(

            noise_values

        )

    )


    # ========================================================
    # AVOID DIVISION BY ZERO
    # ========================================================

    if global_std < 1e-6:

        global_std = 1e-6


    # ========================================================
    # ANALYZE EACH REGION
    # ========================================================

    suspicious_regions = []


    anomaly_scores = []


    for region in regions:

        noise_value = region[

            "noise_std"

        ]


        # Z-score

        z_score = abs(

            noise_value

            -

            global_mean

        ) / global_std


        # Normalize Z-score

        anomaly_score = clamp(

            z_score /

            4.0

        )


        region[

            "z_score"

        ] = round(

            float(

                z_score

            ),

            4

        )


        region[

            "anomaly_score"

        ] = round(

            float(

                anomaly_score

            ),

            4

        )


        anomaly_scores.append(

            anomaly_score

        )


        # ====================================================
        # SUSPICIOUS REGION
        # ====================================================

        if z_score >= 2.0:

            region[

                "suspicious"

            ] = True


            suspicious_regions.append(

                region

            )

        else:

            region[

                "suspicious"

            ] = False


    # ========================================================
    # GLOBAL LOCAL ANOMALY SCORE
    # ========================================================

    if anomaly_scores:

        # Focus more on strongest anomalies

        sorted_scores = sorted(

            anomaly_scores,

            reverse=True

        )


        top_count = max(

            1,

            min(

                5,

                len(

                    sorted_scores

                )

            )

        )


        top_scores = sorted_scores[

            :top_count

        ]


        local_anomaly_score = float(

            np.mean(

                top_scores

            )

        )

    else:

        local_anomaly_score = 0.0


    # ========================================================
    # FINAL RESULT
    # ========================================================

    return {

        "local_anomaly_score": round(

            clamp(

                local_anomaly_score

            ),

            4

        ),

        "suspicious_regions": len(

            suspicious_regions

        ),

        "regions_analyzed": len(

            regions

        ),

        "regions": suspicious_regions

    }