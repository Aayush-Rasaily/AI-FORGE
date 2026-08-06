"""
Run all OCR engines in parallel with per-engine timeout.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional

from backend.ocr.engines.easyocr_engine import run_easyocr
from backend.ocr.engines.paddle_engine import run_paddleocr
from backend.ocr.engines.tesseract_engine import run_tesseract
from backend.ocr.engines.trocr_engine import run_trocr

logger = logging.getLogger("ai_forge.multi_ocr")

ENGINE_TIMEOUT_SEC = 5.0

OCR_ENGINES: Dict[str, Callable[[str], Dict[str, Any]]] = {
    "tesseract": run_tesseract,
    "easyocr": run_easyocr,
    "paddleocr": run_paddleocr,
    "trocr": run_trocr,
}


def run_all_engines(
    image_path: str,
    timeout: float = ENGINE_TIMEOUT_SEC,
    progress: Optional[Callable[[str, str, float], None]] = None,
) -> Dict[str, Any]:
    """Execute all OCR engines concurrently; each engine capped at `timeout` seconds."""
    results: Dict[str, Dict[str, Any]] = {}
    fastest: Optional[Dict[str, Any]] = None

    def _emit(name: str, status: str, elapsed: float = 0.0):
        if progress:
            progress(name, status, elapsed)

    with ThreadPoolExecutor(max_workers=len(OCR_ENGINES)) as executor:
        futures = {executor.submit(fn, image_path): name for name, fn in OCR_ENGINES.items()}
        for future in as_completed(futures):
            name = futures[future]
            _emit(f"ocr_{name}", "running")
            try:
                result = future.result(timeout=timeout)
                results[name] = result
                if result.get("success"):
                    if fastest is None or result.get("elapsed_ms", 99999) < fastest.get("elapsed_ms", 99999):
                        fastest = result
                    _emit(f"ocr_{name}", "completed", result.get("elapsed_ms", 0) / 1000.0)
                else:
                    _emit(f"ocr_{name}", "failed")
            except Exception as exc:
                logger.warning("OCR engine %s timed out or failed: %s", name, exc)
                results[name] = {
                    "engine": name,
                    "success": False,
                    "error": str(exc),
                    "full_text": "",
                    "detections": [],
                    "character_confidence": 0.0,
                    "word_confidence": 0.0,
                    "layout_confidence": 0.0,
                }
                _emit(f"ocr_{name}", "failed")

    succeeded = [n for n, r in results.items() if r.get("success")]
    return {
        "engine_results": results,
        "engines_run": list(OCR_ENGINES.keys()),
        "engines_succeeded": succeeded,
        "fastest_engine": fastest.get("engine") if fastest else None,
        "fastest_result": fastest,
    }
