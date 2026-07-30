import os
import uuid
from fastapi import (
    APIRouter,
    HTTPException
)

from fastapi.responses import FileResponse

from pathlib import Path
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from backend.ingestion.file_router import identify_file_type

from backend.analysis.image_forensics import analyze_image


router = APIRouter(
    prefix="/api",
    tags=["Evidence"]
)


# Directory where uploaded evidence is stored
UPLOAD_DIR = Path("data/temp/uploads")

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# Maximum file size: 100 MB
MAX_FILE_SIZE = 100 * 1024 * 1024


@router.post("/evidence/upload")
async def upload_evidence(
    file: UploadFile = File(...)
):

    # Check filename
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No filename provided"
        )


    # Identify file type
    file_type = identify_file_type(
        file.filename
    )


    # Reject unsupported files
    if file_type == "unsupported":
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type"
        )


    # Generate unique evidence ID
    evidence_id = str(
        uuid.uuid4()
    )


    # Preserve original extension
    extension = Path(
        file.filename
    ).suffix.lower()


    # Create unique filename
    saved_filename = (
        f"{evidence_id}{extension}"
    )


    file_path = (
        UPLOAD_DIR /
        saved_filename
    )


    # Save uploaded file
    total_size = 0

    try:

        with open(
            file_path,
            "wb"
        ) as buffer:

            while True:

                chunk = await file.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                total_size += len(chunk)


                # Prevent oversized uploads
                if total_size > MAX_FILE_SIZE:

                    buffer.close()

                    file_path.unlink(
                        missing_ok=True
                    )

                    raise HTTPException(
                        status_code=413,
                        detail="File exceeds 100 MB limit"
                    )


                buffer.write(
                    chunk
                )


    except HTTPException:
        raise

    except Exception as e:

        file_path.unlink(
            missing_ok=True
        )

        raise HTTPException(
            status_code=500,
            detail=f"Failed to save file: {str(e)}"
        )


    return {
        "success": True,
        "evidence_id": evidence_id,
        "original_filename": file.filename,
        "file_type": file_type,
        "file_size": total_size,
        "stored_filename": saved_filename,
        "message": "Evidence uploaded successfully"
    }
@router.post("/evidence/analyze-image/{evidence_id}")
async def analyze_uploaded_image(
    evidence_id: str
):

    # Search for uploaded image
    image_files = list(
        UPLOAD_DIR.glob(
            f"{evidence_id}.*"
        )
    )

    if not image_files:
        raise HTTPException(
            status_code=404,
            detail="Evidence not found"
        )

    image_path = image_files[0]

    # Run forensic analysis
    try:

        result = analyze_image(
            str(image_path)
        )

        # Add API URLs for generated artifacts
        if "artifacts" in result:

            result["artifacts"] = {
                "ela":
                    f"/api/evidence/artifacts/{evidence_id}/ela",

                "edges":
                    f"/api/evidence/artifacts/{evidence_id}/edges",

                "wavelet":
                    f"/api/evidence/artifacts/{evidence_id}/wavelet"
            }

        return {

            "success": True,

            "evidence_id":
                evidence_id,

            "analysis":
                result

        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
@router.get(
    "/evidence/artifacts/{evidence_id}/{artifact_type}"
)
async def get_evidence_artifact(
    evidence_id: str,
    artifact_type: str
):

    # Find uploaded evidence
    image_files = list(
        UPLOAD_DIR.glob(
            f"{evidence_id}.*"
        )
    )

    if not image_files:

        raise HTTPException(
            status_code=404,
            detail="Evidence not found"
        )


    image_path = image_files[0]


    # Artifact directory
    analysis_dir = (
        image_path.parent /
        "analysis"
    )


    # Supported artifact types
    artifact_map = {

        "ela":
            analysis_dir /
            f"{image_path.stem}_ela.jpg",

        "edges":
            analysis_dir /
            f"{image_path.stem}_edges.jpg",

        "wavelet":
            analysis_dir /
            f"{image_path.stem}_wavelet.jpg"

    }


    if artifact_type not in artifact_map:

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid artifact type. "
                "Use ela, edges, or wavelet."
            )
        )


    artifact_path = artifact_map[
        artifact_type
    ]


    if not artifact_path.exists():

        raise HTTPException(
            status_code=404,
            detail="Artifact not found"
        )


    return FileResponse(
        path=artifact_path,
        media_type="image/jpeg"
    )