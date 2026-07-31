import os
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException
)
from backend.core.evidence_manager import (
    generate_evidence_id
)
from backend.analysis.unified_image_analysis import (
    analyze_image_unified
)
from fastapi.responses import FileResponse

from backend.ingestion.file_router import identify_file_type
from backend.analysis.image_forensics import analyze_image
from backend.analysis.document_forensics import (
    analyze_document
)
from backend.agents.signature_agent import (
    verify_signature
)
from backend.analysis.copy_move import detect_copy_move

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
    evidence_id = generate_evidence_id()


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
            f"{image_path.stem}_wavelet.jpg",

        "copy_move":
            analysis_dir /
            f"{image_path.stem}_copy_move.jpg"

    }


    # Check artifact type
    if artifact_type not in artifact_map:

        raise HTTPException(

            status_code=400,

            detail=(

                "Invalid artifact type. "

                "Use ela, edges, wavelet, or copy_move."

            )

        )


    # Get requested artifact
    artifact_path = artifact_map[
        artifact_type
    ]


    # Check artifact exists
    if not artifact_path.exists():

        raise HTTPException(

            status_code=404,

            detail="Artifact not found"

        )


    # Return artifact image
    return FileResponse(

        path=artifact_path,

        media_type="image/jpeg"

    )
    
#analyze document    
@router.post(
    "/evidence/analyze-document/{evidence_id}"
)
async def analyze_uploaded_document(
    evidence_id: str
):

    document_files = list(

        UPLOAD_DIR.glob(
            f"{evidence_id}.pdf"
        )

    )


    if not document_files:

        raise HTTPException(

            status_code=404,

            detail="PDF document not found"

        )


    document_path = (
        document_files[0]
    )


    try:

        result = analyze_document(

            str(document_path)

        )


        return {

            "success":
                True,

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
        
#verify signature
@router.post(
    "/evidence/verify-signature"
)
async def verify_uploaded_signature(

    reference: UploadFile = File(...),

    query: UploadFile = File(...)

):

    signature_dir = (
        Path("data/temp/signatures")
    )

    signature_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    reference_path = (
        signature_dir /
        f"reference_{uuid.uuid4()}.png"
    )


    query_path = (
        signature_dir /
        f"query_{uuid.uuid4()}.png"
    )


    try:

        # Save reference signature

        with open(
            reference_path,
            "wb"
        ) as buffer:

            buffer.write(
                await reference.read()
            )


        # Save query signature

        with open(
            query_path,
            "wb"
        ) as buffer:

            buffer.write(
                await query.read()
            )


        # Verify signature

        result = verify_signature(

            str(reference_path),

            str(query_path)

        )


        return {

            "success":
                True,

            "analysis":
                result

        }


    except Exception as e:

        raise HTTPException(

            status_code=500,

            detail=str(e)

        )

# ==========================================
# Signature Verification
# ==========================================

@router.post("/signature/verify")
async def verify_signature_api(
    reference: UploadFile = File(...),
    query: UploadFile = File(...)
):

    # --------------------------------------
    # Allowed image formats
    # --------------------------------------

    allowed_extensions = {
        ".png",
        ".jpg",
        ".jpeg"
    }

    reference_ext = Path(
        reference.filename
    ).suffix.lower()

    query_ext = Path(
        query.filename
    ).suffix.lower()


    # --------------------------------------
    # Validate reference signature
    # --------------------------------------

    if reference_ext not in allowed_extensions:

        raise HTTPException(
            status_code=400,
            detail=(
                "Reference signature must be "
                "PNG, JPG, or JPEG"
            )
        )


    # --------------------------------------
    # Validate query signature
    # --------------------------------------

    if query_ext not in allowed_extensions:

        raise HTTPException(
            status_code=400,
            detail=(
                "Query signature must be "
                "PNG, JPG, or JPEG"
            )
        )


    # --------------------------------------
    # Create temporary directory
    # --------------------------------------

    signature_dir = Path(
        "data/temp/signatures"
    )

    signature_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    # --------------------------------------
    # Generate unique filenames
    # --------------------------------------

    reference_id = str(
        uuid.uuid4()
    )

    query_id = str(
        uuid.uuid4()
    )


    reference_path = (
        signature_dir
        / f"{reference_id}{reference_ext}"
    )

    query_path = (
        signature_dir
        / f"{query_id}{query_ext}"
    )


    try:

        # ==================================
        # Save reference signature
        # ==================================

        with open(
            reference_path,
            "wb"
        ) as buffer:

            while True:

                chunk = await reference.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                buffer.write(
                    chunk
                )


        # ==================================
        # Save query signature
        # ==================================

        with open(
            query_path,
            "wb"
        ) as buffer:

            while True:

                chunk = await query.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                buffer.write(
                    chunk
                )


        # ==================================
        # Run Siamese Network
        # ==================================

        result = verify_signature(

            str(reference_path),

            str(query_path)

        )


        # ==================================
        # Return result
        # ==================================

        return {

            "success": True,

            "analysis": {

                "verdict":
                    result["verdict"],

                "similarity":
                    result["similarity"],

                "confidence":
                    result["confidence"]

            }

        }


    except Exception as e:

        raise HTTPException(

            status_code=500,

            detail=(
                "Signature verification "
                f"failed: {str(e)}"
            )

        )


    finally:

        # ==================================
        # Delete temporary files
        # ==================================

        reference_path.unlink(
            missing_ok=True
        )

        query_path.unlink(
            missing_ok=True
        )
        
@router.post(
    "/evidence/analyze-copy-move/{evidence_id}"
)
async def analyze_copy_move(
    evidence_id: str
):

    # --------------------------------
    # Find uploaded evidence
    # --------------------------------

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


    # --------------------------------
    # Analysis directory
    # --------------------------------

    analysis_dir = (

        image_path.parent /

        "analysis"

    )


    analysis_dir.mkdir(

        parents=True,

        exist_ok=True

    )


    # --------------------------------
    # Run Copy-Move Detection
    # --------------------------------

    try:

        result = detect_copy_move(

            str(image_path),

            output_dir=analysis_dir

        )


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

#unified_image_analysis       
@router.post(
    "/evidence/analyze/{evidence_id}"
)
async def analyze_evidence(
    evidence_id: str
):

    # -----------------------------------------
    # Find uploaded evidence
    # -----------------------------------------

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


    image_path = (

        image_files[0]

    )


    # -----------------------------------------
    # Analysis directory
    # -----------------------------------------

    analysis_dir = (

        UPLOAD_DIR /

        "analysis"

    )


    # -----------------------------------------
    # Run unified analysis
    # -----------------------------------------

    try:

        result = (

            analyze_image_unified(

                image_path,

                analysis_dir

            )

        )


        return {

            "success":

                True,

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