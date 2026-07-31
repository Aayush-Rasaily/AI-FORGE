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