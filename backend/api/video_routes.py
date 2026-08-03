from pathlib import Path
import shutil
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException

from backend.analysis.video_forensics import analyze_video

router = APIRouter(
    prefix="/api/video",
    tags=["Video Analysis"]
)

UPLOAD_DIR = Path("data/temp/videos")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/analyze")
async def analyze_video_endpoint(file: UploadFile = File(...)):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No video uploaded"
        )

    extension = Path(file.filename).suffix

    video_id = str(uuid.uuid4())

    video_path = UPLOAD_DIR / f"{video_id}{extension}"

    with open(video_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    analysis_dir = UPLOAD_DIR / "analysis" / video_id

    result = analyze_video(
        str(video_path),
        str(analysis_dir)
    )

    return {
        "success": True,
        "analysis": result
    }