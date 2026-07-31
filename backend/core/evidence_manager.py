import json
from pathlib import Path


# -----------------------------------------
# Evidence Registry
# -----------------------------------------

REGISTRY_DIR = Path(
    "data/temp"
)

REGISTRY_FILE = (
    REGISTRY_DIR /
    "evidence_registry.json"
)


# -----------------------------------------
# Ensure directory exists
# -----------------------------------------

REGISTRY_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# -----------------------------------------
# Generate next Evidence ID
# -----------------------------------------

def generate_evidence_id():

    # If registry doesn't exist
    if not REGISTRY_FILE.exists():

        data = {
            "last_id": 0
        }

    else:

        try:

            with open(
                REGISTRY_FILE,
                "r"
            ) as file:

                data = json.load(
                    file
                )

        except Exception:

            data = {
                "last_id": 0
            }


    # Increment ID
    last_id = (

        data.get(
            "last_id",
            0
        )

        + 1

    )


    # Update registry
    data["last_id"] = last_id


    # Save registry
    with open(
        REGISTRY_FILE,
        "w"
    ) as file:

        json.dump(

            data,

            file,

            indent=4

        )


    # Format ID
    evidence_id = (

        f"EVID-{last_id:04d}"

    )


    return evidence_id