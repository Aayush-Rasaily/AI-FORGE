"""
Document forensic analysis service.

Supports PDF and DOCX with validation, parallel page processing,
and graceful error handling. Never passes PDF directly to OpenCV.
"""

from __future__ import annotations

import logging
import os
import zipfile
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.agents.ocr_agent import extract_text
from backend.document_analysis.document_intelligence import (
    analyze_page_intelligence,
    detect_missing_pages,
)
from backend.document_analysis.heatmap_generator import generate_heatmap
from backend.document_analysis.risk_engine import analyze_document_risk
from backend.ingestion.pdf_processor import pdf_to_images, get_text_pages, get_embedded_text_page
from backend.utils.errors import DocumentAnalysisError
from backend.utils.file_hash import compute_file_hash
from backend.utils.image_utils import is_document_file, validate_path
from backend.utils.performance_config import PDF_PARALLEL_PAGES
from backend.utils.progress import ProgressTracker
from backend.utils.redis_cache import cache_key, get_redis_cache
from backend.utils.timing import ModuleTimer

logger = logging.getLogger("ai_forge.document")

DOCX_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
MAX_PARALLEL_PAGES = PDF_PARALLEL_PAGES


def analyze_document(
    document_path: str,
    evidence_id: Optional[str] = None,
    progress: Optional[ProgressTracker] = None,
) -> Dict[str, Any]:
    """
    Analyze a PDF or DOCX document.

    Parameters
    ----------
    document_path : str
        Path to uploaded document file.
    evidence_id : str, optional
        Evidence identifier for logging.
    """
    path = validate_path(Path(document_path))
    suffix = path.suffix.lower()

    print("Evidence:", evidence_id or path.stem)
    print("Resolved Path:", path)
    print("Exists:", os.path.exists(path))
    print("Suffix:", suffix)

    if not is_document_file(path):
        raise DocumentAnalysisError(
            f"Unsupported document type: {suffix}",
            details="Supported formats: PDF, DOCX",
        )

    timer = ModuleTimer("Document Analysis")

    if suffix == ".pdf":
        with timer.track("pdf_analysis"):
            if progress:
                progress.emit("pdf_render", "running")
            result = _analyze_pdf(path, evidence_id, progress)
            if progress:
                progress.emit("pdf_render", "completed")
    elif suffix == ".docx":
        with timer.track("docx_analysis"):
            if progress:
                progress.emit("ocr", "running")
            result = _analyze_docx(path, evidence_id)
            if progress:
                progress.emit("ocr", "completed")
    elif suffix == ".doc":
        raise DocumentAnalysisError(
            "Legacy .doc format is not supported.",
            details="Please convert to PDF or DOCX and re-upload.",
        )
    else:
        raise DocumentAnalysisError(f"Unsupported document type: {suffix}")

    result["timing"] = timer.log_summary()
    return result


def _analyze_pdf(
    pdf_path: Path,
    evidence_id: Optional[str],
    progress: Optional[ProgressTracker] = None,
) -> Dict[str, Any]:
    output_dir = pdf_path.parent / "document_pages" / pdf_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        page_images = pdf_to_images(str(pdf_path), str(output_dir))
    except OSError as exc:
        raise DocumentAnalysisError(
            "Failed to convert PDF to images.",
            details=str(exc),
        ) from exc
    except Exception as exc:
        raise DocumentAnalysisError(
            "PDF conversion failed.",
            details=str(exc),
        ) from exc

    if not page_images:
        raise DocumentAnalysisError(
            "PDF contains no readable pages.",
            details="The document may be encrypted or corrupted.",
        )

    # Validate page image paths before processing
    validated_pages: List[str] = []
    for img_path in page_images:
        p = Path(img_path)
        if not p.exists() or p.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            logger.warning("Skipping invalid page image: %s", img_path)
            continue
        validated_pages.append(str(p.resolve()))

    if not validated_pages:
        raise DocumentAnalysisError(
            "No valid page images were generated from PDF.",
        )

    text_pages_list = get_text_pages(str(output_dir), str(pdf_path))
    if text_pages_list:
        ocr_page_nums = {p for p, _ in text_pages_list}
    else:
        ocr_page_nums = set()

    pages = _process_pages_parallel(
        validated_pages,
        output_dir,
        doc_type="PDF",
        doc_name=pdf_path.name,
        ocr_pages=ocr_page_nums,
        progress=progress,
        source_pdf=str(pdf_path),
    )

    page_texts = [
        (p.get("ocr") or {}).get("full_text")
        or (p.get("ocr") or {}).get("text")
        or ""
        for p in pages
    ]
    missing_pages_info = detect_missing_pages(
        page_count=len(pages),
        page_texts=page_texts,
    )
    return _build_document_result("PDF", pdf_path.name, pages, missing_pages_info)


