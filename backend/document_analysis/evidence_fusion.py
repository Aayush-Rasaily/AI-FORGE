from backend.document_analysis.risk_intelligence import (
    analyze_risk_intelligence
)


def fuse_evidence(
    evidence_list
):

    result = analyze_risk_intelligence(

        evidence_list

    )

    return result