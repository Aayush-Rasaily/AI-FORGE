from pathlib import Path
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image
)


# ==========================================
# Generate PDF Report
# ==========================================

def generate_report(

    report_data,

    original_image,

    heatmap_image,

    output_pdf

):

    output_pdf = Path(output_pdf)

    output_pdf.parent.mkdir(

        parents=True,

        exist_ok=True

    )

    styles = getSampleStyleSheet()

    story = []

    # --------------------------------------
    # Title
    # --------------------------------------

    story.append(

        Paragraph(

            "<b><font size=20>AI-FORGE</font></b>",

            styles["Title"]

        )

    )

    story.append(

        Paragraph(

            "Digital Forensic Investigation Report",

            styles["Heading2"]

        )

    )

    story.append(

        Spacer(

            1,

            0.25 * inch

        )

    )

    # --------------------------------------
    # Case Information
    # --------------------------------------

    info = [

        [

            "Case ID",

            datetime.now().strftime(

                "CASE-%Y%m%d-%H%M%S"

            )

        ],

        [

            "Generated",

            datetime.now().strftime(

                "%d-%m-%Y %H:%M"

            )

        ],

        [

            "Overall Verdict",

            report_data["overall_verdict"]

        ],

        [

            "Risk Score",

            f'{report_data["risk_score"]}%'

        ],

        [

            "Confidence",

            f'{report_data["confidence"]}%'

        ]

    ]

    table = Table(

        info,

        colWidths=[2 * inch, 4 * inch]

    )

    table.setStyle(

        TableStyle([

            ("BACKGROUND",(0,0),(-1,0),colors.grey),

            ("GRID",(0,0),(-1,-1),1,colors.black),

            ("BACKGROUND",(0,0),(0,-1),colors.lightgrey),

            ("FONTNAME",(0,0),(-1,-1),"Helvetica"),

            ("BOTTOMPADDING",(0,0),(-1,-1),8)

        ])

    )

    story.append(table)

    story.append(

        Spacer(

            1,

            0.3 * inch

        )

    )

    # --------------------------------------
    # Findings
    # --------------------------------------

    story.append(

        Paragraph(

            "<b>Investigation Findings</b>",

            styles["Heading2"]

        )

    )

    for finding in report_data["findings"]:

        story.append(

            Paragraph(

                f"• {finding}",

                styles["BodyText"]

            )

        )

    story.append(

        Spacer(

            1,

            0.2 * inch

        )

    )

    # --------------------------------------
    # Signals
    # --------------------------------------

    story.append(

        Paragraph(

            "<b>Forensic Signals</b>",

            styles["Heading2"]

        )

    )

    signal_data = [

        ["Signal","Value"]

    ]

    for k,v in report_data["signals"].items():

        signal_data.append(

            [k,str(v)]

        )

    signal_table = Table(

        signal_data,

        colWidths=[2.5*inch,2.5*inch]

    )

    signal_table.setStyle(

        TableStyle([

            ("GRID",(0,0),(-1,-1),1,colors.black),

            ("BACKGROUND",(0,0),(-1,0),colors.darkblue),

            ("TEXTCOLOR",(0,0),(-1,0),colors.white),

            ("BACKGROUND",(0,1),(-1,-1),colors.beige)

        ])

    )

    story.append(signal_table)

    story.append(

        Spacer(

            1,

            0.3 * inch

        )

    )

    # --------------------------------------
    # Recommendation
    # --------------------------------------

    story.append(

        Paragraph(

            "<b>Recommendation</b>",

            styles["Heading2"]

        )

    )

    story.append(

        Paragraph(

            report_data["recommendation"],

            styles["BodyText"]

        )

    )

    story.append(

        Spacer(

            1,

            0.3 * inch

        )

    )

    # --------------------------------------
    # Original Image
    # --------------------------------------

    if Path(original_image).exists():

        story.append(

            Paragraph(

                "<b>Original Evidence</b>",

                styles["Heading2"]

            )

        )

        story.append(

            Image(

                str(original_image),

                width=5*inch,

                height=3.5*inch

            )

        )

        story.append(

            Spacer(

                1,

                0.2*inch

            )

        )

    # --------------------------------------
    # Heatmap
    # --------------------------------------

    if Path(heatmap_image).exists():

        story.append(

            Paragraph(

                "<b>AI Heatmap</b>",

                styles["Heading2"]

            )

        )

        story.append(

            Image(

                str(heatmap_image),

                width=5*inch,

                height=3.5*inch

            )

        )

        story.append(

            Spacer(

                1,

                0.2*inch

            )

        )

    # --------------------------------------
    # Footer
    # --------------------------------------

    story.append(

        Spacer(

            1,

            0.4*inch

        )

    )

    story.append(

        Paragraph(

            "<b>Generated by AI-FORGE Digital Forensic Platform</b>",

            styles["Normal"]

        )

    )

    story.append(

        Paragraph(

            "This report is AI-assisted and should be verified by a forensic expert.",

            styles["Italic"]

        )

    )

    doc = SimpleDocTemplate(

        str(output_pdf)

    )

    doc.build(story)

    print()

    print("========== REPORT ==========")

    print(output_pdf)

    print("============================")

    print()

    return str(output_pdf)