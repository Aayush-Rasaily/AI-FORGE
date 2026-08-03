"""
bank_parser.py

AI-FORGE Financial Parser

Converts OCR rows into structured bank transactions.

Supported Banks (v1)

- SBI
- HSBC
- Bank of America
- Generic Statement

Author: AI-FORGE
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
import re

from backend.consistency.parser import OCRParser, OCRRow


# ---------------------------------------------------------
# Models
# ---------------------------------------------------------

@dataclass
class Transaction:

    date: str = ""

    value_date: str = ""

    description: str = ""

    reference: str = ""

    debit: float = 0.0

    credit: float = 0.0

    balance: float = 0.0

    raw_text: str = ""


@dataclass
class ParsedStatement:

    bank_name: str

    account_holder: str = ""

    account_number: str = ""

    ifsc: str = ""

    statement_period: str = ""

    opening_balance: float = 0.0

    closing_balance: float = 0.0

    transactions: List[Transaction] = field(default_factory=list)


# ---------------------------------------------------------
# Parser
# ---------------------------------------------------------

class BankParser:

    def __init__(self):

        self.parser = OCRParser()

    # -----------------------------------------------------

    def parse(self, ocr_output):

        rows = self.parser.parse(ocr_output)

        bank = self.detect_bank(rows)

        header_index = self.find_transaction_header(rows)

        statement = ParsedStatement(
            bank_name=bank
        )

        if header_index == -1:
            return statement

        statement.transactions = self.extract_transactions(
            rows,
            header_index
        )

        self.extract_metadata(
            rows,
            statement
        )

        return statement

    # -----------------------------------------------------

    def detect_bank(self, rows):

        text = " ".join(
            r.text.lower()
            for r in rows[:15]
        )

        if "state bank" in text or "sbi" in text:
            return "SBI"

        if "hsbc" in text:
            return "HSBC"

        if "bank of america" in text:
            return "BANK_OF_AMERICA"

        if "icici" in text:
            return "ICICI"

        if "hdfc" in text:
            return "HDFC"

        if "axis" in text:
            return "AXIS"

        if "canara" in text:
            return "CANARA"

        return "UNKNOWN"

    # -----------------------------------------------------

    def find_transaction_header(self, rows):

        keywords = [

            "txn date",

            "value date",

            "description",

            "debit",

            "credit",

            "balance",

            "withdrawal",

            "deposit",

            "paid out",

            "paid in"

        ]

        best_score = 0
        best_row = -1

        for idx, row in enumerate(rows):

            row_text = row.text.lower()

            score = 0

            for keyword in keywords:

                if keyword in row_text:

                    score += 1

            if score > best_score:

                best_score = score

                best_row = idx

        return best_row

    # -----------------------------------------------------

    def extract_metadata(
        self,
        rows,
        statement
    ):

        account_regex = re.compile(r"\d{9,18}")

        ifsc_regex = re.compile(
            r"[A-Z]{4}0[A-Z0-9]{6}"
        )

        for row in rows:

            text = row.text

            if not statement.account_number:

                m = account_regex.search(text)

                if m:

                    statement.account_number = m.group()

            if not statement.ifsc:

                m = ifsc_regex.search(text)

                if m:

                    statement.ifsc = m.group()

            if "account statement" in text.lower():

                statement.statement_period = text

    # -----------------------------------------------------

    def extract_transactions(
        self,
        rows,
        header_index
    ):

        """
        Implemented in Part-2
        """

        return []