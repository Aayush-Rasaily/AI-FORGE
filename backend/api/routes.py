import tempfile
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException
)

from fastapi.responses import FileResponse

from backend.core.evidence_manager import (
    generate_evidence_id
)

from backend.ingestion.file_router import (
    identify_file_type
)

from backend.analysis.unified_image_analysis import (
    analyze_image_unified
)

from backend.analysis.document_forensics import (
    analyze_document
)

from backend.models.signature.inference import (
    verify_signature
)

from backend.analysis.copy_move import (
    detect_copy_move
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/api",
    tags=["Evidence"]
)


# ============================================================
# DIRECTORIES
# ============================================================

UPLOAD_DIR = Path(
    "data/temp/uploads"
)

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# Maximum upload size: 100 MB

MAX_FILE_SIZE = (
    100 *
    1024 *
    1024
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def find_evidence_file(
    evidence_id: str
):
    """
    Find the uploaded evidence file
    using its generated evidence ID.
    """

    files = list(
        UPLOAD_DIR.glob(
            f"{evidence_id}.*"
        )
    )

    if not files:

        raise HTTPException(
            status_code=404,
            detail="Evidence not found"
        )

    return files[0]


def get_analysis_dir(
    evidence_id: str
):
    """
    Return the dedicated analysis directory
    for a specific evidence item.
    """

    analysis_dir = (

        UPLOAD_DIR /

        "analysis" /

        evidence_id

    )

    analysis_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    return analysis_dir


# ============================================================
# 1. UPLOAD EVIDENCE
# ============================================================

@router.post(
    "/evidence/upload"
)
async def upload_evidence(
    file: UploadFile = File(...)
):

    # -----------------------------------------
    # Validate filename
    # -----------------------------------------

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="No filename provided"
        )


    # -----------------------------------------
    # Identify file type
    # -----------------------------------------

    file_type = identify_file_type(
        file.filename
    )


    # -----------------------------------------
    # Reject unsupported files
    # -----------------------------------------

    if file_type == "unsupported":

        raise HTTPException(
            status_code=400,
            detail="Unsupported file type"
        )


    # -----------------------------------------
    # Generate evidence ID
    # -----------------------------------------

    evidence_id = (
        generate_evidence_id()
    )


    # -----------------------------------------
    # Preserve original extension
    # -----------------------------------------

    extension = Path(
        file.filename
    ).suffix.lower()


    # -----------------------------------------
    # Create unique filename
    # -----------------------------------------

    saved_filename = (

        f"{evidence_id}"

        f"{extension}"

    )


    file_path = (

        UPLOAD_DIR /

        saved_filename

    )


    # -----------------------------------------
    # Save uploaded file
    # -----------------------------------------

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


                total_size += len(
                    chunk
                )


                # -----------------------------------------
                # Check maximum file size
                # -----------------------------------------

                if (

                    total_size >

                    MAX_FILE_SIZE

                ):

                    file_path.unlink(
                        missing_ok=True
                    )

                    raise HTTPException(

                        status_code=413,

                        detail=(
                            "File exceeds "
                            "100 MB limit"
                        )

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

            detail=(

                "Failed to save file: "

                f"{str(e)}"

            )

        )


    # -----------------------------------------
    # Return upload result
    # -----------------------------------------

    return {

        "success":
            True,

        "evidence_id":
            evidence_id,

        "original_filename":
            file.filename,

        "file_type":
            file_type,

        "file_size":
            total_size,

        "stored_filename":
            saved_filename,

        "message":
            "Evidence uploaded successfully"

    }


# ============================================================
# 2. UNIFIED IMAGE ANALYSIS
# ============================================================

