from pathlib import Path


from backend.ingestion.pdf_processor import (

    pdf_to_images

)


from backend.agents.ocr_agent import (

    extract_text

)


from backend.document_analysis.risk_engine import (

    analyze_document_risk

)


from backend.document_analysis.heatmap_generator import (

    generate_heatmap

)


from backend.document_analysis.report_generator import (

    generate_report

)


def analyze_document(

    pdf_path: str

):

    pdf_path = Path(

        pdf_path

    )


    if not pdf_path.exists():

        raise FileNotFoundError(

            f"PDF document not found: {pdf_path}"

        )


    print()

    print(

        "=========================================="

    )

    print(

        "AI-FORGE DOCUMENT FORENSIC ANALYSIS"

    )

    print(

        "=========================================="

    )

    print(

        "Document:",

        pdf_path.name

    )


    # ==========================================
    # OUTPUT DIRECTORY
    # ==========================================

    output_dir = (

        pdf_path.parent

        /

        "document_pages"

        /

        pdf_path.stem

    )


    output_dir.mkdir(

        parents=True,

        exist_ok=True

    )


    # ==========================================
    # PDF TO IMAGES
    # ==========================================

    print()

    print(

        "[DOCUMENT] Converting PDF to images..."

    )


    page_images = pdf_to_images(

        str(pdf_path),

        str(output_dir)

    )


    print(

        "[DOCUMENT] Conversion completed."

    )


    print(

        "[DOCUMENT] Pages:",

        len(page_images)

    )


    pages = []


    # ==========================================
    # PROCESS PAGES
    # ==========================================

    for index, image_path in enumerate(

        page_images

    ):


        page_number = index + 1


        image_path = Path(

            image_path

        )


        print()

        print(

            "=========================================="

        )

        print(

            f"PROCESSING PAGE {page_number}/"

            f"{len(page_images)}"

        )

        print(

            "=========================================="

        )


        # ======================================
        # PAGE DIRECTORY
        # ======================================

        page_analysis_dir = (

            output_dir

            /

            f"page_{page_number}"

        )


        page_analysis_dir.mkdir(

            parents=True,

            exist_ok=True

        )


        # ======================================
        # OCR
        # ======================================

        print(

            "[PAGE] Running OCR..."

        )


        ocr_result = extract_text(

            str(image_path)

        )


        print(

            "[PAGE] OCR completed."

        )


        # ======================================
        # FORENSIC RISK ENGINE
        # ======================================

        print(

            "[PAGE] Running forensic risk engine..."

        )


        risk_result = analyze_document_risk(

            str(image_path),

            str(page_analysis_dir)

        )


        # ======================================
        # HEATMAP
        # ======================================

        raw_analysis = risk_result.get(

            "raw_analysis",

            {}

        )


        region_analysis = raw_analysis.get(

            "regions",

            {}

        )


        regions = region_analysis.get(

            "regions",

            []

        )


        heatmap_result = generate_heatmap(

            str(image_path),

            regions,

            str(page_analysis_dir)

        )


        # ======================================
        # PAGE RESULT
        # ======================================

        page_result = {

            "page_number":

                page_number,

            "image":

                str(image_path),

            "ocr":

                ocr_result,

            "risk":

                risk_result,

            "heatmap":

                heatmap_result

        }


        pages.append(

            page_result

        )


        print()

        print(

            f"[PAGE {page_number}] "

            "FINAL RESULT"

        )

        print(

            "Risk Score:",

            risk_result[

                "risk_score"

            ]

        )

        print(

            "Confidence:",

            risk_result[

                "confidence"

            ]

        )

        print(

            "Verdict:",

            risk_result[

                "overall_verdict"

            ]

        )


    # ==========================================
    # DOCUMENT LEVEL RISK
    # ==========================================

    if pages:

        page_scores = [

            p["risk"]["risk_score"]

            for p in pages

        ]


        # The strongest suspicious page
        # matters significantly.

        max_score = max(

            page_scores

        )


        average_score = sum(

            page_scores

        ) / len(

            page_scores

        )


        # Weighted document score

        document_risk = (

            max_score * 0.70

            +

            average_score * 0.30

        )


    else:

        document_risk = 0.0


    document_risk = round(

        min(

            document_risk,

            100

        ),

        2

    )


    # ==========================================
    # DOCUMENT VERDICT
    # ==========================================

    if document_risk >= 80:

        document_verdict = (

            "CRITICAL RISK"

        )


    elif document_risk >= 60:

        document_verdict = (

            "HIGH RISK"

        )


    elif document_risk >= 35:

        document_verdict = (

            "MEDIUM RISK"

        )


    elif document_risk >= 15:

        document_verdict = (

            "LOW RISK"

        )


    else:

        document_verdict = (

            "NO SIGNIFICANT ANOMALY"

        )


    # ==========================================
    # DOCUMENT FINDINGS
    # ==========================================

    document_findings = []


    for page in pages:

        for finding in page["risk"].get(

            "findings",

            []

        ):

            document_findings.append({

                "page":

                    page[

                        "page_number"

                    ],

                **finding

            })


    # ==========================================
    # FINAL RESULT
    # ==========================================

    final_result = {

        "document_type":

            "PDF",

        "document_name":

            pdf_path.name,

        "page_count":

            len(pages),

        "risk_score":

            document_risk,

        "overall_verdict":

            document_verdict,

        "pages":

            pages,

        "findings":

            document_findings

    }


    print()

    print(

        "=========================================="

    )

    print(

        "DOCUMENT FORENSIC ANALYSIS COMPLETE"

    )

    print(

        "=========================================="

    )

    print(

        "Document Risk:",

        document_risk

    )

    print(

        "Verdict:",

        document_verdict

    )

    print(

        "Suspicious Findings:",

        len(document_findings)

    )

    print(

        "=========================================="

    )

    print()


    return final_result