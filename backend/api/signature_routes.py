import asyncio
import tempfile
import uuid

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException
)

from pathlib import Path
import tempfile

from backend.models.signature.inference import (
    verify_signature
)


router = APIRouter(
    prefix="/api/signature",
    tags=["Signature Verification"]
)
compare_alias_router = APIRouter(
    prefix="/signature",
    tags=["Signature Verification"],
)


@router.post("/compare")
async def compare_signature_endpoint(
    reference: UploadFile = File(...),
    questioned: UploadFile = File(...),
):
    """Compare a reference signature with a questioned signature."""
    allowed_extensions = {".png", ".jpg", ".jpeg"}
    reference_name = reference.filename or ""
    questioned_name = questioned.filename or ""
    reference_ext = Path(reference_name).suffix.lower()
    questioned_ext = Path(questioned_name).suffix.lower()
    if reference_ext not in allowed_extensions or questioned_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Reference and questioned signatures must be PNG, JPG, or JPEG",
        )

    comparison_id = f"SIG-COMP-{uuid.uuid4().hex[:12].upper()}"
    from backend.evidence.paths import get_analysis_dir
    from backend.services.signature_comparison_service import compare_signatures

    with tempfile.TemporaryDirectory(prefix="aiforge_signature_") as temp_dir:
        temp_path = Path(temp_dir)
        reference_path = temp_path / f"reference{reference_ext}"
        questioned_path = temp_path / f"questioned{questioned_ext}"
        reference_path.write_bytes(await reference.read())
        questioned_path.write_bytes(await questioned.read())
        result = await asyncio.to_thread(
            compare_signatures,
            reference_path,
            questioned_path,
            evidence_id=comparison_id,
            analysis_dir=get_analysis_dir(comparison_id),
        )

    return {
        "success": True,
        "evidence_id": comparison_id,
        "result": result,
        "signature_verification": result,
    }


compare_alias_router.add_api_route(
    "/compare",
    compare_signature_endpoint,
    methods=["POST"],
)


@router.post("/verify")
async def verify_signature_endpoint(

    original: UploadFile = File(...),

    test: UploadFile = File(...)

):

    try:

        # -----------------------------
        # Validate files
        # -----------------------------

        if not original.filename:

            raise HTTPException(

                status_code=400,

                detail=(
                    "Original signature "
                    "file is required"
                )

            )


        if not test.filename:

            raise HTTPException(

                status_code=400,

                detail=(
                    "Test signature "
                    "file is required"
                )

            )


        # -----------------------------
        # Temporary directory
        # -----------------------------

        with tempfile.TemporaryDirectory() as temp_dir:

            temp_path = Path(
                temp_dir
            )


            original_path = (

                temp_path /

                "original.png"

            )


            test_path = (

                temp_path /

                "test.png"

            )


            # -----------------------------
            # Save original signature
            # -----------------------------

            with open(

                original_path,

                "wb"

            ) as buffer:

                buffer.write(

                    await original.read()

                )


            # -----------------------------
            # Save test signature
            # -----------------------------

            with open(

                test_path,

                "wb"

            ) as buffer:

                buffer.write(

                    await test.read()

                )


            # -----------------------------
            # Run Siamese model
            # -----------------------------

            result = verify_signature(

                str(original_path),

                str(test_path)

            )


            # -----------------------------
            # Return result
            # -----------------------------

            return {

                "success":

                    True,

                "result":

                    result

            }


    except HTTPException:

        raise


    except Exception as e:

        raise HTTPException(

            status_code=500,

            detail=str(e)

        )