@router.post(
    "/evidence/analyze-image/{evidence_id}"
)
async def analyze_uploaded_image(
    evidence_id: str
):

    # -----------------------------------------
    # Find uploaded evidence
    # -----------------------------------------

    image_path = find_evidence_file(
        evidence_id
    )


    # -----------------------------------------
    # Get dedicated analysis directory
    # -----------------------------------------

    analysis_dir = get_analysis_dir(
        evidence_id
    )


    # -----------------------------------------
    # Run unified analysis
    # -----------------------------------------

    try:

        result = analyze_image_unified(

            image_path,

            analysis_dir

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

        print(
            "\n========== IMAGE ANALYSIS ERROR =========="
        )

        print(
            "Evidence ID:",
            evidence_id
        )

        print(
            "Image:",
            image_path
        )

        print(
            "Error:",
            repr(e)
        )

        print(
            "===========================================\n"
        )


        raise HTTPException(

            status_code=500,

            detail=str(e)

        )


# ============================================================
# 3. UNIFIED ANALYSIS ALIAS
# ============================================================
#
# This keeps your existing frontend/API calls working:
#
# POST /api/evidence/analyze/{evidence_id}
#
# Both endpoints now run the SAME unified pipeline.
#
# ============================================================

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

    image_path = image_files[0]

    # -----------------------------------------
    # Analysis directory
    # -----------------------------------------

    analysis_dir = (
        UPLOAD_DIR /
        "analysis" /
        evidence_id
    )

    analysis_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # -----------------------------------------
    # Run unified analysis
    # -----------------------------------------

    try:

        result = analyze_image_unified(
            image_path,
            analysis_dir
        )

        return {

            "success": True,

            "evidence_id":
                evidence_id,

            "analysis":
                result

        }

    except Exception as e:

        print(
            "Unified image analysis failed:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============================================================
# 4. GET FORENSIC ARTIFACT
# ============================================================

@router.get(
    "/evidence/artifacts/{evidence_id}/{artifact_type}"
)
async def get_evidence_artifact(
    evidence_id: str,
    artifact_type: str
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

    image_path = image_files[0]

    # -----------------------------------------
    # Analysis directory
    # -----------------------------------------

    analysis_dir = (
        UPLOAD_DIR /
        "analysis" /
        evidence_id
    )

    # -----------------------------------------
    # Artifact paths
    # -----------------------------------------

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

    # -----------------------------------------
    # Validate artifact type
    # -----------------------------------------

    if artifact_type not in artifact_map:

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid artifact type. "
                "Use ela, edges, wavelet, or copy_move."
            )
        )

    artifact_path = artifact_map[
        artifact_type
    ]

    # -----------------------------------------
    # Generate Copy-Move if missing
    # -----------------------------------------

    if (
        artifact_type == "copy_move"
        and
        not artifact_path.exists()
    ):

        try:

            detect_copy_move(
                str(image_path),
                output_dir=analysis_dir
            )

        except Exception as e:

            raise HTTPException(
                status_code=500,
                detail=(
                    "Copy-move artifact generation failed: "
                    f"{str(e)}"
                )
            )

    # -----------------------------------------
    # Check artifact
    # -----------------------------------------

    if not artifact_path.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                f"Artifact not found: {artifact_path}"
            )
        )

    # -----------------------------------------
    # Return artifact
    # -----------------------------------------

    return FileResponse(
        path=str(artifact_path),
        media_type="image/jpeg"
    )

