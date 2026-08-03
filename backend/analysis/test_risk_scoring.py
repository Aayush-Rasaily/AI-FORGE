from backend.analysis.risk_scoring import (
    calculate_risk_score
)


result = calculate_risk_score(

    ela_score=0.04,

    wavelet_score=0.45,

    edge_density=0.30,

    copy_move_score=0.44,

    copy_move_detected=True,

    noise_inconsistency=1.2,

    metadata_suspicious=False,

    software_detected=False

)


print("\n==============================")

print(
    "RISK SCORE:",
    result["risk_score"]
)

print(
    "RISK LEVEL:",
    result["risk_level"]
)

print(
    "CONFIDENCE:",
    result["confidence"]
)

print(
    "SIGNALS:",
    result["signals_triggered"]
)

print(
    "EVIDENCE:"
)

for evidence in result["evidence"]:

    print(
        "-",
        evidence
    )

print(
    "==============================\n"
)