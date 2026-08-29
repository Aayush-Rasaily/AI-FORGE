from pathlib import Path

import pytest

from backend.contracts.adapters.reference_comparison import adapt_reference_comparison
from backend.contracts.forensic_finding import build_finding, normalize_bbox


def _finding(**overrides):
    values = {
        "evidence_id": "EVID-1",
        "title": "Compression anomaly",
        "finding_type": "compression_anomaly",
        "verdict": "Potential anomaly",
        "severity": "HIGH",
        "confidence": 0.21,
        "media_type": "image",
        "bbox": [10, 20, 30, 40],
        "observed_evidence": ["Observed local compression residual."],
        "short_explanation": "The region may be inconsistent.",
        "provenance": {"evidence_id": "EVID-1", "method": "ela"},
    }
    values.update(overrides)
    return build_finding(**values)


def test_ids_are_deterministic_and_confidence_normalizes():
    first = _finding(confidence=87)
    second = _finding(confidence=0.87)
    assert first.finding_id == second.finding_id
    assert first.confidence == second.confidence == 0.87


def test_severity_is_independent_from_confidence():
    finding = _finding(severity="CRITICAL", confidence=0.05)
    assert finding.severity == "CRITICAL"
    assert finding.confidence == 0.05


def test_no_evidence_and_placeholder_bbox_are_rejected():
    with pytest.raises(ValueError, match="observed evidence"):
        _finding(observed_evidence=[])
    with pytest.raises(ValueError, match="zero-area"):
        normalize_bbox([0, 0, 0, 25])
    assert _finding(bbox=None).location == "Document-wide"


def test_reference_adapter_does_not_fabricate_weak_comparisons():
    weak = {
        "reference": {
            "reference_id": "EVID-2",
            "comparison": {
                "field_comparisons": [{
                    "field": "Total", "examined_value": "10", "reference_value": "20",
                    "values_match": False, "correspondence": "weak_alignment",
                }]
            },
        }
    }
    assert adapt_reference_comparison(weak, "EVID-1") == []


def test_aggregation_is_deterministic_and_omits_unsupported_rows(tmp_path: Path):
    import json
    from backend.services.forensic_findings_service import build_forensic_findings

    (tmp_path / "evidence_localization.json").write_text(json.dumps({
        "regions": [
            {"type": "copy_move", "bbox": [1, 2, 20, 30], "confidence": 0.8,
             "severity": "HIGH", "evidence": ["Matched local feature clusters."]},
            {"type": "empty_claim", "bbox": [5, 5, 10, 10], "confidence": 0.99},
            {"type": "placeholder", "bbox": [0, 0, 0, 10], "evidence": ["Invalid box."]},
        ]
    }), encoding="utf-8")
    first = build_forensic_findings("EVID-1", tmp_path)
    second = build_forensic_findings("EVID-1", tmp_path)
    assert len(first["findings"]) == 1
    assert first["findings"][0]["finding_id"] == second["findings"][0]["finding_id"]
    assert (tmp_path / "forensic_findings.json").is_file()


def test_reference_link_validation_and_sidecar(monkeypatch, tmp_path: Path):
    import backend.services.reference_link_service as service

    evidence_files = {}
    for evidence_id in ("EVID-1", "EVID-2"):
        path = tmp_path / f"{evidence_id}.png"
        path.write_bytes(evidence_id.encode())
        evidence_files[evidence_id] = path

    monkeypatch.setattr(service, "get_evidence_record", lambda value: {
        "evidence_id": value, "media_type": "image",
        "sha256": value.lower(), "sha512": value.upper(),
    } if value in evidence_files else None)
    monkeypatch.setattr(service, "find_evidence_file", lambda value: evidence_files.get(value))
    monkeypatch.setattr(service, "get_analysis_dir",
                        lambda value, create=True: tmp_path / "analysis" / value)
    monkeypatch.setattr(service, "append_custody_event", lambda *args, **kwargs: {})
    monkeypatch.setattr(service, "append_audit_log", lambda *args, **kwargs: {})

    with pytest.raises(ValueError, match="itself"):
        service.create_reference_link("EVID-1", "EVID-1", relationship="duplicate")
    with pytest.raises(ValueError, match="authenticity_status"):
        service.create_reference_link(
            "EVID-1", "EVID-2", relationship="source", authenticity_status="trusted"
        )

    (tmp_path / "analysis" / "EVID-1").mkdir(parents=True)
    linked = service.create_reference_link(
        "EVID-1", "EVID-2", relationship="issuer copy",
        authenticity_status="unverified",
    )
    assert linked["comparison"]["side_by_side_available"] is True
    assert "not authenticated" in linked["provenance_caveat"]
    assert service.get_reference_link("EVID-1")["reference_id"] == "EVID-2"
