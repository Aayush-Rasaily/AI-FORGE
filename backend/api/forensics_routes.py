"""
Forensics API Routes — attention heatmaps and deepfake detection.
"""

import logging
import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend.analysis.attention_heatmap import generate_attention_heatmap
from backend.analysis.explainability.engine import run_explainability
from backend.analysis.deepfake_detector import (
    analyze_deepfake_image,
    analyze_deepfake_video,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/forensics", tags=["forensics"])

UPLOAD_DIR = Path("data/temp/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

VIDEO_DIR = Path("data/temp/videos")
VIDEO_DIR.mkdir(parents=True, exist_ok=True)


def _find_evidence_file(evidence_id: str) -> Path:
    files = [
        f for f in UPLOAD_DIR.glob(f"{evidence_id}.*")
        if f.is_file() and "analysis" not in str(f)
    ]
    if not files:
        raise HTTPException(status_code=404, detail=f"Evidence not found: {evidence_id}")
    return files[0]


def _get_analysis_dir(evidence_id: str) -> Path:
    d = UPLOAD_DIR / "analysis" / evidence_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _artifact_urls(evidence_id: str) -> dict:
    base = f"/api/forensics/heatmap/{evidence_id}/artifact"
    return {
        "heatmap": f"{base}/heatmap",
        "overlay": f"{base}/overlay",
        "legend": f"{base}/legend",
        "original": f"{base}/original",
    }


@router.post("/explain/{evidence_id}")
async def generate_explainability(evidence_id: str):
    """Generate GradCAM, SHAP, LIME, attention maps, and forensic explainability report."""
    image_path = _find_evidence_file(evidence_id)
    analysis_dir = _get_analysis_dir(evidence_id)

    try:
        result = run_explainability(
            str(image_path),
            str(analysis_dir),
            context={"verdict": "PENDING", "risk_score": 50, "confidence": 75, "signals": {}, "evidence": []},
        )
        result["evidence_id"] = evidence_id
        return {"success": True, **result}
    except Exception as exc:
        logger.exception("Explainability generation failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/explain/{evidence_id}/artifact/{artifact_type}")
async def get_explainability_artifact(evidence_id: str, artifact_type: str):
    """Serve explainability artifacts."""
    analysis_dir = _get_analysis_dir(evidence_id) / "explainability"
    artifact_map = {
        "gradcam_overlay": analysis_dir / "gradcam_overlay.jpg",
        "gradcam_heatmap": analysis_dir / "gradcam_heatmap.jpg",
        "attention_overlay": analysis_dir / "attention_overlay.jpg",
        "shap_overlay": analysis_dir / "shap_overlay.jpg",
        "lime_overlay": analysis_dir / "lime_overlay.jpg",
        "fused_overlay": analysis_dir / "fused_suspicious_overlay.jpg",
        "boxed_regions": analysis_dir / "fused_suspicious_regions.jpg",
    }
    if artifact_type not in artifact_map:
        raise HTTPException(status_code=400, detail="Invalid artifact type.")
    path = artifact_map[artifact_type]
    if not path.exists():
        image_path = _find_evidence_file(evidence_id)
        run_explainability(str(image_path), str(_get_analysis_dir(evidence_id)))
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact not found.")
    return FileResponse(str(path), media_type="image/jpeg")


@router.post("/heatmap/{evidence_id}")
async def generate_heatmap(evidence_id: str):
    """Generate unified attention heatmap for uploaded evidence."""
    image_path = _find_evidence_file(evidence_id)
    analysis_dir = _get_analysis_dir(evidence_id)

    try:
        result = generate_attention_heatmap(
            str(image_path),
            str(analysis_dir),
        )
        result["evidence_id"] = evidence_id
        result["artifacts"] = _artifact_urls(evidence_id)
        try:
            from backend.pipeline.report_manager import persist_analysis_payload, generate_reports

            persist_analysis_payload(evidence_id, result, kind="dashboard")
            generate_reports(evidence_id, background=True)
        except Exception as report_exc:
            logger.warning("heatmap_report_queue_failed | error=%s", report_exc)
        result["reports_pending"] = True
        result["report_status"] = "queued"
        return {"success": True, **result}
    except Exception as exc:
        logger.exception("Heatmap generation failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/heatmap/{evidence_id}/artifact/{artifact_type}")
async def get_heatmap_artifact(evidence_id: str, artifact_type: str):
    """Serve heatmap artifacts: heatmap, overlay, legend, original."""
    image_path = _find_evidence_file(evidence_id)
    analysis_dir = _get_analysis_dir(evidence_id)
    stem = image_path.stem

    artifact_map = {
        "heatmap": analysis_dir / f"{stem}_attention_heatmap.jpg",
        "overlay": analysis_dir / f"{stem}_attention_overlay.jpg",
        "legend": analysis_dir / f"{stem}_attention_legend.jpg",
        "original": image_path,
    }

    if artifact_type not in artifact_map:
        raise HTTPException(
            status_code=400,
            detail="Invalid artifact type. Use heatmap, overlay, legend, or original.",
        )

    path = artifact_map[artifact_type]

    if artifact_type != "original" and not path.exists():
        generate_attention_heatmap(str(image_path), str(analysis_dir))
        if not path.exists():
            raise HTTPException(status_code=404, detail="Artifact not found.")

    return FileResponse(str(path), media_type="image/jpeg")


@router.post("/deepfake/image/{evidence_id}")
async def deepfake_analyze_image(evidence_id: str):
    """Run deepfake detection on uploaded image evidence."""
    image_path = _find_evidence_file(evidence_id)
    analysis_dir = _get_analysis_dir(evidence_id) / "deepfake"

    try:
        result = analyze_deepfake_image(str(image_path), str(analysis_dir))
        if result.get("heatmap"):
            rel = Path(result["heatmap"]).as_posix()
            result["heatmap_url"] = f"/data/{rel.split('data/')[-1]}" if "data/" in rel else result["heatmap"]
        result["evidence_id"] = evidence_id
        try:
            from backend.pipeline.report_manager import persist_analysis_payload, generate_reports

            persist_analysis_payload(evidence_id, result, kind="deepfake")
            generate_reports(evidence_id, background=True)
        except Exception as report_exc:
            logger.warning("deepfake_report_queue_failed | error=%s", report_exc)
        result["reports_pending"] = True
        result["report_status"] = "queued"
        return {"success": True, **result}
    except Exception as exc:
        logger.exception("Deepfake image analysis failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/deepfake/video")
async def deepfake_analyze_video(file: UploadFile = File(...)):
    """Run deepfake detection on uploaded video."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No video uploaded.")

    video_id = str(uuid.uuid4())
    ext = Path(file.filename).suffix or ".mp4"
    video_path = VIDEO_DIR / f"{video_id}{ext}"

    with open(video_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    analysis_dir = VIDEO_DIR / "deepfake" / video_id

    try:
        result = analyze_deepfake_video(str(video_path), str(analysis_dir))
        result["video_id"] = video_id
        result["evidence_id"] = video_id
        try:
            from backend.pipeline.report_manager import persist_analysis_payload, generate_reports

            persist_analysis_payload(video_id, result, kind="deepfake")
            generate_reports(video_id, background=True)
        except Exception as report_exc:
            logger.warning("deepfake_video_report_queue_failed | error=%s", report_exc)
        result["reports_pending"] = True
        result["report_status"] = "queued"
        return {"success": True, **result}
    except Exception as exc:
        logger.exception("Deepfake video analysis failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/deepfake/image")
async def deepfake_analyze_image_upload(file: UploadFile = File(...)):
    """Run deepfake detection on uploaded image file."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No image uploaded.")

    image_id = str(uuid.uuid4())
    ext = Path(file.filename).suffix or ".jpg"
    image_path = UPLOAD_DIR / f"{image_id}{ext}"

    with open(image_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    analysis_dir = UPLOAD_DIR / "analysis" / image_id / "deepfake"

    try:
        result = analyze_deepfake_image(str(image_path), str(analysis_dir))
        if result.get("heatmap"):
            rel = Path(result["heatmap"]).as_posix()
            result["heatmap_url"] = f"/data/{rel.split('data/')[-1]}" if "data/" in rel else result["heatmap"]
        result["image_id"] = image_id
        result["evidence_id"] = image_id
        try:
            from backend.pipeline.report_manager import persist_analysis_payload, generate_reports
            from backend.forensics.integration import on_evidence_uploaded

            on_evidence_uploaded(
                image_id,
                image_path,
                original_filename=file.filename,
                media_type="image",
            )
            persist_analysis_payload(image_id, result, kind="deepfake")
            generate_reports(image_id, background=True)
        except Exception as report_exc:
            logger.warning("deepfake_upload_report_queue_failed | error=%s", report_exc)
        result["reports_pending"] = True
        result["report_status"] = "queued"
        return {"success": True, **result}
    except Exception as exc:
        logger.exception("Deepfake image upload analysis failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/health")
async def forensics_health():
    return {
        "status": "ok",
        "services": ["attention_heatmap", "deepfake_detection", "explainability"],
    }
