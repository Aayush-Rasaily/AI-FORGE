from fastapi import (

    APIRouter,

    UploadFile,

    File,

    HTTPException

)

from pathlib import Path

import shutil

import uuid


from backend.analysis.video_forensics import (

    analyze_video

)


router = APIRouter(

    prefix="/api/video",

    tags=["Video Analytics"]

)


# ------------------------------------------
# Storage directories
# ------------------------------------------

BASE_DIR = Path(

    "data/temp/video_analysis"

)


UPLOAD_DIR = (

    BASE_DIR /

    "uploads"

)


ANALYSIS_DIR = (

    BASE_DIR /

    "analysis"

)


UPLOAD_DIR.mkdir(

    parents=True,

    exist_ok=True

)


ANALYSIS_DIR.mkdir(

    parents=True,

    exist_ok=True

)


# ------------------------------------------
# Supported video extensions
# ------------------------------------------

ALLOWED_EXTENSIONS = {

    ".mp4",

    ".avi",

    ".mov",

    ".mkv",

    ".webm"

}


@router.post(

    "/analyze"

)

async def analyze_video_endpoint(

    file: UploadFile = File(...)

):

    try:

        # --------------------------------------
        # Validate filename
        # --------------------------------------

        if not file.filename:

            raise HTTPException(

                status_code=400,

                detail=(

                    "Video file is required."

                )

            )


        extension = (

            Path(

                file.filename

            ).suffix.lower()

        )


        # --------------------------------------
        # Validate extension
        # --------------------------------------

        if extension not in ALLOWED_EXTENSIONS:

            raise HTTPException(

                status_code=400,

                detail=(

                    "Unsupported video format. "

                    "Supported formats: "

                    "MP4, AVI, MOV, MKV, WEBM."

                )

            )


        # --------------------------------------
        # Generate unique ID
        # --------------------------------------

        video_id = (

            f"VID-"

            f"{uuid.uuid4().hex[:8].upper()}"

        )


        # --------------------------------------
        # Create directories
        # --------------------------------------

        video_upload_dir = (

            UPLOAD_DIR /

            video_id

        )


        video_analysis_dir = (

            ANALYSIS_DIR /

            video_id

        )


        video_upload_dir.mkdir(

            parents=True,

            exist_ok=True

        )


        video_analysis_dir.mkdir(

            parents=True,

            exist_ok=True

        )


        # --------------------------------------
        # Save uploaded video
        # --------------------------------------

        video_path = (

            video_upload_dir /

            f"original{extension}"

        )


        with open(

            video_path,

            "wb"

        ) as buffer:

            shutil.copyfileobj(

                file.file,

                buffer

            )


        print(

            f"[VIDEO API] Saved video: "

            f"{video_path}"

        )


        # --------------------------------------
        # Analyze video
        # --------------------------------------

        result = analyze_video(

            str(video_path),

            str(video_analysis_dir)

        )


        # --------------------------------------
        # Return result
        # --------------------------------------

        return {

            "success":

                True,

            "video_id":

                video_id,

            "filename":

                file.filename,

            "analysis":

                result

        }


    except HTTPException:

        raise


    except Exception as e:

        print(

            "[VIDEO API ERROR]",

            str(e)

        )


        raise HTTPException(

            status_code=500,

            detail=str(e)

        )