# ============================================================
# 5. DOCUMENT ANALYSIS
# ============================================================

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

    document_path = document_files[0]

    try:

        result = analyze_document(

            str(document_path)

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


# ============================================================
# 6. SIGNATURE VERIFICATION
# ============================================================

@router.post(
    "/evidence/verify-signature"
)
async def verify_signature_endpoint(

    reference: UploadFile = File(...),

    query: UploadFile = File(...)

):

    try:

        # -----------------------------------------
        # Validate files
        # -----------------------------------------

        if not reference.filename:

            raise HTTPException(

                status_code=400,

                detail=(
                    "Reference signature "
                    "is required"
                )

            )


        if not query.filename:

            raise HTTPException(

                status_code=400,

                detail=(
                    "Query signature "
                    "is required"
                )

            )


        # -----------------------------------------
        # Temporary directory
        # -----------------------------------------

        with tempfile.TemporaryDirectory() as temp_dir:

            temp_path = Path(
                temp_dir
            )


            reference_ext = Path(
                reference.filename
            ).suffix.lower()


            query_ext = Path(
                query.filename
            ).suffix.lower()


            reference_path = (

                temp_path /

                f"reference{reference_ext}"

            )


            query_path = (

                temp_path /

                f"query{query_ext}"

            )


            # -----------------------------------------
            # Save reference signature
            # -----------------------------------------

            with open(

                reference_path,

                "wb"

            ) as buffer:

                buffer.write(

                    await reference.read()

                )


            # -----------------------------------------
            # Save query signature
            # -----------------------------------------

            with open(

                query_path,

                "wb"

            ) as buffer:

                buffer.write(

                    await query.read()

                )


            # -----------------------------------------
            # Run signature verification
            # -----------------------------------------

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


    except HTTPException:

        raise


    except Exception as e:

        raise HTTPException(

            status_code=500,

            detail=(

                "Signature verification "
                "failed: "

                f"{str(e)}"

            )

        )


# ============================================================
# 7. SIGNATURE VERIFICATION ALIAS
# ============================================================
#
# Keeps your existing frontend call:
#
# POST /api/signature/verify
#
# ============================================================

@router.post(
    "/signature/verify"
)
async def verify_signature_api(

    reference: UploadFile = File(...),

    query: UploadFile = File(...)

):

    allowed_extensions = {

        ".png",

        ".jpg",

        ".jpeg"

    }


    # -----------------------------------------
    # Validate filenames
    # -----------------------------------------

    if not reference.filename:

        raise HTTPException(

            status_code=400,

            detail=(
                "Reference signature "
                "is required"
            )

        )


    if not query.filename:

        raise HTTPException(

            status_code=400,

            detail=(
                "Query signature "
                "is required"
            )

        )


    # -----------------------------------------
    # Validate extensions
    # -----------------------------------------

    reference_ext = Path(

        reference.filename

    ).suffix.lower()


    query_ext = Path(

        query.filename

    ).suffix.lower()


    if reference_ext not in allowed_extensions:

        raise HTTPException(

            status_code=400,

            detail=(
                "Reference signature must be "
                "PNG, JPG, or JPEG"
            )

        )


    if query_ext not in allowed_extensions:

        raise HTTPException(

            status_code=400,

            detail=(
                "Query signature must be "
                "PNG, JPG, or JPEG"
            )

        )


    # -----------------------------------------
    # Temporary directory
    # -----------------------------------------

    signature_dir = Path(

        "data/temp/signatures"

    )


    signature_dir.mkdir(

        parents=True,

        exist_ok=True

    )


    reference_id = str(
        uuid.uuid4()
    )


    query_id = str(
        uuid.uuid4()
    )


    reference_path = (

        signature_dir /

        f"{reference_id}"
        f"{reference_ext}"

    )


    query_path = (

        signature_dir /

        f"{query_id}"
        f"{query_ext}"

    )


    try:

        # -----------------------------------------
        # Save reference
        # -----------------------------------------

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


        # -----------------------------------------
        # Save query
        # -----------------------------------------

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


        # -----------------------------------------
        # Run model
        # -----------------------------------------

        result = verify_signature(

            str(reference_path),

            str(query_path)

        )


        # -----------------------------------------
        # Return result
        # -----------------------------------------

        return {

            "success":
                True,

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
                "failed: "

                f"{str(e)}"

            )

        )


    finally:

        # -----------------------------------------
        # Cleanup
        # -----------------------------------------

        reference_path.unlink(
            missing_ok=True
        )

        query_path.unlink(
            missing_ok=True
        )


# ============================================================
# 8. COPY-MOVE ANALYSIS
# ============================================================

@router.post(
    "/evidence/analyze-copy-move/"
    "{evidence_id}"
)
async def analyze_copy_move_endpoint(

    evidence_id: str

):

    # -----------------------------------------
    # Find evidence
    # -----------------------------------------

    image_path = find_evidence_file(

        evidence_id

    )


    # -----------------------------------------
    # Get dedicated analysis directory
    # -----------------------------------------

    analysis_dir = get_analysis_dir(

        evidence_id

    )


    # -----------------------------------------
    # Run Copy-Move Detection
    # -----------------------------------------

    try:

        result = detect_copy_move(

            str(image_path),

            output_dir=analysis_dir

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