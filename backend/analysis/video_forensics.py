"""Video forensics — delegates to parallel video service."""

from backend.services.video_service import analyze_video_parallel as analyze_video

__all__ = ["analyze_video", "calculate_frame_signals"]

# Backward compatibility
from backend.services.video_service import _calculate_frame_signals as calculate_frame_signals
