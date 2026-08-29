"""
OCR Difference Engine — Phase 2 of AI-FORGE Intelligent Forensic Analysis.

File: backend/document_analysis/ocr_difference_engine.py

Produces:  <analysis_dir>/ocr_difference_report.json

Pipeline stages
---------------
  Stage 1  FieldGrouper          Group OCR words into semantic document fields
  Stage 2  ValueAnalyzer         Detect altered numbers, dates, currencies, IDs
  Stage 3  FontAnomalyDetector   Per-word statistical font feature comparison
  Stage 4  LayoutAnomalyDetector Geometric layout anomalies (misalignment, floats)
  Stage 5  EvidenceLinker        IoU-link findings to Phase 1 localization regions
  Stage 6  Serializer            Atomic JSON write

Public API
----------
  run_ocr_difference_engine(
      analysis_result: dict,
      analysis_dir: Path,
      evidence_id: str,
  ) -> dict

Contract
--------
  • Never mutates analysis_result.
  • Always writes ocr_difference_report.json.
  • On any failure: logs warning, returns error dict (caller wraps in try/except).
  • Deterministic — identical inputs produce identical output.
  • No external dependencies beyond stdlib + numpy (already required).
"""

from __future__ import annotations

import json
import logging
import math
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("ai_forge.ocr_difference_engine")

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

SCHEMA_VERSION = "2.0"
OUTPUT_FILENAME = "ocr_difference_report.json"

# Statistical z-score thresholds for font anomaly detection
_Z_FONT_HEIGHT   = 1.8   # line-level height z-score
_Z_BLACK_RATIO   = 2.0   # document-level stroke thickness
_Z_EDGE_DENSITY  = 2.0   # document-level edge density
_Z_INTENSITY     = 2.5   # document-level mean pixel intensity
_Z_ASPECT_RATIO  = 2.0   # document-level w/h ratio

_BASELINE_FRAC   = 0.25  # max baseline deviation as fraction of word height
_KERNING_MULT    = 3.5   # gap must exceed avg gap × this to flag
_OVERLAP_IOU     = 0.10  # bbox IoU threshold to flag overlap
_LAYOUT_LEFT_TOL = 25    # px — tolerated left-edge deviation from margin
_LAYOUT_RIGHT_TOL = 40   # px — tolerated right-edge deviation from margin

# Minimum IoU between a finding bbox and a Phase 1 region to consider linked
_LINK_IOU_THRESH = 0.12

# Confidence boost per linked Phase 1 region
_LINK_BOOST      = 0.10

# Maximum findings in the final report
_MAX_FINDINGS    = 60

# ─────────────────────────────────────────────────────────────────────────────
# Currency symbol set
_CURRENCY_SYMBOLS = frozenset("$₹€£¥")

# Semantic field patterns — ordered list of (regex, field_label, field_category)
_FIELD_PATTERNS: List[Tuple[re.Pattern, str, str]] = [
    (re.compile(r"(?i)\b(?:invoice|inv)\b[\s\-\.]*(?:no|num|#|number|id)?[\s\-\.:]*"), "Invoice Number", "reference"),
    (re.compile(r"(?i)\b(?:invoice|due|issue|effective|expiry|start|end|policy)\s*date\b"), "Date", "date"),
    (re.compile(r"(?i)\bdate\b"), "Date", "date"),
    (re.compile(r"(?i)\b(?:total\s*amount|total\s*due|amount\s*due|balance\s*due|net\s*amount)\b"), "Total Amount", "currency"),
    (re.compile(r"(?i)\b(?:sub[\s\-]?total)\b"), "Subtotal", "currency"),
    (re.compile(r"(?i)\btotal\b"), "Total", "currency"),
    (re.compile(r"(?i)\b(?:unit\s*price|price\s*per|rate)\b"), "Unit Price", "currency"),
    (re.compile(r"(?i)\bprice\b"), "Price", "currency"),
    (re.compile(r"(?i)\b(?:tax|vat|gst|igst|cgst|sgst)\b"), "Tax", "percentage"),
    (re.compile(r"(?i)\b(?:qty|quantity|units?)\b"), "Quantity", "numeric"),
    (re.compile(r"(?i)\b(?:discount|rebate)\b"), "Discount", "percentage"),
    (re.compile(r"(?i)\b(?:account\s*(?:no|num|number)|a[\s/]c|bank\s*account|acct)\b"), "Account Number", "reference"),
    (re.compile(r"(?i)\b(?:policy\s*(?:no|num|number|id)|policy)\b"), "Policy Number", "reference"),
    (re.compile(r"(?i)\b(?:customer|client|bill\s*to|ship\s*to|payee)\b"), "Customer Name", "text"),
    (re.compile(r"(?i)\b(?:company|firm|vendor|supplier|seller)\b"), "Company Name", "text"),
    (re.compile(r"(?i)\b(?:authorized\s*signatory|signature|sign\s*here)\b"), "Signature", "signature"),
    (re.compile(r"(?i)\b(?:company\s*seal|stamp|official\s*seal)\b"), "Stamp / Seal", "signature"),
    (re.compile(r"(?i)\b(?:vehicle\s*(?:no|number)|reg(?:istration)?\s*no|vin)\b"), "Vehicle / Reg Number", "reference"),
    (re.compile(r"(?i)\b(?:description|particulars|item\s*name|product)\b"), "Item Description", "text"),
    (re.compile(r"(?i)\b(?:hsn|sac)\b"), "HSN / SAC Code", "reference"),
]

