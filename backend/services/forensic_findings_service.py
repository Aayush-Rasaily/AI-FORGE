"""Load, normalize, deduplicate, and atomically persist canonical findings."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List

from backend.contracts.adapters import (
    adapt_analysis, adapt_copy_move, adapt_document_tampering, adapt_jury_or_dossier,
    adapt_localization, adapt_ocr_document,
    adapt_reference_comparison,
)
from backend.contracts.forensic_finding import ForensicFinding
from backend.evidence.paths import get_analysis_dir

logger = logging.getLogger("ai_forge.forensic_findings")
OUTPUT_FILENAME = "forensic_findings.json"


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _dedupe(findings: List[ForensicFinding]) -> List[Dict[str, Any]]:
    """Merge semantically identical rows while retaining all provenance."""
    merged: Dict[tuple, Dict[str, Any]] = {}
    severity_rank = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
    for finding in sorted(findings, key=lambda item: item.finding_id):
        item = finding.to_dict()
        bbox = item.get("bbox") or {}
        key = (
            str(item.get("type", "")).lower(),
            item.get("page"), item.get("frame"),
            round(float(item.get("time_seconds") or 0), 2),
            tuple(round(float(bbox.get(k, 0)), 2) for k in ("x", "y", "width", "height")),
            str(item.get("location", "")).lower(),
        )
        existing = merged.get(key)
        if existing is None:
            merged[key] = item
            continue
        existing["confidence"] = max(existing["confidence"], item["confidence"])
        if severity_rank[item["severity"]] > severity_rank[existing["severity"]]:
            existing["severity"] = item["severity"]
        existing["observed_evidence"] = sorted(set(
            existing["observed_evidence"] + item["observed_evidence"]
        ))
        known = {
            json.dumps(p, sort_keys=True, default=str)
            for p in existing["evidence_chain"]
        }
        existing["evidence_chain"].extend(
            p for p in item["evidence_chain"]
            if json.dumps(p, sort_keys=True, default=str) not in known
        )
    result = sorted(merged.values(), key=lambda item: (
        -{"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}[item["severity"]],
        -item["confidence"], item["finding_id"],
    ))
    for item in result:
        item["provenance"] = list(item["evidence_chain"])
    return result


def _summary(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts = {level: 0 for level in ("LOW", "MEDIUM", "HIGH", "CRITICAL")}
    for item in findings:
        counts[item["severity"]] += 1
    if counts["CRITICAL"]:
        level, verdict = "CRITICAL", "Critical indicators warrant prompt qualified review."
    elif counts["HIGH"]:
        level, verdict = "HIGH", "Material indicators may be consistent with alteration."
    elif counts["MEDIUM"]:
        level, verdict = "MEDIUM", "Some indicators warrant contextual or source comparison."
    elif counts["LOW"]:
        level, verdict = "LOW", "Limited indicators were observed; their significance is uncertain."
    else:
        level, verdict = "LOW", (
            "No supported canonical findings were produced. This does not establish authenticity."
        )
    return {
        "finding_count": len(findings),
        "severity_counts": counts,
        "overall_severity": level,
        "conclusion": verdict,
        "requires_human_review": bool(findings),
    }


def _provenance_context(evidence_id: str, analysis_dir: Path) -> Dict[str, Any]:
    metadata = _read_json(analysis_dir / "metadata.json")
    try:
        from backend.forensics.repository import get_evidence_record
        record = get_evidence_record(evidence_id) or {}
    except Exception:
        record = {}
    return {
        "sha256": record.get("sha256") or metadata.get("sha256"),
        "source_file": (
            record.get("stored_path") or
            metadata.get("original_path") or
            metadata.get("working_path")
        ),
        "observed_at": (
            record.get("intake_timestamp") or
            metadata.get("archived_at") or
            metadata.get("created_at")
        ),
    }


def build_forensic_findings(
    evidence_id: str,
    analysis_dir: Path | None = None,
    *,
    write: bool = True,
) -> Dict[str, Any]:
    analysis_dir = Path(analysis_dir or get_analysis_dir(evidence_id))
    sources: List[tuple[str, Callable[[Dict[str, Any], str, str], List[ForensicFinding]]]] = [
        ("evidence_localization.json", adapt_localization),
        ("localization.json", adapt_localization),
        ("forgery_localization.json", adapt_localization),
        ("ocr_difference_report.json", adapt_ocr_document),
        ("reference_comparison.json", adapt_ocr_document),
        ("jury.json", adapt_jury_or_dossier),
        ("forensic_dossier.json", adapt_jury_or_dossier),
        ("analysis.json", adapt_analysis),
        ("signature_analysis.json", adapt_analysis),
        ("document_tampering.json", adapt_document_tampering),
        ("copymove.json", adapt_copy_move),
        ("video_analysis.json", adapt_analysis),
        ("reference_link.json", adapt_reference_comparison),
    ]
    all_findings: List[ForensicFinding] = []
    loaded_sources: List[str] = []
    for filename, adapter in sources:
        path = analysis_dir / filename
        if not path.is_file():
            continue
        data = _read_json(path)
        if not data:
            continue
        try:
            all_findings.extend(adapter(data, evidence_id, filename))
            loaded_sources.append(filename)
        except Exception as exc:
            logger.warning("finding_adapter_failed | %s | %s | %s", evidence_id, filename, exc)

    findings = _dedupe(all_findings)
    context = _provenance_context(evidence_id, analysis_dir)
    for finding in findings:
        for source in finding.get("evidence_chain") or []:
            source["sha256"] = source.get("sha256") or context["sha256"]
            source["source_file"] = source.get("source_file") or context["source_file"]
            source["observed_at"] = source.get("observed_at") or context["observed_at"]
    payload = {
        "schema_version": "1.0",
        "success": True,
        "evidence_id": evidence_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "findings": findings,
        "summary": {**_summary(findings), "sources_loaded": sorted(loaded_sources)},
    }
    if write:
        analysis_dir.mkdir(parents=True, exist_ok=True)
        path = analysis_dir / OUTPUT_FILENAME
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)
    return payload


def get_or_build_forensic_findings(evidence_id: str, analysis_dir: Path | None = None) -> Dict[str, Any]:
    analysis_dir = Path(analysis_dir or get_analysis_dir(evidence_id))
    path = analysis_dir / OUTPUT_FILENAME
    if path.is_file():
        payload = _read_json(path)
        if payload.get("schema_version") == "1.0" and isinstance(payload.get("findings"), list):
            payload["success"] = True
            return payload
    return build_forensic_findings(evidence_id, analysis_dir)