def _analyze_docx(docx_path: Path, evidence_id: Optional[str]) -> Dict[str, Any]:
    """DOCX: extract text and layout — skip image-only forensic modules."""
    try:
        text_content = _extract_docx_text(docx_path)
    except Exception as exc:
        raise DocumentAnalysisError(
            "Failed to read DOCX file.",
            details=str(exc),
        ) from exc

    word_count = len(text_content.split())
    lines = [ln for ln in text_content.splitlines() if ln.strip()]

    spacing_issues = 0
    for i in range(1, len(lines)):
        if abs(len(lines[i]) - len(lines[i - 1])) > 40:
            spacing_issues += 1

    layout_risk = min(100, spacing_issues * 8)
    risk_score = layout_risk

    if word_count < 5:
        risk_score = max(risk_score, 20)

    verdict = _verdict_from_score(risk_score)
    findings: List[Dict[str, Any]] = []
    if spacing_issues > 2:
        findings.append({
            "module": "layout",
            "what": f"Irregular line length patterns detected ({spacing_issues} anomalies).",
            "severity": "medium",
        })

    page_result = {
        "page_number": 1,
        "image": None,
        "ocr": {
            "text": text_content[:5000],
            "word_count": word_count,
            "source": "docx_extraction",
        },
        "risk": {
            "risk_score": risk_score,
            "confidence": 0.75,
            "overall_verdict": verdict,
            "findings": findings,
            "raw_analysis": {"docx": True, "spacing_issues": spacing_issues},
        },
        "heatmap": None,
    }

    return _build_document_result("DOCX", docx_path.name, [page_result])


def _extract_docx_text(docx_path: Path) -> str:
    with zipfile.ZipFile(docx_path, "r") as archive:
        if "word/document.xml" not in archive.namelist():
            raise DocumentAnalysisError("Invalid DOCX: missing document.xml")
        xml_data = archive.read("word/document.xml")

    root = ET.fromstring(xml_data)
    texts: List[str] = []
    for node in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"):
        if node.text:
            texts.append(node.text)
    return "\n".join(texts)


def _process_single_page(
    image_path: str,
    page_number: int,
    output_dir: Path,
    run_ocr: bool = True,
    pdf_path: Optional[str] = None,
    progress: Optional[ProgressTracker] = None,
) -> Dict[str, Any]:
    """Process one PDF page — OCR (if text detected), risk, heatmap."""
    image_path = str(Path(image_path).resolve())
    if not os.path.exists(image_path):
        raise DocumentAnalysisError(f"Page image not found: {image_path}")

    redis = get_redis_cache()
    page_hash = compute_file_hash(Path(image_path))
    pkey = cache_key("pdf_page", page_hash, f"p{page_number}")
    cached = redis.get(pkey)
    if cached and cached.get("page"):
        return cached["page"]

    page_analysis_dir = output_dir / f"page_{page_number}"
    page_analysis_dir.mkdir(parents=True, exist_ok=True)

    embedded = get_embedded_text_page(pdf_path, page_number) if pdf_path else None
    if embedded:
        ocr_result = {
            "text": embedded[:5000],
            "full_text": embedded,
            "word_count": len(embedded.split()),
            "source": "pymupdf_embedded",
            "skipped_ocr": True,
        }
    elif run_ocr:
        def _ocr_progress(module: str, status: str, elapsed: float = 0.0):
            if progress:
                progress.emit(module, status, elapsed=elapsed)

        ocr_result = extract_text(
            image_path,
            analysis_dir=str(page_analysis_dir),
            progress=_ocr_progress,
        )
        # Attach visualization paths for frontend
        if ocr_result.get("visualizations"):
            ocr_result["artifacts"] = ocr_result["visualizations"]
    else:
        ocr_result = {"text": "", "word_count": 0, "skipped": True, "reason": "no_text_detected"}

    risk_result = analyze_document_risk(image_path, str(page_analysis_dir))

    if progress:
        progress.emit("layoutlmv3", "running")
    intelligence = analyze_page_intelligence(
        image_path,
        ocr_result,
        risk_result,
        str(page_analysis_dir),
    )
    if progress:
        progress.emit("layoutlmv3", "completed")
        progress.emit("donut", "completed")
        progress.emit("document_intelligence", "completed")

    raw_analysis = risk_result.get("raw_analysis", {}) or {}
    region_analysis = raw_analysis.get("regions", {}) or {}
    regions = region_analysis.get("regions", []) or []

    normalized_regions = []
    for region in regions:
        r = dict(region)
        if "risk_score" not in r and "score" in r:
            r["risk_score"] = r["score"]
        normalized_regions.append(r)

    heatmap_result = None
    try:
        heatmap_result = generate_heatmap(
            image_path, normalized_regions, str(page_analysis_dir)
        )
    except Exception as exc:
        logger.warning("Heatmap failed for page %s: %s", page_number, exc)

    page_result = {
        "page_number": page_number,
        "image": image_path,
        "ocr": ocr_result,
        "risk": risk_result,
        "heatmap": heatmap_result,
        "intelligence": intelligence,
        "page_confidence": intelligence.get("page_confidence"),
        "page_confidence_pct": intelligence.get("page_confidence_pct"),
        "issues": intelligence.get("issues", []),
    }
    redis.set(pkey, {"page": page_result})
    return page_result


