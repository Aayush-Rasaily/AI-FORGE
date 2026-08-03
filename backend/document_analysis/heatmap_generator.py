from pathlib import Path

import cv2
import numpy as np


def get_color(score):

    if score >= 80:

        return (0, 0, 255)

    elif score >= 60:

        return (0, 165, 255)

    elif score >= 40:

        return (0, 255, 255)

    return (0, 255, 0)


def get_bbox_coordinates(bbox):

    if not bbox:

        return None

    try:

        # Polygon format:
        #
        # [
        #   [x1,y1],
        #   [x2,y2],
        #   [x3,y3],
        #   [x4,y4]
        # ]

        if isinstance(

            bbox[0],

            (list, tuple)

        ):

            xs = [

                float(point[0])

                for point in bbox

            ]

            ys = [

                float(point[1])

                for point in bbox

            ]

            return (

                int(min(xs)),

                int(min(ys)),

                int(max(xs)),

                int(max(ys))

            )


        # Flat format:
        #
        # [x1,y1,x2,y2]

        if len(bbox) == 4:

            return (

                int(bbox[0]),

                int(bbox[1]),

                int(bbox[2]),

                int(bbox[3])

            )


    except (

        TypeError,

        ValueError,

        IndexError

    ):

        return None


    return None


def generate_heatmap(

    image_path,

    regions,

    output_dir

):

    image_path = Path(

        image_path

    )

    output_dir = Path(

        output_dir

    )


    output_dir.mkdir(

        parents=True,

        exist_ok=True

    )


    image = cv2.imread(

        str(image_path)

    )


    if image is None:

        raise ValueError(

            "Unable to read image"

        )


    overlay = image.copy()


    for region in regions:

        bbox = region.get(

            "bbox"

        )


        score = float(

            region.get(

                "risk_score",

                0

            )

        )


        coords = get_bbox_coordinates(

            bbox

        )


        if coords is None:

            continue


        x1, y1, x2, y2 = coords


        color = get_color(

            score

        )


        alpha = min(

            max(

                score / 100,

                0.15

            ),

            0.70

        )


        cv2.rectangle(

            overlay,

            (x1, y1),

            (x2, y2),

            color,

            -1

        )


        cv2.rectangle(

            image,

            (x1, y1),

            (x2, y2),

            color,

            2

        )


        cv2.putText(

            image,

            f"{int(score)}%",

            (

                x1,

                max(

                    15,

                    y1 - 8

                )

            ),

            cv2.FONT_HERSHEY_SIMPLEX,

            0.5,

            color,

            2

        )


    heatmap = cv2.addWeighted(

        overlay,

        0.35,

        image,

        0.65,

        0

    )


    # ======================================
    # LEGEND
    # ======================================

    legend = np.full(

        (80, 450, 3),

        255,

        dtype=np.uint8

    )


    cv2.putText(

        legend,

        "Risk Legend",

        (10, 20),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.6,

        (0, 0, 0),

        2

    )


    labels = [

        (

            "Low",

            (0, 255, 0),

            10

        ),

        (

            "Medium",

            (0, 255, 255),

            110

        ),

        (

            "High",

            (0, 165, 255),

            220

        ),

        (

            "Critical",

            (0, 0, 255),

            330

        )

    ]


    for text, color, x in labels:

        cv2.rectangle(

            legend,

            (x, 40),

            (x + 18, 58),

            color,

            -1

        )


        cv2.putText(

            legend,

            text,

            (x + 22, 54),

            cv2.FONT_HERSHEY_SIMPLEX,

            0.42,

            (0, 0, 0),

            1

        )


    # ======================================
    # SAVE
    # ======================================

    heatmap_path = (

        output_dir

        /

        f"{image_path.stem}_heatmap.jpg"

    )


    legend_path = (

        output_dir

        /

        f"{image_path.stem}_legend.jpg"

    )


    cv2.imwrite(

        str(heatmap_path),

        heatmap

    )


    cv2.imwrite(

        str(legend_path),

        legend

    )


    print()

    print(

        "========== HEATMAP =========="

    )

    print(

        "Regions:",

        len(regions)

    )

    print(

        "Saved:",

        heatmap_path

    )

    print(

        "============================="

    )

    print()


    return {

        "heatmap":

            str(

                heatmap_path

            ),

        "legend":

            str(

                legend_path

            )

    }