from pathlib import Path

from backend.models.signature.inference import (
    verify_signature as siamese_verify_signature
)


def verify_signature(
    reference_path: str,
    query_path: str
):

    reference_path = Path(
        reference_path
    )

    query_path = Path(
        query_path
    )


    # --------------------------------
    # Validate reference signature
    # --------------------------------

    if not reference_path.exists():

        raise FileNotFoundError(
            "Reference signature not found"
        )


    # --------------------------------
    # Validate query signature
    # --------------------------------

    if not query_path.exists():

        raise FileNotFoundError(
            "Query signature not found"
        )


    # --------------------------------
    # Run Siamese Network
    # --------------------------------

    result = siamese_verify_signature(

        str(reference_path),

        str(query_path)

    )


    # --------------------------------
    # Return result
    # --------------------------------

    return {

        "verdict":
            result["verdict"],

        "similarity":
            result["similarity"],

        "confidence":
            result["confidence"]

    }