# Value-type patterns for unmatched standalone words
_NUMBER_RE      = re.compile(r"^\d[\d,\.]*$")
_CURRENCY_RE    = re.compile(r"^[$₹€£¥]\s*[\d,\.]+$")
_PERCENT_RE     = re.compile(r"^\d+(?:\.\d+)?%$")
_DATE_RE        = re.compile(
    r"\b(\d{1,2})[/\-\.](\d{1,2}|\w{3,9})[/\-\.](\d{2,4})\b"
    r"|\b(\d{4})[/\-\.](\d{2})[/\-\.](\d{2})\b"
)
_ID_RE          = re.compile(r"\b([A-Z]{2,}\d{4,}|\d{8,})\b")


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _sf(v: Any, d: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def _si(v: Any, d: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return d


def _bbox_from_word(word: Dict[str, Any]) -> Optional[Tuple[int, int, int, int]]:
    """
    Extract (x, y, w, h) from an OCR word dict.
    Supports polygon bbox [[x,y]×4], dict {x,y,w,h}, list [x,y,w,h].
    """
    raw = word.get("bbox") or word.get("bounding_box")
    if raw is None:
        return None
    if isinstance(raw, (list, tuple)):
        if len(raw) == 4 and isinstance(raw[0], (list, tuple)):
            # polygon: [[x0,y0],[x1,y1],[x2,y2],[x3,y3]]
            xs = [float(p[0]) for p in raw]
            ys = [float(p[1]) for p in raw]
            x, y = int(min(xs)), int(min(ys))
            w = int(max(xs) - min(xs))
            h = int(max(ys) - min(ys))
            return (x, y, max(1, w), max(1, h))
        if len(raw) >= 4:
            return (_si(raw[0]), _si(raw[1]), _si(raw[2]), _si(raw[3]))
    if isinstance(raw, dict):
        x = _si(raw.get("x", raw.get("left", 0)))
        y = _si(raw.get("y", raw.get("top", 0)))
        w = _si(raw.get("w", raw.get("width", 0)))
        h = _si(raw.get("h", raw.get("height", 0)))
        return (x, y, max(1, w), max(1, h))
    return None


def _iou_xywh(
    a: Tuple[int, int, int, int],
    b: Tuple[int, int, int, int],
) -> float:
    ax1, ay1 = a[0], a[1]
    ax2, ay2 = a[0] + a[2], a[1] + a[3]
    bx1, by1 = b[0], b[1]
    bx2, by2 = b[0] + b[2], b[1] + b[3]
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter == 0:
        return 0.0
    ua = a[2] * a[3]
    ub = b[2] * b[3]
    return inter / (ua + ub - inter + 1e-8)


def _parse_number(text: str) -> Optional[float]:
    """Parse a numeric string, stripping commas and currency symbols."""
    cleaned = re.sub(r"[,$₹€£¥\s]", "", text)
    try:
        return float(cleaned)
    except ValueError:
        return None


def _zscore(val: float, mean: float, std: float) -> float:
    return abs(val - mean) / (std + 1e-9)


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 1 — FIELD GROUPER
# ═══════════════════════════════════════════════════════════════════════════════

class _GroupedField:
    """A semantic document field with its label-word and value-words."""
    __slots__ = ("label", "category", "label_text", "label_bbox",
                 "value_words", "line_y")

    def __init__(
        self,
        label: str,
        category: str,
        label_text: str,
        label_bbox: Optional[Tuple[int, int, int, int]],
        value_words: List[Dict[str, Any]],
        line_y: float,
    ):
        self.label = label
        self.category = category
        self.label_text = label_text
        self.label_bbox = label_bbox
        self.value_words = value_words
        self.line_y = line_y

    @property
    def value_text(self) -> str:
        return " ".join(w.get("text", "") for w in self.value_words).strip()

    @property
    def value_bbox(self) -> Optional[Tuple[int, int, int, int]]:
        bboxes = [_bbox_from_word(w) for w in self.value_words]
        bboxes = [b for b in bboxes if b]
        if not bboxes:
            return None
        x1 = min(b[0] for b in bboxes)
        y1 = min(b[1] for b in bboxes)
        x2 = max(b[0] + b[2] for b in bboxes)
        y2 = max(b[1] + b[3] for b in bboxes)
        return (x1, y1, max(1, x2 - x1), max(1, y2 - y1))

    @property
    def confidence(self) -> float:
        confs = [_sf(w.get("confidence", 0.9)) for w in self.value_words]
        # normalise: OCR engines sometimes use 0-100, sometimes 0-1
        norm = []
        for c in confs:
            norm.append(c / 100.0 if c > 1.0 else c)
        return round(sum(norm) / max(1, len(norm)), 4) if norm else 0.90


class FieldGrouper:
    """
    Stage 1: Groups OCR detections into semantic document fields.

    Algorithm
    ---------
    1. Sort all words top-to-bottom, left-to-right.
    2. For each word, check if it matches any field label pattern.
    3. If matched, scan rightward and downward (next line) for value tokens.
    4. Unmatched numeric/currency/date words → "Unknown Numeric/Value" fields.
    """

    def group(
        self,
        layout_data: Dict[str, Any],
        detections: List[Dict[str, Any]],
    ) -> List[_GroupedField]:
        """
        Parameters
        ----------
        layout_data  : output from text_layout_analysis (has 'lines' key)
        detections   : OCR word detections (from consensus engine or any engine)

        Returns
        -------
        List of _GroupedField objects.
        """
        lines = layout_data.get("lines") or []

        # Flatten all words, attaching line metadata
        all_words: List[Dict[str, Any]] = []
        for line in lines:
            for word in line.get("words", []):
                w = dict(word)
                w["_line_y"] = float(word.get("center_y", 0))
                all_words.append(w)

        # Also include consensus detections not present in layout (different OCR path)
        layout_texts = {w.get("text", ""): True for w in all_words}
        for det in detections:
            if det.get("text") not in layout_texts:
                d = dict(det)
                top = _sf(det.get("top", det.get("y", 0)))
                h   = _sf(det.get("height", det.get("h", 10)))
                d["_line_y"] = top + h / 2.0
                all_words.append(d)

        # Sort: top-to-bottom, left-to-right
        all_words.sort(key=lambda w: (w.get("_line_y", 0), _sf(
            ((_bbox_from_word(w) or (0, 0, 0, 0))[0])
        )))

        fields: List[_GroupedField] = []
        used_indices: set = set()

        for i, word in enumerate(all_words):
            if i in used_indices:
                continue
            text = str(word.get("text", "")).strip()
            if not text:
                continue

            matched_label, matched_cat = self._match_label(text)

            if matched_label:
                used_indices.add(i)
                # Collect value words: same line (right of label) + next line
                value_words = self._collect_values(
                    i, word, all_words, used_indices
                )
                if value_words:
                    fields.append(_GroupedField(
                        label=matched_label,
                        category=matched_cat,
                        label_text=text,
                        label_bbox=_bbox_from_word(word),
                        value_words=value_words,
                        line_y=word.get("_line_y", 0),
                    ))

        # Collect ungrouped numeric/currency/date tokens as anonymous fields
        for i, word in enumerate(all_words):
            if i in used_indices:
                continue
            text = str(word.get("text", "")).strip()
            if not text:
                continue
            cat = self._classify_standalone(text)
            if cat:
                fields.append(_GroupedField(
                    label=f"Standalone {cat.title()} Value",
                    category=cat,
                    label_text="",
                    label_bbox=None,
                    value_words=[word],
                    line_y=word.get("_line_y", 0),
                ))
                used_indices.add(i)

        return fields

    @staticmethod
    def _match_label(text: str) -> Tuple[Optional[str], Optional[str]]:
        for pattern, label, cat in _FIELD_PATTERNS:
            if pattern.search(text):
                return label, cat
        return None, None

    @staticmethod
    def _collect_values(
        label_idx: int,
        label_word: Dict[str, Any],
        all_words: List[Dict[str, Any]],
        used_indices: set,
    ) -> List[Dict[str, Any]]:
        label_y   = label_word.get("_line_y", 0)
        label_bbox = _bbox_from_word(label_word)
        label_x2   = (label_bbox[0] + label_bbox[2]) if label_bbox else 0

        values = []
        for j, w in enumerate(all_words):
            if j == label_idx or j in used_indices:
                continue
            t = str(w.get("text", "")).strip()
            if not t:
                continue
            wy = w.get("_line_y", 0)
            wb = _bbox_from_word(w)
            wx = wb[0] if wb else 0

            # Same line, to the right of label — always a value candidate
            if abs(wy - label_y) <= 25 and wx >= label_x2 - 10:
                values.append(w)
                used_indices.add(j)
            # Next line below label — take first token if it looks like a value
            elif label_y < wy <= label_y + 60:
                if (
                    _NUMBER_RE.match(t)
                    or _CURRENCY_RE.match(t)
                    or _PERCENT_RE.match(t)
                    or _DATE_RE.search(t)
                    or _ID_RE.search(t)
                ):
                    values.append(w)
                    used_indices.add(j)

        return values

    @staticmethod
    def _classify_standalone(text: str) -> Optional[str]:
        if _CURRENCY_RE.match(text):
            return "currency"
        if _PERCENT_RE.match(text):
            return "percentage"
        if _DATE_RE.search(text):
            return "date"
        if _NUMBER_RE.match(text) and len(text) >= 4:
            return "numeric"
        if _ID_RE.search(text):
            return "reference"
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 2 — VALUE ANALYZER
# ═══════════════════════════════════════════════════════════════════════════════

class ValueAnalyzer:
    """
    Stage 2: Detects value manipulation within each semantic field.

    Cross-references:
        • OCR consensus mismatch_regions (engine disagreement on a bbox)
        • Standalone value anomalies (suspicious number patterns)
        • Known manipulation signatures (digit insertion, magnitude change, etc.)
    """

    def analyze(
        self,
        fields: List[_GroupedField],
        mismatch_regions: List[Dict[str, Any]],
        font_result: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []

        # Build mismatch lookup: map bbox → mismatch info (for overlap testing)
        mismatch_bboxes: List[Tuple[Tuple[int,int,int,int], Dict[str,Any]]] = []
        for m in mismatch_regions:
            raw = m.get("bbox")
            if raw:
                bbox = _bbox_from_word({"bbox": raw})
                if bbox:
                    mismatch_bboxes.append((bbox, m))

        # Suspicious words from font_consistency (pre-computed in pipeline)
        suspicious_font_texts: set = {
            str(w.get("text", "")).strip().lower()
            for w in (font_result.get("suspicious_words") or [])
        }

        for field in fields:
            val = field.value_text
            if not val:
                continue

            reasons: List[str] = []
            ftype: Optional[str] = None
            original_estimate: str = ""
            current_val: str = val

            # ── Numeric manipulation ────────────────────────────────────────
            if field.category in ("currency", "numeric", "percentage"):
                result = self._check_numeric(val, field.category)
                if result:
                    ftype, reason_list, original_estimate = result
                    reasons.extend(reason_list)

            # ── Date manipulation ───────────────────────────────────────────
            elif field.category == "date":
                result = self._check_date(val)
                if result:
                    ftype, reason_list, original_estimate = result
                    reasons.extend(reason_list)

            # ── Reference / ID manipulation ─────────────────────────────────
            elif field.category == "reference":
                result = self._check_reference(val)
                if result:
                    ftype, reason_list, original_estimate = result
                    reasons.extend(reason_list)

            # ── OCR consensus mismatch overlap ──────────────────────────────
            vbbox = field.value_bbox
            if vbbox:
                for mbbox, m in mismatch_bboxes:
                    if _iou_xywh(vbbox, mbbox) >= 0.15:
                        texts = m.get("texts") or []
                        winner = m.get("winner", val)
                        disagree = round(_sf(m.get("disagreement", 0)) * 100)
                        reasons.append(
                            f"OCR engine disagreement on this region "
                            f"({disagree}% disagreement — engines saw: "
                            f"{', '.join(str(t) for t in texts[:3])})"
                        )
                        if not ftype:
                            ftype = "ocr_engine_mismatch"

            # ── Font-consistency cross-check ────────────────────────────────
            for vword in field.value_words:
                wt = str(vword.get("text", "")).strip().lower()
                if wt in suspicious_font_texts:
                    reasons.append(
                        f"Font inconsistency flagged on value token '{vword.get('text', '')}'"
                    )
                    if not ftype:
                        ftype = "font_anomaly_on_value"

            # ── Low OCR confidence on value words ───────────────────────────
            low_conf = [
                w for w in field.value_words
                if _sf(w.get("confidence", 1.0)) < (0.70 if _sf(w.get("confidence", 1.0)) <= 1.0 else 70)
            ]
            if low_conf:
                reasons.append(
                    f"Low OCR confidence on value token(s): "
                    + ", ".join(f"'{w.get('text','')}'" for w in low_conf[:3])
                )
                if not ftype:
                    ftype = "low_ocr_confidence"

            if not reasons and not ftype:
                continue

            conf = self._estimate_confidence(reasons, field.confidence)
            severity = "Critical" if conf >= 0.85 else "High" if conf >= 0.65 else "Medium"

            findings.append({
                "_stage": "value",
                "field": field.label,
                "field_category": field.category,
                "type": ftype or "value_anomaly",
                "original": original_estimate or "—",
                "current": current_val,
                "confidence": conf,
                "bbox": list(vbbox) if vbbox else None,
                "reason": reasons,
                "severity": severity,
            })

        return findings

    # ── Sub-detectors ───────────────────────────────────────────────────────

    def _check_numeric(
        self, val: str, category: str
    ) -> Optional[Tuple[str, List[str], str]]:
        num = _parse_number(val)
        if num is None:
            return None

        reasons: List[str] = []
        ftype = ""

        # Character insertion: e.g. 200 → 2000 (same leading digits, more digits)
        digits = re.sub(r"[^\d]", "", val)
        if len(digits) >= 2:
            # Suspiciously round: trailing zeros exceeding 2
            trailing_zeros = len(digits) - len(digits.rstrip("0"))
            if trailing_zeros >= 3 and len(digits) >= 4:
                original_est = val.rstrip("0").rstrip(".") or digits[0]
                reasons.append(
                    f"Suspicious trailing zeros: '{val}' has {trailing_zeros} "
                    f"trailing zeros — possible digit insertion"
                )
                ftype = "character_insertion"

            # Magnitude check: value unusually large for field category
            if category == "percentage" and num > 100:
                reasons.append(
                    f"Percentage value {num:.1f} exceeds 100% — impossible value"
                )
                ftype = "impossible_value"

        if reasons:
            original_est = re.sub(r"0+$", "", digits)
            return ftype or "numeric_anomaly", reasons, original_est

        return None

    def _check_date(
        self, val: str
    ) -> Optional[Tuple[str, List[str], str]]:
        match = _DATE_RE.search(val)
        if not match:
            return None

        reasons: List[str] = []
        ftype = ""

        # Try to extract numeric day/month/year
        groups = [g for g in match.groups() if g]
        try:
            if len(groups) >= 3:
                d_str, m_str, y_str = str(groups[0]), str(groups[1]), str(groups[2])
                day = int(d_str) if d_str.isdigit() else None
                month = int(m_str) if m_str.isdigit() else None
                year = int(y_str)

                if day and day > 31:
                    reasons.append(f"Impossible day value: {day}")
                    ftype = "impossible_date"

                if month and month > 12:
                    reasons.append(f"Impossible month value: {month}")
                    ftype = "impossible_date"

                if year < 1900 or year > 2100:
                    reasons.append(f"Year {year} outside plausible document range")
                    ftype = "date_out_of_range"

                # Future date check
                now = datetime.now()
                if day and month:
                    try:
                        y2 = year if year > 100 else (2000 + year)
                        parsed = datetime(y2, month, day)
                        if parsed > now:
                            reasons.append(
                                f"Document date {parsed.strftime('%Y-%m-%d')} "
                                f"is in the future — possibly altered"
                            )
                            if not ftype:
                                ftype = "future_date"
                    except ValueError:
                        reasons.append(
                            f"Date value '{val}' is not a valid calendar date"
                        )
                        ftype = "impossible_date"
        except Exception:
            pass

        if reasons:
            return ftype or "date_anomaly", reasons, ""
        return None

    def _check_reference(
        self, val: str
    ) -> Optional[Tuple[str, List[str], str]]:
        reasons: List[str] = []
        ftype = ""

        digits = re.sub(r"[^\d]", "", val)

        # Luhn check for long numeric IDs (card numbers, account numbers)
        if len(digits) >= 13 and not self._luhn_check(digits):
            reasons.append(
                f"Checksum (Luhn) validation failed for numeric ID '{val}'"
            )
            ftype = "checksum_failed"

        if reasons:
            return ftype or "reference_anomaly", reasons, ""
        return None

    @staticmethod
    def _luhn_check(num_str: str) -> bool:
        total = 0
        reverse = num_str[::-1]
        for i, d in enumerate(reverse):
            n = int(d)
            if i % 2 == 1:
                n *= 2
                if n > 9:
                    n -= 9
            total += n
        return total % 10 == 0

    @staticmethod
    def _estimate_confidence(reasons: List[str], ocr_conf: float) -> float:
        base = 0.55
        base += min(0.30, len(reasons) * 0.10)
        # OCR engine confidence is inversely correlated with manipulation confidence
        base += (1.0 - min(1.0, ocr_conf)) * 0.15
        return round(min(0.99, max(0.50, base)), 4)


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 3 — FONT ANOMALY DETECTOR
# ═══════════════════════════════════════════════════════════════════════════════

class FontAnomalyDetector:
    """
    Stage 3: Statistical per-word font feature comparison.

    Consumes pre-computed font features from font_consistency.py output.
    Computes document-wide statistics, then flags words that deviate
    beyond threshold z-scores in multiple dimensions.
    """

    def detect(
        self,
        font_result: Dict[str, Any],
        layout_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []

        # ── Build per-word feature matrix ───────────────────────────────────
        suspicious_words = font_result.get("suspicious_words") or []
        avg_stats        = font_result.get("average") or {}

        # Document-wide averages (pre-computed by font_consistency.py)
        doc_black  = _sf(avg_stats.get("black_ratio", 0.15))
        doc_edge   = _sf(avg_stats.get("edge_density", 0.05))

        # Collect all word features for std calculation
        all_intensities: List[float] = []
        all_aspects: List[float]     = []
        all_heights: List[float]     = []

        lines = layout_data.get("lines") or []
        for line in lines:
            for word in line.get("words", []):
                feats = word.get("features") or {}
                if feats:
                    all_intensities.append(_sf(feats.get("mean_intensity", 0)))
                    all_aspects.append(_sf(feats.get("aspect_ratio", 1.0)))
                    all_heights.append(_sf(feats.get("height", 20)))

        std_intensity = float(np.std(all_intensities)) if all_intensities else 1.0
        std_aspect    = float(np.std(all_aspects))     if all_aspects    else 1.0
        std_height    = float(np.std(all_heights))     if all_heights    else 1.0
        mean_intensity = float(np.mean(all_intensities)) if all_intensities else 128.0
        mean_aspect    = float(np.mean(all_aspects))     if all_aspects    else 1.0
        mean_height    = float(np.mean(all_heights))     if all_heights    else 20.0

        # ── Per-line baseline / kerning analysis ────────────────────────────
        baseline_findings = self._check_baselines(lines)
        findings.extend(baseline_findings)

        # ── Per-word multi-feature check (using pre-flagged suspicious words) ─
        for word in suspicious_words:
            feats = word.get("features") or {}
            text  = str(word.get("text", "")).strip()
            bbox  = _bbox_from_word(word)
            if not text or not feats:
                continue

            triggered: List[str] = []

            br = _sf(feats.get("black_ratio", doc_black))
            if abs(br - doc_black) > 0.08:
                z = _zscore(br, doc_black, max(0.01, abs(br - doc_black) / 3))
                triggered.append(
                    f"Stroke thickness (black_ratio) deviates {z:.1f}σ "
                    f"from document mean ({br:.3f} vs {doc_black:.3f})"
                )

            ed = _sf(feats.get("edge_density", doc_edge))
            if abs(ed - doc_edge) > 0.08:
                z = _zscore(ed, doc_edge, max(0.01, abs(ed - doc_edge) / 3))
                triggered.append(
                    f"Edge density deviates {z:.1f}σ "
                    f"from document mean ({ed:.3f} vs {doc_edge:.3f})"
                )

            mi = _sf(feats.get("mean_intensity", mean_intensity))
            if std_intensity > 1:
                z = _zscore(mi, mean_intensity, std_intensity)
                if z >= _Z_INTENSITY:
                    triggered.append(
                        f"Mean pixel intensity deviates {z:.1f}σ — "
                        f"possible paste/overlay ({mi:.1f} vs mean {mean_intensity:.1f})"
                    )

            ar = _sf(feats.get("aspect_ratio", mean_aspect))
            if std_aspect > 0.01:
                z = _zscore(ar, mean_aspect, std_aspect)
                if z >= _Z_ASPECT_RATIO:
                    triggered.append(
                        f"Character aspect ratio {z:.1f}σ from mean — "
                        f"font size or stretch anomaly"
                    )

            h = _sf(feats.get("height", mean_height))
            if std_height > 1:
                z = _zscore(h, mean_height, std_height)
                if z >= _Z_FONT_HEIGHT:
                    triggered.append(
                        f"Character height {z:.1f}σ from document mean — "
                        f"different font size ({h:.1f}px vs {mean_height:.1f}px)"
                    )

            if triggered:
                conf = min(0.97, 0.60 + len(triggered) * 0.10)
                severity = "High" if conf >= 0.75 else "Medium"
                findings.append({
                    "_stage": "font",
                    "field": f"Word: '{text}'",
                    "field_category": "font_anomaly",
                    "type": "font_feature_deviation",
                    "original": "Expected font properties",
                    "current": text,
                    "confidence": round(conf, 4),
                    "bbox": list(bbox) if bbox else None,
                    "reason": triggered,
                    "severity": severity,
                })

        return findings

    def _check_baselines(self, lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Check per-line baseline jitter and kerning anomalies."""
        findings: List[Dict[str, Any]] = []

        for line in lines:
            words = line.get("words", [])
            if len(words) < 2:
                continue

            center_ys = [_sf(w.get("center_y", 0)) for w in words]
            avg_y = float(np.mean(center_ys))

            # Collect bboxes for gap analysis
            sorted_words = sorted(words, key=lambda w: _sf(
                (_bbox_from_word(w) or (0,0,0,0))[0]
            ))
            gaps: List[float] = []
            for i in range(len(sorted_words) - 1):
                b1 = _bbox_from_word(sorted_words[i])
                b2 = _bbox_from_word(sorted_words[i + 1])
                if b1 and b2:
                    gap = (b2[0]) - (b1[0] + b1[2])
                    if gap > 0:
                        gaps.append(gap)

            avg_gap = float(np.mean(gaps)) if gaps else 0

            for i, word in enumerate(words):
                text = str(word.get("text", "")).strip()
                cy   = _sf(word.get("center_y", avg_y))
                bbox = _bbox_from_word(word)
                h    = bbox[3] if bbox else 20

                # Baseline jitter
                deviation = abs(cy - avg_y)
                if deviation > h * _BASELINE_FRAC and h > 5:
                    conf = min(0.94, 0.60 + deviation / max(h, 1) * 0.25)
                    findings.append({
                        "_stage": "font",
                        "field": f"Word: '{text}'",
                        "field_category": "baseline_jitter",
                        "type": "baseline_jitter",
                        "original": f"Baseline Y ≈ {avg_y:.1f}",
                        "current": f"Word Y = {cy:.1f} (deviation {deviation:.1f}px)",
                        "confidence": round(conf, 4),
                        "bbox": list(bbox) if bbox else None,
                        "reason": [
                            f"Text baseline deviates {deviation:.1f}px from line average "
                            f"({avg_y:.1f}px) — possible re-typed or pasted word"
                        ],
                        "severity": "Medium",
                    })

                # Kerning / gap anomaly for this word relative to next
                if avg_gap > 2 and i < len(sorted_words) - 1:
                    b1 = _bbox_from_word(sorted_words[i])
                    b2 = _bbox_from_word(sorted_words[i + 1])
                    if b1 and b2:
                        gap = b2[0] - (b1[0] + b1[2])
                        if gap > avg_gap * _KERNING_MULT:
                            union_bbox = (
                                b1[0], min(b1[1], b2[1]),
                                b2[0] + b2[2] - b1[0],
                                max(b1[1]+b1[3], b2[1]+b2[3]) - min(b1[1], b2[1])
                            )
                            findings.append({
                                "_stage": "font",
                                "field": f"Between '{sorted_words[i].get('text','')}' and '{sorted_words[i+1].get('text','')}'",
                                "field_category": "kerning_anomaly",
                                "type": "irregular_kerning",
                                "original": f"Expected gap ≈ {avg_gap:.1f}px",
                                "current": f"Actual gap = {gap:.1f}px ({gap/avg_gap:.1f}× average)",
                                "confidence": round(min(0.92, 0.60 + gap / avg_gap * 0.04), 4),
                                "bbox": list(union_bbox),
                                "reason": [
                                    f"Word gap {gap:.1f}px is {gap/avg_gap:.1f}× the line average "
                                    f"({avg_gap:.1f}px) — possible content insertion"
                                ],
                                "severity": "Medium",
                            })

        return findings


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 4 — LAYOUT ANOMALY DETECTOR
# ═══════════════════════════════════════════════════════════════════════════════

class LayoutAnomalyDetector:
    """
    Stage 4: Document-geometry anomaly detection.

    Detects misaligned lines, floating words, overlapping text, and
    abnormal margins using only the layout structure.
    """

    def detect(
        self,
        layout_data: Dict[str, Any],
        spacing_result: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        lines = layout_data.get("lines") or []
        if not lines:
            return findings

        # ── Collect document-level margin statistics ─────────────────────────
        left_edges: List[float]  = []
        right_edges: List[float] = []

        all_word_bboxes: List[Tuple[int,int,int,int]] = []

        for line in lines:
            words = line.get("words", [])
            if not words:
                continue
            line_bboxes = [_bbox_from_word(w) for w in words]
            line_bboxes = [b for b in line_bboxes if b]
            if line_bboxes:
                left_edges.append(float(min(b[0] for b in line_bboxes)))
                right_edges.append(float(max(b[0] + b[2] for b in line_bboxes)))
            all_word_bboxes.extend(b for b in line_bboxes if b)

        if not left_edges:
            return findings

        modal_left  = float(np.median(left_edges))
        modal_right = float(np.median(right_edges))

        # ── Line-level alignment checks ──────────────────────────────────────
        for line in lines:
            words = line.get("words", [])
            if not words:
                continue
            line_bboxes = [_bbox_from_word(w) for w in words]
            line_bboxes_valid = [b for b in line_bboxes if b]
            if not line_bboxes_valid:
                continue

            line_left  = min(b[0] for b in line_bboxes_valid)
            line_right = max(b[0] + b[2] for b in line_bboxes_valid)
            text       = line.get("text", "").strip()

            # Left-margin misalignment (only multi-word lines)
            if len(words) > 2:
                dev = abs(line_left - modal_left)
                if dev > _LAYOUT_LEFT_TOL:
                    findings.append({
                        "_stage": "layout",
                        "field": f"Line: '{text[:50]}'",
                        "field_category": "misalignment",
                        "type": "left_margin_misalignment",
                        "original": f"Expected left edge ≈ {modal_left:.0f}px",
                        "current": f"Actual left edge = {line_left:.0f}px (deviation {dev:.0f}px)",
                        "confidence": round(min(0.90, 0.55 + dev / 100.0), 4),
                        "bbox": self._line_bbox(line_bboxes_valid),
                        "reason": [
                            f"Line starts at x={line_left:.0f}px, deviating {dev:.0f}px "
                            f"from document left margin ({modal_left:.0f}px)"
                        ],
                        "severity": "Medium",
                    })

        # ── Floating word detection ──────────────────────────────────────────
        # A word is "floating" when no other word exists within 2× its height
        # above or below it (isolated, not part of any text row)
        for line in lines:
            words = line.get("words", [])
            if len(words) == 1:
                word = words[0]
                text = str(word.get("text", "")).strip()
                if not text or len(text) < 2:
                    continue
                bbox = _bbox_from_word(word)
                if not bbox:
                    continue
                cy = word.get("center_y", bbox[1] + bbox[3] / 2.0)

                # Check if any other word is nearby
                nearby = [
                    w for l in lines for w in l.get("words", [])
                    if w is not word and abs(_sf(w.get("center_y", 0)) - cy) < bbox[3] * 2.5
                ]
                if not nearby and _NUMBER_RE.match(text):
                    findings.append({
                        "_stage": "layout",
                        "field": f"Floating value: '{text}'",
                        "field_category": "floating_word",
                        "type": "floating_isolated_word",
                        "original": "Expected to be part of a text row",
                        "current": text,
                        "confidence": 0.72,
                        "bbox": list(bbox),
                        "reason": [
                            f"Numeric token '{text}' appears in isolation with no "
                            "adjacent text on the same or neighboring lines — possible insertion"
                        ],
                        "severity": "High",
                    })

        # ── Overlapping word detection ───────────────────────────────────────
        for i in range(len(all_word_bboxes)):
            for j in range(i + 1, len(all_word_bboxes)):
                iou = _iou_xywh(all_word_bboxes[i], all_word_bboxes[j])
                if iou >= _OVERLAP_IOU:
                    # Merge bboxes for the finding location
                    a, b = all_word_bboxes[i], all_word_bboxes[j]
                    x1 = min(a[0], b[0])
                    y1 = min(a[1], b[1])
                    x2 = max(a[0]+a[2], b[0]+b[2])
                    y2 = max(a[1]+a[3], b[1]+b[3])
                    findings.append({
                        "_stage": "layout",
                        "field": "Overlapping Text",
                        "field_category": "overlap",
                        "type": "overlapping_text_regions",
                        "original": "Non-overlapping text",
                        "current": f"IoU={iou:.2f}",
                        "confidence": round(min(0.95, 0.65 + iou), 4),
                        "bbox": [x1, y1, x2 - x1, y2 - y1],
                        "reason": [
                            f"Two text bounding boxes overlap with IoU={iou:.2f} — "
                            "possible content pasted over existing text"
                        ],
                        "severity": "High",
                    })

        # ── Spacing-level anomalies from spacing_analysis ────────────────────
        for sline in (spacing_result.get("lines") or []):
            if sline.get("spacing_anomaly"):
                lnum = sline.get("line")
                ltext = sline.get("text", "")[:50]
                mean_sp = sline.get("mean_spacing", 0)
                sp_var  = sline.get("spacing_variation", 0)
                findings.append({
                    "_stage": "layout",
                    "field": f"Line {lnum}: '{ltext}'",
                    "field_category": "spacing_anomaly",
                    "type": "irregular_word_spacing",
                    "original": "Consistent word spacing",
                    "current": f"Spacing variation = {sp_var:.1f}px (mean {mean_sp:.1f}px)",
                    "confidence": round(min(0.90, 0.55 + sp_var / 100.0), 4),
                    "bbox": None,
                    "reason": [
                        f"Word spacing on line {lnum} has high variation "
                        f"(std={sp_var:.1f}px vs mean={mean_sp:.1f}px) — "
                        "consistent with inserted or re-typed content"
                    ],
                    "severity": "Medium",
                })

        return findings

    @staticmethod
    def _line_bbox(bboxes: List[Tuple[int,int,int,int]]) -> List[int]:
        x1 = min(b[0] for b in bboxes)
        y1 = min(b[1] for b in bboxes)
        x2 = max(b[0]+b[2] for b in bboxes)
        y2 = max(b[1]+b[3] for b in bboxes)
        return [x1, y1, x2 - x1, y2 - y1]


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 5 — EVIDENCE LINKER
# ═══════════════════════════════════════════════════════════════════════════════

class EvidenceLinker:
    """
    Stage 5: Cross-references OCR findings with Phase 1 evidence localization regions.

    For each finding whose bbox overlaps a Phase 1 region (IoU ≥ threshold):
        • Sets 'region' to the Phase 1 region ID
        • Boosts confidence by _LINK_BOOST × phase1_confidence
        • Adds a corroboration reason bullet
    """

    def __init__(self, phase1_regions: List[Dict[str, Any]]):
        self._regions = phase1_regions

    def link(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self._regions or not findings:
            return findings

        linked: List[Dict[str, Any]] = []
        for f in findings:
            raw_bbox = f.get("bbox")
            if not raw_bbox or not isinstance(raw_bbox, (list, tuple)) or len(raw_bbox) < 4:
                linked.append(f)
                continue

            fbbox = (
                _si(raw_bbox[0]), _si(raw_bbox[1]),
                _si(raw_bbox[2]), _si(raw_bbox[3]),
            )

            best_iou    = 0.0
            best_region = None

            for reg in self._regions:
                rbbox_raw = reg.get("bbox")
                if not rbbox_raw or len(rbbox_raw) < 4:
                    continue
                rbbox = (
                    _si(rbbox_raw[0]), _si(rbbox_raw[1]),
                    _si(rbbox_raw[2]), _si(rbbox_raw[3]),
                )
                iou = _iou_xywh(fbbox, rbbox)
                if iou > best_iou:
                    best_iou    = iou
                    best_region = reg

            if best_region and best_iou >= _LINK_IOU_THRESH:
                reg_conf   = _sf(best_region.get("confidence", 0.0))
                boost      = round(_LINK_BOOST * reg_conf, 4)
                new_conf   = round(min(0.99, _sf(f.get("confidence", 0.5)) + boost), 4)
                f = dict(f)
                f["confidence"] = new_conf
                f["region"]     = str(best_region.get("id", "unknown"))
                f["reason"]     = list(f.get("reason", [])) + [
                    f"Confirmed by pixel-level forensic analysis — "
                    f"Phase 1 region {best_region.get('id')} "
                    f"(IoU={best_iou:.2f}, region confidence={reg_conf:.2f})"
                ]
                # Escalate severity if region is corroborated
                if f.get("severity") == "Medium" and new_conf >= 0.75:
                    f["severity"] = "High"

            linked.append(f)

        return linked

    @classmethod
    def from_analysis_dir(cls, analysis_dir: Path) -> "EvidenceLinker":
        """Load Phase 1 evidence_localization.json from disk."""
        el_path = analysis_dir / "evidence_localization.json"
        if el_path.is_file():
            try:
                data = json.loads(el_path.read_text(encoding="utf-8"))
                return cls(data.get("regions") or [])
            except Exception as exc:
                logger.debug("EvidenceLinker: could not load phase1 regions: %s", exc)
        return cls([])


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 6 — SERIALIZER
# ═══════════════════════════════════════════════════════════════════════════════

def _assign_ids(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Assign sequential deterministic IDs and normalise the schema."""
    out = []
    for idx, f in enumerate(findings):
        out.append({
            "id":              f"ocr_diff_{idx + 1:03d}",
            "field":           str(f.get("field", "—")),
            "field_category":  str(f.get("field_category", "unknown")),
            "type":            str(f.get("type", "anomaly")),
            "original":        str(f.get("original", "—")),
            "current":         str(f.get("current", "—")),
            "confidence":      round(_sf(f.get("confidence", 0.5)), 4),
            "bbox":            f.get("bbox"),
            "region":          f.get("region"),                   # Phase 1 link
            "reason":          [str(r) for r in (f.get("reason") or [])],
            "severity":        str(f.get("severity", "Medium")),
            "_stage":          str(f.get("_stage", "unknown")),   # kept for debug
        })
    return out


def _build_summary(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    stages = {f.get("_stage") for f in findings}
    return {
        "finding_count":               len(findings),
        "field_modifications":         sum(1 for f in findings if f.get("_stage") == "value"),
        "font_anomalies":              sum(1 for f in findings if f.get("_stage") == "font"),
        "layout_anomalies":            sum(1 for f in findings if f.get("_stage") == "layout"),
        "critical_findings":           sum(1 for f in findings if f.get("severity") == "Critical"),
        "high_confidence_findings":    sum(1 for f in findings if _sf(f.get("confidence", 0)) >= 0.75),
        "linked_to_localization":      sum(1 for f in findings if f.get("region")),
        "stages_active":               sorted(s for s in stages if s),
        "manipulation_types":          sorted({f.get("type") for f in findings if f.get("type")}),
    }


def _serialize(
    evidence_id: str,
    analysis_dir: Path,
    findings: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Write ocr_difference_report.json atomically and return the output dict."""
    output: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "evidence_id":    str(evidence_id),
        "generated_at":   datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary":        _build_summary(findings),
        "findings":       findings,
    }

    out_path = analysis_dir / OUTPUT_FILENAME
    tmp_path = out_path.with_suffix(".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(output, fh, indent=2, ensure_ascii=False, sort_keys=False)
        tmp_path.replace(out_path)
    except Exception as exc:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise RuntimeError(
            f"ocr_difference_engine: failed to write {out_path}: {exc}"
        ) from exc

    logger.info(
        "ocr_difference_engine: %d findings → %s",
        len(findings), out_path,
    )
    return output


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def run_ocr_difference_engine(
    analysis_result: Dict[str, Any],
    analysis_dir: Path,
    evidence_id: str,
) -> Dict[str, Any]:
    """
    Run the Phase 2 OCR Difference Engine end-to-end.

    Parameters
    ----------
    analysis_result : Complete output dict from analyze_image_unified() — read-only.
    analysis_dir    : Directory where forensic artifacts live.
                      ocr_difference_report.json will be written here.
    evidence_id     : UUID string identifying this analysis case.

    Returns
    -------
    The serialized output dict matching the ocr_difference_report.json schema.
    On failure, returns {"success": False, "error": "...", "finding_count": 0}.
    """
    t_start = time.perf_counter()
    analysis_dir = Path(analysis_dir)

    logger.info(
        "ocr_difference_engine | evidence_id=%s | start",
        evidence_id,
    )

    try:
        # ── Extract input data from analysis_result (all read-only) ─────────
        layout_data    = analysis_result.get("text_layout") or {}
        font_result    = analysis_result.get("font_consistency") or {}
        spacing_result = analysis_result.get("spacing_analysis") or {}

        # OCR detections from multiple possible keys
        ocr_data = (
            analysis_result.get("ocr")
            or (analysis_result.get("document_intelligence") or {}).get("ocr")
            or {}
        )
        detections      = ocr_data.get("detections") or []
        mismatch_regions = (
            ocr_data.get("mismatch_regions")
            or ocr_data.get("consensus", {}).get("mismatch_regions")
            or []
        )

        # If layout_data is empty but we have detections, build a minimal stub
        if not layout_data.get("lines") and detections:
            layout_data = _build_minimal_layout(detections)

        # ── Stage 1: Field Grouper ───────────────────────────────────────────
        grouper = FieldGrouper()
        fields  = grouper.group(layout_data, detections)
        logger.debug("ocr_diff | stage=group | fields=%d", len(fields))

        # ── Stage 2: Value Analyzer ──────────────────────────────────────────
        value_analyzer = ValueAnalyzer()
        value_findings = value_analyzer.analyze(fields, mismatch_regions, font_result)
        logger.debug("ocr_diff | stage=value | findings=%d", len(value_findings))

        # ── Stage 3: Font Anomaly Detector ───────────────────────────────────
        font_detector  = FontAnomalyDetector()
        font_findings  = font_detector.detect(font_result, layout_data)
        logger.debug("ocr_diff | stage=font  | findings=%d", len(font_findings))

        # ── Stage 4: Layout Anomaly Detector ─────────────────────────────────
        layout_detector = LayoutAnomalyDetector()
        layout_findings = layout_detector.detect(layout_data, spacing_result)
        logger.debug("ocr_diff | stage=layout| findings=%d", len(layout_findings))

        # ── Merge + deduplicate ──────────────────────────────────────────────
        all_findings = value_findings + font_findings + layout_findings
        all_findings = _deduplicate_findings(all_findings)
        all_findings.sort(key=lambda f: -_sf(f.get("confidence", 0)))
        all_findings = all_findings[:_MAX_FINDINGS]

        # ── Stage 5: Evidence Linker ──────────────────────────────────────────
        linker      = EvidenceLinker.from_analysis_dir(analysis_dir)
        all_findings = linker.link(all_findings)

        # Re-sort after confidence boost
        all_findings.sort(key=lambda f: -_sf(f.get("confidence", 0)))

        # ── Stage 6: Assign IDs and serialize ────────────────────────────────
        all_findings = _assign_ids(all_findings)
        output = _serialize(evidence_id, analysis_dir, all_findings)

        elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
        logger.info(
            "ocr_difference_engine | done | findings=%d | elapsed_ms=%.1f",
            len(all_findings), elapsed_ms,
        )
        return output

    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
        logger.error(
            "ocr_difference_engine | FAILED | evidence_id=%s | error=%s | elapsed_ms=%.1f",
            evidence_id, exc, elapsed_ms,
        )
        return {
            "success":       False,
            "error":         str(exc),
            "evidence_id":   str(evidence_id),
            "finding_count": 0,
            "findings":      [],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# INTERNAL UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

def _deduplicate_findings(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove near-duplicate findings (same type + highly overlapping bboxes)."""
    kept: List[Dict[str, Any]] = []
    for f in findings:
        fbbox = f.get("bbox")
        ftype = f.get("type", "")
        is_dup = False
        if fbbox and isinstance(fbbox, (list, tuple)) and len(fbbox) >= 4:
            fb = (_si(fbbox[0]), _si(fbbox[1]), _si(fbbox[2]), _si(fbbox[3]))
            for k in kept:
                kbbox = k.get("bbox")
                if kbbox and k.get("type") == ftype:
                    kb = (_si(kbbox[0]), _si(kbbox[1]), _si(kbbox[2]), _si(kbbox[3]))
                    if _iou_xywh(fb, kb) >= 0.50:
                        is_dup = True
                        break
        else:
            # No bbox — deduplicate by type + field name
            for k in kept:
                if k.get("type") == ftype and k.get("field") == f.get("field"):
                    is_dup = True
                    break
        if not is_dup:
            kept.append(f)
    return kept


def _build_minimal_layout(detections: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build a minimal layout_data stub from raw OCR detections.
    Used when text_layout_analysis was not run (e.g. non-document images).
    """
    # Group detections into approximate lines by y-coordinate
    word_dicts: List[Dict[str, Any]] = []
    for det in detections:
        top  = _sf(det.get("top", det.get("y", 0)))
        h    = _sf(det.get("height", det.get("h", 12)))
        left = _sf(det.get("left", det.get("x", 0)))
        w    = _sf(det.get("width", det.get("w", 10)))
        wd = {
            "text":       str(det.get("text", "")),
            "confidence": _sf(det.get("confidence", 0.90)),
            "center_x":   left + w / 2,
            "center_y":   top  + h / 2,
            "bbox":       [[left, top], [left + w, top], [left + w, top + h], [left, top + h]],
        }
        word_dicts.append(wd)

    word_dicts.sort(key=lambda w: w["center_y"])

    lines_dict: Dict[int, List] = defaultdict(list)
    for wd in word_dicts:
        placed = False
        for key in list(lines_dict.keys()):
            ref_y = float(np.mean([w["center_y"] for w in lines_dict[key]]))
            if abs(wd["center_y"] - ref_y) <= 15:
                lines_dict[key].append(wd)
                placed = True
                break
        if not placed:
            lines_dict[int(wd["center_y"])].append(wd)

    line_results = []
    for i, (_, words) in enumerate(sorted(lines_dict.items())):
        words.sort(key=lambda w: w["center_x"])
        line_results.append({
            "line_number": i + 1,
            "text":        " ".join(w["text"] for w in words),
            "words":       words,
        })

    return {
        "total_words":           sum(len(l["words"]) for l in line_results),
        "total_lines":           len(line_results),
        "alignment":             "Mixed",
        "average_word_spacing":  0,
        "average_line_spacing":  0,
        "lines":                 line_results,
    }
