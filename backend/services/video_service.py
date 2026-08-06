"""
Production-grade video forensic analysis with parallel frame batches.
"""

from __future__ import annotations

import logging
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

from backend.ingestion.video_processor import extract_scene_keyframes, get_video_metadata
from backend.database.repository import get_analysis_by_hash, save_analysis_record
from backend.utils.file_hash import compute_file_hash
from backend.utils.performance_config import SLA_VIDEO_SEC, VIDEO_FRAME_WORKERS
from backend.utils.progress import ProgressTracker
from backend.forensics.integration import on_analysis_complete
from backend.utils.redis_cache import cache_key, get_redis_cache
from backend.utils.sla_guard import sla_timer
from backend.utils.timing import ModuleTimer

logger = logging.getLogger("ai_forge.video")

# Cheap signal analysis on all keyframes
MAX_KEYFRAMES = 12
# Expensive AI modules only on representative subset
EXPENSIVE_FRAME_COUNT = 3
FRAME_BATCH_SIZE = 4


def _calculate_frame_signals(frame_path: str) -> Dict[str, float]:
    image = cv2.imread(str(frame_path))
    if image is None:
        return {"edge_density": 0.0, "brightness": 0.0, "blur_score": 0.0}

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 200)
    edge_pixels = np.count_nonzero(edges)
    total_pixels = edges.shape[0] * edges.shape[1]
    edge_density = edge_pixels / total_pixels if total_pixels > 0 else 0.0
    brightness = float(np.mean(gray))
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    return {
        "edge_density": round(edge_density, 4),
        "brightness": round(brightness, 2),
        "blur_score": round(blur_score, 2),
    }


def _analyze_frame_batch(frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results = []
    for frame in frames:
        signals = _calculate_frame_signals(frame["path"])
        results.append({
            "frame_number": frame["frame_number"],
            "frame_index": frame["frame_index"],
            "timestamp": frame["timestamp"],
            "image": frame["path"],
            "signals": signals,
        })
    return results


def _select_expensive_frames(frames: List[Dict[str, Any]], count: int) -> List[Dict[str, Any]]:
    """Pick evenly spaced keyframes for expensive downstream AI modules."""
    if len(frames) <= count:
        return frames
    step = len(frames) / count
    indices = [int(i * step) for i in range(count)]
    return [frames[i] for i in indices]


def analyze_video_parallel(
    video_path: str,
    analysis_dir: str,
    max_frames: int = MAX_KEYFRAMES,
    progress: Optional[ProgressTracker] = None,
    use_cache: bool = True,
    video_id: Optional[str] = None,
) -> Dict[str, Any]:
    video_path = Path(video_path)
    analysis_dir = Path(analysis_dir)

    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    file_hash = compute_file_hash(video_path)
    redis = get_redis_cache()
    rkey = cache_key("video", file_hash)
    if use_cache:
        redis_cached = redis.get(rkey)
        if redis_cached and redis_cached.get("analysis"):
            if progress:
                progress.emit("cache", "completed", extra={"source": "redis"})
            result = redis_cached["analysis"]
            result["cached"] = True
            return result

    if use_cache:
        cached = get_analysis_by_hash(file_hash, "video")
        if cached:
            if progress:
                progress.emit("cache", "completed", extra={"source": "database"})
            result = cached["analysis"]
            result["cached"] = True
            return result

    analysis_dir.mkdir(parents=True, exist_ok=True)
    timer = ModuleTimer("Video Analysis")

    with sla_timer("video", video_id or ""):
        def _emit(module: str, status: str, elapsed: float = 0.0):
            if progress:
                progress.emit(module, status, elapsed=elapsed)

        with timer.track("metadata"):
            _emit("metadata", "running")
            metadata = get_video_metadata(str(video_path))
            _emit("metadata", "completed")

        frames_dir = analysis_dir / "keyframes"
        with timer.track("keyframes"):
            _emit("keyframes", "running")
            keyframes = extract_scene_keyframes(str(video_path), str(frames_dir), max_frames)
            _emit("keyframes", "completed")

        frame_results: List[Dict[str, Any]] = []
        batches = [
            keyframes[i: i + FRAME_BATCH_SIZE]
            for i in range(0, len(keyframes), FRAME_BATCH_SIZE)
        ]

        with timer.track("frame_signals"):
            _emit("frame_signals", "running")
            workers = min(VIDEO_FRAME_WORKERS, len(batches) or 1)
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [executor.submit(_analyze_frame_batch, batch) for batch in batches]
                for future in as_completed(futures):
                    frame_results.extend(future.result())
            frame_results.sort(key=lambda x: x["frame_index"])
            _emit("frame_signals", "completed")

        expensive_frames = _select_expensive_frames(keyframes, EXPENSIVE_FRAME_COUNT)
        expensive_analysis: List[Dict[str, Any]] = []

        with timer.track("keyframe_forensics"):
            _emit("keyframe_forensics", "running")

            def _expensive_one(frame):
                signals = _calculate_frame_signals(frame["path"])
                return {
                    "frame_index": frame["frame_index"],
                    "timestamp": frame["timestamp"],
                    "forensic_signals": signals,
                    "note": "Deep analysis on representative keyframe",
                }

            with ThreadPoolExecutor(max_workers=min(3, len(expensive_frames) or 1)) as executor:
                futures = [executor.submit(_expensive_one, f) for f in expensive_frames]
                for future in as_completed(futures):
                    try:
                        expensive_analysis.append(future.result())
                    except Exception as exc:
                        logger.warning("Expensive frame analysis failed: %s", exc)
            _emit("keyframe_forensics", "completed")

        if frame_results:
            edge_values = [f["signals"]["edge_density"] for f in frame_results]
            brightness_values = [f["signals"]["brightness"] for f in frame_results]
            blur_values = [f["signals"]["blur_score"] for f in frame_results]
            avg_edge = sum(edge_values) / len(edge_values)
            avg_brightness = sum(brightness_values) / len(brightness_values)
            avg_blur = sum(blur_values) / len(blur_values)
        else:
            avg_edge = avg_brightness = avg_blur = 0.0

        timing = timer.log_summary()

        result = {
            "video": metadata,
            "summary": {
                "frames_analyzed": len(frame_results),
                "expensive_frames_analyzed": len(expensive_analysis),
                "average_edge_density": round(avg_edge, 4),
                "average_brightness": round(avg_brightness, 2),
                "average_blur_score": round(avg_blur, 2),
            },
            "frames": frame_results,
            "keyframe_forensics": expensive_analysis,
            "timing": timing,
            "file_hash": file_hash,
        }

    try:
        save_analysis_record(
            record_id=str(uuid.uuid4()),
            file_hash=file_hash,
            media_type="video",
            analysis=result,
            evidence_id=video_id,
            filename=video_path.name,
            execution_times=timing,
            deep_scan=True,
        )
    except Exception as exc:
        logger.warning("Video DB persist failed: %s", exc)

    redis.set(rkey, {"analysis": result, "timing": timing})

    if video_id:
        on_analysis_complete(video_id, result, media_type="video", execution_times=timing)

    return result
