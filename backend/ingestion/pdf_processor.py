"""
Optimized PDF processing — cached renders, low-res preview, smart page OCR.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import fitz
import numpy as np

from backend.utils.module_registry import likely_contains_text

logger = logging.getLogger("ai_forge.pdf")

MANIFEST_NAME = "page_manifest.json"
PREVIEW_MATRIX = fitz.Matrix(1.0, 1.0)  # Fast low-res
ANALYSIS_MATRIX = fitz.Matrix(1.5, 1.5)  # Balanced quality/speed
JPEG_QUALITY = 85


def _manifest_path(output_dir: Path) -> Path:
    return output_dir / MANIFEST_NAME


def _load_manifest(output_dir: Path) -> Optional[Dict]:
    path = _manifest_path(output_dir)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _save_manifest(output_dir: Path, manifest: Dict) -> None:
    with open(_manifest_path(output_dir), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def pdf_to_images(
    pdf_path: str,
    output_dir: str,
    force_refresh: bool = False,
) -> List[str]:
    """
    Render PDF pages with caching. Returns paths to analysis-resolution JPEGs.
    Never re-renders pages already in manifest.
    """
    pdf_path = Path(pdf_path).resolve()
    output_dir = Path(output_dir).resolve()

    if not pdf_path.is_file() or pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Not a valid PDF: {pdf_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    if not force_refresh:
        manifest = _load_manifest(output_dir)
        if manifest and manifest.get("pages"):
            paths = [p["analysis_path"] for p in manifest["pages"] if Path(p["analysis_path"]).exists()]
            if len(paths) == manifest.get("page_count", 0):
                logger.info("PDF page cache hit: %s (%d pages)", pdf_path.name, len(paths))
                return paths

    document = fitz.open(str(pdf_path))
    pages_manifest: List[Dict[str, Any]] = []
    image_paths: List[str] = []

    for page_number in range(len(document)):
        page = document[page_number]
        stem = f"{pdf_path.stem}_page_{page_number + 1}"

        preview_path = output_dir / f"{stem}_preview.jpg"
        analysis_path = output_dir / f"{stem}.jpg"

        # Low-res preview for text detection
        if not preview_path.exists():
            preview_pix = page.get_pixmap(matrix=PREVIEW_MATRIX)
            preview_path.write_bytes(_compress_pixmap(preview_pix))

        has_text = likely_contains_text(str(preview_path))

        # Analysis resolution — JPEG for smaller I/O
        if not analysis_path.exists():
            analysis_pix = page.get_pixmap(matrix=ANALYSIS_MATRIX)
            analysis_path.write_bytes(_compress_pixmap(analysis_pix))

        pages_manifest.append({
            "page_number": page_number + 1,
            "preview_path": str(preview_path.resolve()),
            "analysis_path": str(analysis_path.resolve()),
            "has_text": has_text,
        })
        image_paths.append(str(analysis_path.resolve()))

    document.close()

    _save_manifest(output_dir, {
        "source": str(pdf_path),
        "page_count": len(image_paths),
        "pages": pages_manifest,
    })

    return image_paths


def extract_embedded_text_pages(pdf_path: str) -> Dict[int, str]:
    """
    Extract embedded text per page via PyMuPDF.
    Returns {page_number: text} for pages with sufficient embedded text.
    """
    document = fitz.open(str(pdf_path))
    pages: Dict[int, str] = {}
    for i in range(len(document)):
        text = (document[i].get_text("text") or "").strip()
        if len(text.split()) >= 5:
            pages[i + 1] = text
    document.close()
    return pages


def get_embedded_text_page(pdf_path: str, page_number: int) -> Optional[str]:
    pages = extract_embedded_text_pages(pdf_path)
    return pages.get(page_number)


def get_text_pages(output_dir: str, pdf_path: Optional[str] = None) -> List[Tuple[int, str]]:
    """
    Return pages needing OCR.
    Skips pages with embedded PyMuPDF text when pdf_path is provided.
    """
    if pdf_path:
        embedded = extract_embedded_text_pages(pdf_path)
        manifest = _load_manifest(Path(output_dir))
        if manifest:
            ocr_pages = []
            for p in manifest.get("pages", []):
                page_num = p["page_number"]
                if page_num in embedded:
                    text_path = Path(output_dir) / f"page_{page_num}_embedded.txt"
                    if not text_path.exists():
                        text_path.write_text(embedded[page_num], encoding="utf-8")
                    continue
                if p.get("has_text", True):
                    ocr_pages.append((page_num, p["analysis_path"]))
            return ocr_pages

    manifest = _load_manifest(Path(output_dir))
    if not manifest:
        return []
    return [
        (p["page_number"], p["analysis_path"])
        for p in manifest.get("pages", [])
        if p.get("has_text", True)
    ]


def _compress_pixmap(pixmap: fitz.Pixmap) -> bytes:
    """Convert pixmap to JPEG bytes for smaller disk footprint."""
    img = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.height, pixmap.width, pixmap.n)
    if pixmap.n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    elif pixmap.n == 1:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    else:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    return buf.tobytes() if ok else pixmap.tobytes()
