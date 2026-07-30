from pathlib import Path

from backend.ingestion.pdf_processor import (
    pdf_to_images
)

from backend.agents.ocr_agent import (
    extract_text
)

from backend.analysis.image_forensics import (
    analyze_image
)


def analyze_document(
    pdf_path: str
):

    pdf_path = Path(
        pdf_path
    )

    print(
        f"\n[DOCUMENT] Starting analysis: {pdf_path.name}"
    )


    # Temporary directory
    output_dir = (
        pdf_path.parent /
        "document_pages"
    )


    print(
        "[DOCUMENT] Converting PDF to images..."
    )


    page_images = pdf_to_images(

        str(pdf_path),

        str(output_dir)

    )


    print(
        f"[DOCUMENT] PDF converted successfully."
    )

    print(
        f"[DOCUMENT] Total pages: {len(page_images)}"
    )


    pages = []


    for index, image_path in enumerate(
        page_images
    ):

        page_number = index + 1


        print(
            f"\n[DOCUMENT] Processing page "
            f"{page_number}/{len(page_images)}"
        )


        # --------------------------------
        # Image Forensics
        # --------------------------------

        print(
            f"[PAGE {page_number}] "
            f"Running forensic analysis..."
        )


        forensic_result = analyze_image(
            image_path
        )


        print(
            f"[PAGE {page_number}] "
            f"Forensic analysis completed."
        )


        # --------------------------------
        # OCR
        # --------------------------------

        print(
            f"[PAGE {page_number}] "
            f"Running OCR..."
        )


        ocr_result = extract_text(
            image_path
        )


        print(
            f"[PAGE {page_number}] "
            f"OCR completed."
        )


        pages.append({

            "page_number":
                page_number,

            "image":
                image_path,

            "ocr":
                ocr_result,

            "forensics":
                forensic_result

        })


    print(
        "\n[DOCUMENT] Analysis completed successfully."
    )


    return {

        "document_type":
            "PDF",

        "page_count":
            len(pages),

        "pages":
            pages

    }