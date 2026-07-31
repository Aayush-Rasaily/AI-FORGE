from backend.models.signature.inference import (
    verify_signature
)


reference = (
    "data/signatures/full_org/"
    "original_1_1.png"
)


query = (
    "data/signatures/full_forg/"
    "forgeries_1_2.png"
)


result = verify_signature(

    reference,

    query

)


print(
    "\nSignature Verification Result"
)

print(
    "=============================="
)

print(
    result
)