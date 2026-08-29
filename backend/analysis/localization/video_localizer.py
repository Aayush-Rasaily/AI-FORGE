"""Video manipulation localization — frame timeline with regions."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger("ai_forge.localization.video")


def build_video_localization(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build manipulation timeline from video analysis frames.
    Identifies suspicious frames and altered face/object regions.
    """
    video = analysis.get("video") or {}
    frames = analysis.get("frames") or video.get("frames") or []
    keyframe_forensics = analysis.get("keyframe_forensics") or video.get("keyframe_forensics") or []

    timeline: List[Dict[str, Any]] = []
    manipulated_frames: List[Dict[str, Any]] = []

    # Forward the advanced frame-level localization timeline created by video_service
    video_timeline = analysis.get("video", {}).get("timeline") or analysis.get("video_timeline") or []
    
    for event in video_timeline:
        score = event.get("confidence", 0)
        entry = {
            "frame_number": event.get("frame_number"),
            "timestamp": event.get("time_seconds", 0),
            "score": score,
            "reason": event.get("reason", "Anomalous edge/blur forensic signals on keyframe"),
            "regions": [{
                "type": "video_frame",
                "label": event.get("finding", "Suspicious region"),
                "confidence": round(score * 100, 2),
                "bbox": event.get("bbox")
            }],
        }
        timeline.append(entry)
        if score >= 0.5:
            manipulated_frames.append(entry)

    timeline.sort(key=lambda x: float(x.get("timestamp") or 0))
    manipulated_frames.sort(key=lambda x: float(x.get("timestamp") or 0))

    return {
        "suspicious_intervals": timeline,
        "manipulated_frames": manipulated_frames,
        "frame_count": len(frames),
        "manipulated_count": len(manipulated_frames),
        "available": bool(timeline),
    }
