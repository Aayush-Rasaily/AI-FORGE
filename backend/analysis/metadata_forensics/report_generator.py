"""Forensic metadata report generation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List


def _classify_issues(all_issues: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    classified = {
        "fake_metadata": [],
        "edited_metadata": [],
        "removed_metadata": [],
    }
    for issue in all_issues:
        itype = issue.get("type", "edited_metadata")
        if itype in classified:
            classified[itype].append(issue)
        else:
            classified["edited_metadata"].append(issue)
    return classified


def _severity_rank(severity: str) -> int:
    return {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(severity, 0)


def generate_forensic_report(
    exif_data: Dict[str, Any],
    module_results: Dict[str, Any],
    all_issues: List[Dict[str, Any]],
    risk_score: float,
) -> Dict[str, Any]:
    classified = _classify_issues(all_issues)
    sorted_issues = sorted(
        all_issues,
        key=lambda i: (_severity_rank(i.get("severity", "low")), i.get("score", 0)),
        reverse=True,
    )

    if risk_score >= 0.7:
        verdict = "CRITICAL METADATA RISK"
        recommendation = (
            "Multiple metadata integrity violations detected. "
            "Treat provenance as unreliable and perform manual chain-of-custody review."
        )
    elif risk_score >= 0.45:
        verdict = "HIGH METADATA RISK"
        recommendation = (
            "Significant metadata anomalies suggest editing or sanitization. "
            "Cross-validate with source device and capture context."
        )
    elif risk_score >= 0.25:
        verdict = "MEDIUM METADATA RISK"
        recommendation = "Some metadata inconsistencies found. Review before relying on EXIF provenance."
    else:
        verdict = "LOW METADATA RISK"
        recommendation = "Metadata appears largely consistent with image content."

    summary_lines = []
    if classified["fake_metadata"]:
        summary_lines.append(f"{len(classified['fake_metadata'])} fake metadata indicator(s).")
    if classified["edited_metadata"]:
        summary_lines.append(f"{len(classified['edited_metadata'])} editing/sanitization indicator(s).")
    if classified["removed_metadata"]:
        summary_lines.append(f"{len(classified['removed_metadata'])} stripped/missing metadata indicator(s).")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "risk_score": round(risk_score, 4),
        "risk_score_pct": round(risk_score * 100, 2),
        "confidence": round(0.75 + min(0.2, len(all_issues) * 0.03), 4),
        "recommendation": recommendation,
        "summary": " ".join(summary_lines) if summary_lines else "No significant metadata anomalies.",
        "issue_count": len(all_issues),
        "classified_issues": classified,
        "top_issues": sorted_issues[:10],
        "modules": {
            name: {
                "score": result.get("score", 0),
                "verdict": result.get("verdict", ""),
            }
            for name, result in module_results.items()
        },
        "exif_summary": {
            "camera": f"{exif_data.get('camera_make') or '?'} {exif_data.get('camera_model') or ''}".strip(),
            "software": exif_data.get("software"),
            "datetime_original": exif_data.get("datetime_original"),
            "gps": exif_data.get("gps"),
            "metadata_count": exif_data.get("metadata_count", 0),
        },
    }
