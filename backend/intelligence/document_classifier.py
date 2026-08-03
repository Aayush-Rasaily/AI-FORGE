"""
document_classifier.py

AI-FORGE Document Intelligence Engine

Detects the uploaded document type from OCR output.

Supported:
- Bank Statement
- Hospital Bill
- Insurance Policy
- Aadhaar
- PAN
- Passport
- Driving Licence
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List
import re


# ---------------------------------------------

@dataclass
class ClassificationResult:
    document_type: str
    confidence: float
    matched_keywords: List[str]


# ---------------------------------------------

DOCUMENT_RULES = {

    "BANK_STATEMENT": [

        "account number",
        "available balance",
        "opening balance",
        "closing balance",
        "transaction",
        "withdrawal",
        "deposit",
        "ifsc",
        "statement",
        "bank",
        "credited",
        "debited"

    ],

    "HOSPITAL_BILL": [

        "patient",
        "hospital",
        "invoice",
        "doctor",
        "medicine",
        "consultation",
        "diagnosis",
        "gst",
        "pharmacy",
        "admission",
        "discharge"

    ],

    "INSURANCE_POLICY": [

        "policy",
        "premium",
        "insured",
        "claim",
        "coverage",
        "vehicle",
        "insurance",
        "sum insured",
        "nominee"

    ],

    "AADHAAR": [

        "aadhaar",
        "government of india",
        "uidai",
        "dob",
        "male",
        "female"

    ],

    "PAN_CARD": [

        "income tax department",
        "permanent account number",
        "pan"

    ],

    "PASSPORT": [

        "passport",
        "nationality",
        "place of birth",
        "date of issue"

    ],

    "DRIVING_LICENSE": [

        "driving licence",
        "transport",
        "dl no",
        "valid till"

    ]

}


# ---------------------------------------------

class DocumentClassifier:

    def __init__(self):

        self.rules = DOCUMENT_RULES

    # -----------------------------------------

    def classify(
        self,
        ocr_output: Dict
    ) -> ClassificationResult:

        text = ocr_output.get(
            "full_text",
            ""
        ).lower()

        scores = {}

        matches = {}

        for doc_type, keywords in self.rules.items():

            score = 0

            found = []

            for keyword in keywords:

                if keyword in text:

                    score += 1

                    found.append(keyword)

            scores[doc_type] = score

            matches[doc_type] = found

        best = max(
            scores,
            key=scores.get
        )

        total_keywords = len(
            self.rules[best]
        )

        confidence = (
            scores[best] / total_keywords
        )

        return ClassificationResult(

            document_type=best,

            confidence=round(confidence, 3),

            matched_keywords=matches[best]

        )