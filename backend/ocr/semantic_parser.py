import re
from typing import Any, Dict, List

from backend.models.document_structure import DocumentStructure, SemanticField, TextElement


class SemanticDocumentParser:
    def __init__(self):
        self.rules = {
            "Invoice Number": re.compile(r"(?i)\b(?:invoice|inv)\b[\s\-\.]*(?:no|num|#)?[\s\-\.:]*([A-Z0-9\-]{3,})"),
            "Invoice Date": re.compile(r"(?i)\b(?:date)\b[\s\-\.]*[:]?[\s\-\.]*(\b\d{1,2}[/\-\.][A-Za-z]{3,9}[/\-\.]\d{2,4}\b|\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b)"),
            "Customer Name": re.compile(r"(?i)\b(?:customer|client|bill to|ship to)\b[\s\-\.]*[:]?\s*([A-Za-z\s]+)"),
            "Item Table": re.compile(r"(?i)\b(?:description|item|product)\b"),
            "Item Name": re.compile(r"(?i)\b(?:item name|product name)\b[\s\-\.]*[:]?\s*(.+)"),
            "Quantity": re.compile(r"(?i)\b(?:qty|quantity)\b\s*[:]?\s*(\d+)"),
            "Unit Price": re.compile(r"(?i)\b(?:price|unit price)\b\s*[:\$]?\s*([\d\,\.]+)"),
            "Total": re.compile(r"(?i)(?:total|amount due|balance)[\s\-\.]*[:\$]?\s*([\d\,\.]+)"),
            "Tax": re.compile(r"(?i)(?:tax|vat|gst)[\s\-\.]*[:\$]?\s*([\d\,\.]+)"),
            "Logo": re.compile(r"(?i)(?:logo)"),
            "Signature": re.compile(r"(?i)(?:authorized\s+signatory|signature|sign\s+here)"),
            "Stamp": re.compile(r"(?i)(?:company\s+seal|stamp)"),
            "QR": re.compile(r"(?i)(?:qr code)"),
            "Barcode": re.compile(r"(?i)(?:barcode)"),
        }

    def parse(self, ocr_result: Dict[str, Any]) -> DocumentStructure:
        elements: List[TextElement] = []
        for i, d in enumerate(ocr_result.get("detections", [])):
            elem = TextElement.from_dict(d)
            if not elem.line_index:
                elem.line_index = i
            elements.append(elem)

        fields: List[SemanticField] = []

        # Sort elements top to bottom, left to right
        sorted_elements = sorted(elements, key=lambda e: (e.baseline_position, e.bounding_box.get('x', 0)))

        for element in sorted_elements:
            text = element.text.strip()
            if not text:
                continue

            matched = False
            for label, pattern in self.rules.items():
                match = pattern.search(text)
                if match:
                    extracted_val = match.group(1).strip() if match.groups() else match.group(0).strip()
                    if extracted_val:
                        fields.append(
                            SemanticField(
                                label=label,
                                text=extracted_val,
                                bounding_box=element.bounding_box,
                                confidence=element.confidence
                            )
                        )
                        matched = True
                        break
            
            # Simple heuristic for table cells (e.g. standalone numbers or short text aligned in grids)
            # This is a basic fallback for "Item Names" or "Table Cells" if not matched
            if not matched:
                if re.match(r"^[\d\,\.\$]+$", text) and element.bounding_box.get("x", 0) > 100:
                     fields.append(
                        SemanticField(
                            label="Table Cells",
                            text=text,
                            bounding_box=element.bounding_box,
                            confidence=element.confidence
                        )
                     )
                elif len(text) > 3 and " " in text and element.bounding_box.get("y", 0) < 200:
                     # Very basic heuristic for Document Title if it's near the top
                     if not any(f.label == "Document Title" for f in fields):
                         fields.append(
                            SemanticField(
                                label="Document Title",
                                text=text,
                                bounding_box=element.bounding_box,
                                confidence=element.confidence
                            )
                         )

        return DocumentStructure(elements=elements, fields=fields, metadata={"engine": ocr_result.get("engine")})
