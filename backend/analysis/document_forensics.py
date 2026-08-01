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


    # ==========================================
    # VALIDATE PDF
    # ==========================================

    if not pdf_path.exists():

        raise FileNotFoundError(
            f"PDF document not found: {pdf_path}"
        )


    print(
        f"\n[DOCUMENT] Starting analysis: "
        f"{pdf_path.name}"
    )


    # ==========================================
    # DOCUMENT PAGE OUTPUT DIRECTORY
    # ==========================================

    output_dir = (

        pdf_path.parent /

        "document_pages" /

        pdf_path.stem

    )


    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    # ==========================================
    # CONVERT PDF TO IMAGES
    # ==========================================

    print(
        "[DOCUMENT] Converting PDF to images..."
    )


    page_images = pdf_to_images(

        str(pdf_path),

        str(output_dir)

    )


    print(
        "[DOCUMENT] PDF converted successfully."
    )


    print(
        f"[DOCUMENT] Total pages: "
        f"{len(page_images)}"
    )


    pages = []


    # ==========================================
    # PROCESS EACH PAGE
    # ==========================================

    for index, image_path in enumerate(
        page_images
    ):

        page_number = index + 1


        print(

            f"\n[DOCUMENT] Processing page "

            f"{page_number}/"

            f"{len(page_images)}"

        )


        image_path = Path(
            image_path
        )


        # ======================================
        # PAGE FORENSIC OUTPUT DIRECTORY
        # ======================================

        page_analysis_dir = (

            output_dir /

            f"page_{page_number}"

        )


        page_analysis_dir.mkdir(

            parents=True,

            exist_ok=True

        )


        # ======================================
        # IMAGE FORENSICS
        # ======================================

        print(

            f"[PAGE {page_number}] "

            f"Running forensic analysis..."

        )


        forensic_result = analyze_image(

            str(image_path),

            str(page_analysis_dir)

        )


        print(

            f"[PAGE {page_number}] "

            f"Forensic analysis completed."

        )


        # ======================================
        # OCR
        # ======================================

        print(

            f"[PAGE {page_number}] "

            f"Running OCR..."

        )


        ocr_result = extract_text(

            str(image_path)

        )


        print(

            f"[PAGE {page_number}] "

            f"OCR completed."

        )


        # ======================================
        # STORE PAGE RESULT
        # ======================================

        pages.append({

            "page_number":

                page_number,


            "image":

                str(image_path),


            "ocr":

                ocr_result,


            "forensics":

                forensic_result

        })


    # ==========================================
    # FINAL DOCUMENT RESULT
    # ==========================================

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