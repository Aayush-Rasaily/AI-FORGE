"""
Metadata forensics engine — orchestrates all metadata analysis modules.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from backend.analysis.metadata_forensics.camera_fingerprint import validate_camera_fingerprint
from backend.analysis.metadata_forensics.content_comparison import compare_metadata_content
from backend.analysis.metadata_forensics.editing_software import detect_editing_software
from backend.analysis.metadata_forensics.exif_analyzer import extract_exif
from backend.analysis.metadata_forensics.gps_validator import validate_gps
from backend.analysis.metadata_forensics.hash_consistency import validate_hash_consistency
from backend.analysis.metadata_forensics.hidden_metadata import scan_hidden_metadata
from backend.analysis.metadata_forensics.report_generator import generate_forensic_report
from backend.analysis.metadata_forensics.thumbnail_verification import verify_thumbnail
from backend.analysis.metadata_forensics.timezone_validator import validate_timezone

logger = logging.getLogger("ai_forge.metadata_forensics")

MODULE_WEIGHTS = {
    "gps": 0.12,
    "timezone": 0.12,
    "camera_fingerprint": 0.10,
    "editing_software": 0.18,
    "thumbnail": 0.14,
    "hash": 0.08,
    "hidden": 0.10,
    "content": 0.16,
}


def _collect_issues(*module_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    for result in module_results:
        for issue in result.get("issues", []) or []:
            issues.append(dict(issue))
    return issues


def _compute_risk_score(module_results: Dict[str, Dict[str, Any]], exif_data: Dict[str, Any]) -> float:
    weighted = 0.0
    for key, weight in MODULE_WEIGHTS.items():
        score = float(module_results.get(key, {}).get("score", 0))
        weighted += score * weight

    if not exif_data.get("metadata_found"):
        weighted = max(weighted, 0.35)

    return min(1.0, weighted)


def analyze_metadata_forensics(image_path: str) -> Dict[str, Any]:
    """Run full metadata forensics pipeline and return forensic report."""
    exif_data = extract_exif(image_path)
    hidden = scan_hidden_metadata(image_path)

    gps_result = validate_gps(exif_data.get("gps") or {})
    timezone_result = validate_timezone(exif_data)
    camera_result = validate_camera_fingerprint(exif_data)
    software_result = detect_editing_software(exif_data, hidden)
    thumbnail_result = verify_thumbnail(image_path)
    hash_result = validate_hash_consistency(image_path, exif_data)
    content_result = compare_metadata_content(image_path, exif_data)

    module_results = {
        "exif": exif_data,
        "gps": gps_result,
        "timezone": timezone_result,
        "camera_fingerprint": camera_result,
        "editing_software": software_result,
        "thumbnail": thumbnail_result,
        "hash": hash_result,
        "hidden": hidden,
        "content": content_result,
    }

    all_issues = _collect_issues(
        gps_result, timezone_result, camera_result, software_result,
        thumbnail_result, hash_result, hidden, content_result,
    )

    if not exif_data.get("metadata_found"):
        all_issues.append({
            "type": "removed_metadata",
            "severity": "medium",
            "description": "EXIF metadata completely stripped from file.",
            "score": 0.4,
        })

    risk_score = _compute_risk_score(
        {k: v for k, v in module_results.items() if k != "exif"},
        exif_data,
    )
    report = generate_forensic_report(exif_data, module_results, all_issues, risk_score)

    suspicious_reasons = [i["description"] for i in all_issues[:8]]

    return {
        # Backward-compatible fields
        "metadata_found": exif_data.get("metadata_found", False),
        "metadata_missing": not exif_data.get("metadata_found", False),
        "metadata_count": exif_data.get("metadata_count", 0),
        "suspicious": risk_score >= 0.35 or bool(all_issues),
        "software_detected": software_result.get("software_detected", False),
        "software": software_result.get("software") or exif_data.get("software"),
        "camera_make": exif_data.get("camera_make"),
        "camera_model": exif_data.get("camera_model"),
        "creation_time": exif_data.get("datetime_original") or exif_data.get("datetime_modified"),
        "modification_time": exif_data.get("datetime_modified"),
        "suspicious_reasons": suspicious_reasons,
        "metadata_risk_score": round(risk_score, 4),
        "metadata_risk_pct": round(risk_score * 100, 2),
        # Full forensics payload
        "modules": module_results,
        "issues": all_issues,
        "classified": report.get("classified_issues", {}),
        "fake_metadata_detected": len(report.get("classified_issues", {}).get("fake_metadata", [])) > 0,
        "edited_metadata_detected": len(report.get("classified_issues", {}).get("edited_metadata", [])) > 0,
        "removed_metadata_detected": len(report.get("classified_issues", {}).get("removed_metadata", [])) > 0,
        "forensic_report": report,
    }