def _process_pages_parallel(
    page_images: List[str],
    output_dir: Path,
    doc_type: str,
    doc_name: str,
    ocr_pages: Optional[set] = None,
    progress: Optional[ProgressTracker] = None,
    source_pdf: Optional[str] = None,
) -> List[Dict[str, Any]]:
    pages: List[Optional[Dict[str, Any]]] = [None] * len(page_images)
    workers = min(MAX_PARALLEL_PAGES, len(page_images))
    ocr_pages = ocr_pages or set(range(1, len(page_images) + 1))

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                _process_single_page,
                img,
                idx + 1,
                output_dir,
                (idx + 1) in ocr_pages,
                str(source_pdf) if doc_type == "PDF" else None,
                progress,
            ): idx
            for idx, img in enumerate(page_images)
        }
        completed = 0
        for future in as_completed(futures):
            idx = futures[future]
            try:
                pages[idx] = future.result()
            except Exception as exc:
                logger.error("Page %s failed: %s", idx + 1, exc)
                pages[idx] = {
                    "page_number": idx + 1,
                    "image": page_images[idx],
                    "ocr": {"error": str(exc)},
                    "risk": {
                        "risk_score": 0,
                        "confidence": 0,
                        "overall_verdict": "PAGE ANALYSIS FAILED",
                        "findings": [],
                    },
                    "heatmap": None,
                }
            completed += 1
            if progress:
                progress.emit(
                    "region",
                    "running",
                    extra={"page": idx + 1, "completed": completed, "total": len(page_images)},
                )

    if progress:
        progress.emit("region", "completed")
        progress.emit("fusion", "completed")

    return [p for p in pages if p is not None]


def _build_document_result(
    doc_type: str,
    doc_name: str,
    pages: List[Dict[str, Any]],
    missing_pages_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if pages:
        page_scores = [
            float(p.get("risk", {}).get("risk_score", 0) or 0)
            for p in pages
        ]
        document_risk = round(min(max(page_scores) * 0.70 + (sum(page_scores) / len(page_scores)) * 0.30, 100), 2)
    else:
        document_risk = 0.0

    page_confidences = [
        {
            "page_number": p.get("page_number"),
            "confidence": p.get("page_confidence"),
            "confidence_pct": p.get("page_confidence_pct"),
            "issue_count": len(p.get("issues") or []),
        }
        for p in pages
    ]

    document_findings: List[Dict[str, Any]] = []
    for page in pages:
        for finding in page.get("risk", {}).get("findings", []) or []:
            document_findings.append({"page": page["page_number"], **finding})
        for issue in page.get("issues") or []:
            document_findings.append({
                "page": page["page_number"],
                "module": "document_intelligence",
                "what": issue.get("description", issue.get("type", "Anomaly detected")),
                "severity": issue.get("severity", "medium"),
                "type": issue.get("type"),
                "score": issue.get("score"),
            })

    missing_pages_info = missing_pages_info or detect_missing_pages(len(pages))
    if missing_pages_info.get("missing_page_detected"):
        document_findings.append({
            "page": None,
            "module": "missing_pages",
            "what": f"Possible missing pages detected: {missing_pages_info.get('missing_pages', [])}",
            "severity": "high",
        })

    avg_confidence = (
        round(sum(c["confidence"] or 0 for c in page_confidences) / len(page_confidences), 4)
        if page_confidences else 0.0
    )

    return {
        "document_type": doc_type,
        "document_name": doc_name,
        "page_count": len(pages),
        "risk_score": document_risk,
        "overall_verdict": _verdict_from_score(document_risk),
        "pages": pages,
        "findings": document_findings,
        "page_confidences": page_confidences,
        "document_confidence": avg_confidence,
        "document_confidence_pct": round(avg_confidence * 100, 2),
        "missing_pages": missing_pages_info,
        "models": {
            "layoutlmv3": "microsoft/layoutlmv3-base",
            "donut": "naver-clova-ix/donut-base-finetuned-cord-v2",
        },
    }


def _verdict_from_score(score: float) -> str:
    if score >= 80:
        return "CRITICAL RISK"
    if score >= 60:
        return "HIGH RISK"
    if score >= 35:
        return "MEDIUM RISK"
    if score >= 15:
        return "LOW RISK"
    return "NO SIGNIFICANT ANOMALY"
