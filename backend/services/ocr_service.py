"""
Unified OCR service — multi-engine parallel OCR with consensus voting.

Engines: Tesseract, EasyOCR, PaddleOCR, TrOCR
Each engine runs in parallel with a 5-second timeout.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from backend.ocr.consensus_engine import build_consensus
from backend.ocr.multi_ocr_runner import run_all_engines
from backend.ocr.visualizations import build_ocr_visualizations

logger = logging.getLogger("ai_forge.ocr")

_MEMORY_CACHE: Dict[str, Dict[str, Any]] = {}
_CACHE_LOCK = threading.Lock()


def _cache_key(image_path: str) -> str:
    p = Path(image_path)
    stat = p.stat()
    return f"{p.resolve()}:{stat.st_mtime_ns}:{stat.st_size}"


def _ocr_cache_path(analysis_dir: Optional[Path]) -> Optional[Path]:
    if not analysis_dir:
        return None
    return Path(analysis_dir) / "ocr.json"


def _layout_cache_path(analysis_dir: Optional[Path]) -> Optional[Path]:
    if not analysis_dir:
        return None
    return Path(analysis_dir) / "layout.json"


def _load_disk_cache(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _save_disk_cache(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _legacy_single_engine(image_path: str) -> Dict[str, Any]:
    """Fallback: PaddleOCR → RapidOCR → EasyOCR (preserves prior behavior)."""
    from backend.services.ocr_service_legacy import run_legacy_ocr
    return run_legacy_ocr(image_path)


def run_multi_ocr(
    image_path: str,
    analysis_dir: Optional[str | Path] = None,
    progress: Optional[Callable[[str, str, float], None]] = None,
) -> Dict[str, Any]:
    """Run all OCR engines in parallel and build consensus result."""
    image_path = str(Path(image_path).resolve())

    if progress:
        progress("ocr", "running")

    multi = run_all_engines(image_path, progress=progress)
    result = build_consensus(multi)

    if not result.get("success"):
        logger.warning("Multi-OCR consensus failed, falling back to legacy single engine")
        legacy = _legacy_single_engine(image_path)
        if legacy.get("full_text") or legacy.get("detections"):
            result = {
                **legacy,
                "engine": legacy.get("engine", "legacy"),
                "primary_engine": legacy.get("engine"),
                "ocr_confidence": legacy.get("word_confidence", 0.5),
                "character_confidence": legacy.get("character_confidence", 0.5),
                "word_confidence": legacy.get("word_confidence", 0.5),
                "layout_confidence": legacy.get("layout_confidence", 0.5),
                "detected_language": legacy.get("detected_language", "en"),
                "consensus": {"reasoning": "Legacy single-engine fallback used."},
                "engine_results": {legacy.get("engine", "legacy"): legacy},
            }

    analysis_path = Path(analysis_dir) if analysis_dir else None
    visuals = build_ocr_visualizations(image_path, result, str(analysis_path) if analysis_path else None)
    result["visualizations"] = visuals
    result["mismatch_heatmap"] = visuals.get("mismatch_heatmap")
    result["layout_overlay"] = visuals.get("layout_overlay")
    result["source"] = image_path
    result["cached"] = False

    if progress:
        progress("ocr", "completed")
        progress("ocr_consensus", "completed")

    return result


def extract_text(
    image_path: str,
    analysis_dir: Optional[str | Path] = None,
    use_cache: bool = True,
    progress: Optional[Callable[[str, str, float], None]] = None,
) -> Dict[str, Any]:
    """
    Extract text with multi-engine OCR consensus.

    Layered cache: memory → disk → parallel OCR engines.
    Preserves backward-compatible keys: text, full_text, detections, word_count, engine.
    """
    image_path = str(Path(image_path).resolve())
    cache_key = _cache_key(image_path)
    analysis_path = Path(analysis_dir) if analysis_dir else None

    with _CACHE_LOCK:
        if use_cache and cache_key in _MEMORY_CACHE:
            return _MEMORY_CACHE[cache_key]

    disk_path = _ocr_cache_path(analysis_path)
    if use_cache and disk_path:
        cached = _load_disk_cache(disk_path)
        if cached and cached.get("source") == image_path:
            with _CACHE_LOCK:
                _MEMORY_CACHE[cache_key] = cached
            return cached

    result = run_multi_ocr(image_path, analysis_dir=analysis_path, progress=progress)

    # Backward-compatible aliases
    if "text" not in result:
        result["text"] = result.get("full_text", "")

    if use_cache:
        with _CACHE_LOCK:
            _MEMORY_CACHE[cache_key] = result
        if disk_path:
            _save_disk_cache(disk_path, result)

    return result


def get_layout_cache(
    image_path: str,
    analysis_dir: Optional[str | Path] = None,
) -> Optional[Dict[str, Any]]:
    path = _layout_cache_path(Path(analysis_dir) if analysis_dir else None)
    if not path:
        return None
    cached = _load_disk_cache(path)
    if cached and cached.get("source") == str(Path(image_path).resolve()):
        return cached
    return None


def save_layout_cache(
    image_path: str,
    layout: Dict[str, Any],
    analysis_dir: Optional[str | Path] = None,
) -> None:
    path = _layout_cache_path(Path(analysis_dir) if analysis_dir else None)
    if not path:
        return
    layout = dict(layout)
    layout["source"] = str(Path(image_path).resolve())
    _save_disk_cache(path, layout)
    with _CACHE_LOCK:
        _MEMORY_CACHE[_cache_key(image_path)] = layout
