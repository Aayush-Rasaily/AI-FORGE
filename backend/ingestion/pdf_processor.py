import fitz
from pathlib import Path


def pdf_to_images(
    pdf_path: str,
    output_dir: str
):

    pdf_path = Path(pdf_path)

    output_dir = Path(
        output_dir
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    document = fitz.open(
        pdf_path
    )


    image_paths = []


    for page_number in range(
        len(document)
    ):

        page = document[
            page_number
        ]


        # Render page at high resolution
        pixmap = page.get_pixmap(
            matrix=fitz.Matrix(
                2,
                2
            )
        )


        output_path = (
            output_dir /
            f"{pdf_path.stem}_page_{page_number + 1}.png"
        )


        pixmap.save(
            str(output_path)
        )


        image_paths.append(
            str(output_path)
        )


    document.close()


    return image_paths