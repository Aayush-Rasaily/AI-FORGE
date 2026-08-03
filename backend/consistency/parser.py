"""
parser.py

Universal OCR parser for AI-FORGE.

Converts EasyOCR detections into structured rows and
normalized text suitable for forensic validation.

Author: AI-FORGE
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any
import re


# --------------------------------------------------
# Data Models
# --------------------------------------------------

@dataclass
class OCRWord:
    text: str
    confidence: float

    left: float
    right: float
    top: float
    bottom: float

    width: float
    height: float

    center_x: float
    center_y: float


@dataclass
class OCRRow:
    words: List[OCRWord]

    top: float
    bottom: float

    text: str

    confidence: float


# --------------------------------------------------
# Parser
# --------------------------------------------------

class OCRParser:

    def __init__(self,
                 row_threshold: int = 15):

        self.row_threshold = row_threshold

    # ----------------------------------------------

    def parse(self,
              ocr_output: Dict[str, Any]) -> List[OCRRow]:

        words = self._convert_to_words(
            ocr_output["detections"]
        )

        words = sorted(
            words,
            key=lambda w: w.center_y
        )

        rows = self._group_rows(words)

        return rows

    # ----------------------------------------------

    def _convert_to_words(
        self,
        detections: List[Dict]
    ) -> List[OCRWord]:

        words = []

        for d in detections:

            words.append(

                OCRWord(

                    text=d["text"],

                    confidence=d["confidence"],

                    left=d["left"],

                    right=d["right"],

                    top=d["top"],

                    bottom=d["bottom"],

                    width=d["width"],

                    height=d["height"],

                    center_x=d["center_x"],

                    center_y=d["center_y"]

                )

            )

        return words

    # ----------------------------------------------

    def _group_rows(
        self,
        words: List[OCRWord]
    ) -> List[OCRRow]:

        rows = []

        current = []

        current_y = None

        for word in words:

            if current_y is None:

                current.append(word)

                current_y = word.center_y

                continue

            if abs(word.center_y-current_y) <= self.row_threshold:

                current.append(word)

            else:

                rows.append(
                    self._create_row(current)
                )

                current = [word]

                current_y = word.center_y

        if current:

            rows.append(
                self._create_row(current)
            )

        return rows

    # ----------------------------------------------

    def _create_row(
        self,
        words: List[OCRWord]
    ) -> OCRRow:

        words = sorted(
            words,
            key=lambda w: w.left
        )

        text = " ".join(

            w.text

            for w in words

        )

        confidence = sum(

            w.confidence

            for w in words

        ) / len(words)

        return OCRRow(

            words=words,

            top=min(w.top for w in words),

            bottom=max(w.bottom for w in words),

            text=text,

            confidence=confidence

        )

# --------------------------------------------------
# Utility Functions
# --------------------------------------------------

amount_regex = re.compile(
    r'[-+]?\d[\d,]*\.?\d*'
)

date_regex = re.compile(
    r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}'
)


def is_amount(text: str):

    return bool(
        amount_regex.fullmatch(
            text.replace("₹", "")
                .replace(",", "")
        )
    )


def parse_amount(text: str):

    text = (
        text.replace("₹", "")
            .replace(",", "")
            .strip()
    )

    try:

        return float(text)

    except:

        return None


def is_date(text: str):

    return bool(
        date_regex.fullmatch(text)
    )


# --------------------------------------------------
# Pretty Print
# --------------------------------------------------

def print_rows(rows: List[OCRRow]):

    print("=" * 80)

    for idx, row in enumerate(rows):

        print(f"ROW {idx+1}")

        print(row.text)

        print("-" * 80)