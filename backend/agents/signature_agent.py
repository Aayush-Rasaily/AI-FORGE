from pathlib import Path


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


    if not reference_path.exists():

        raise FileNotFoundError(
            "Reference signature not found"
        )


    if not query_path.exists():

        raise FileNotFoundError(
            "Query signature not found"
        )


    # TODO:
    # Load trained Siamese Network
    # Generate embeddings
    # Calculate similarity


    return {

        "verdict":
            "Not Implemented",

        "similarity":
            0.0,

        "confidence":
            0.0

    }