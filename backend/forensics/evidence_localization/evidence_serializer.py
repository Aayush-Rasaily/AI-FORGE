"""
Evidence Serializer — Stage 4 of the Evidence Localization Engine.

Converts ScoredRegion objects into the canonical evidence_localization.json
format and writes it atomically to the analysis directory.

Output schema (schema_version "1.0"):
{
  "schema_version": "1.0",
  "evidence_id": "<uuid>",
  "generated_at": "<ISO-8601 UTC>",
  "region_count": <int>,
  "summary": {
    "highest_confidence": <float>,
    "manipulation_types": [<str>, ...],
    "corroborated_regions": <int>,
    "sources_used": [<str>, ...]
  },
  "regions": [
    {
      "id": "region_001",
      "type": "<manipulation_type>",
      "bbox": [x, y, w, h],
      "confidence": <float>,
      "evidence": ["<label>", ...],
      "source_signals": ["<source>", ...],
      "corroborated": <bool>
    },
    ...
  ]
}

The file is written atomically using a .tmp intermediary to prevent
partial-write corruption.  The output is fully deterministic — identical
inputs always produce identical JSON (same key ordering, same float rounding).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from backend.forensics.evidence_localization.confidence_scorer import ScoredRegion

logger = logging.getLogger("ai_forge.evidence_localization.serializer")

SCHEMA_VERSION = "1.0"
OUTPUT_FILENAME = "evidence_localization.json"


def _region_to_dict(region: ScoredRegion) -> Dict[str, Any]:
    """
    Convert a ScoredRegion to the canonical JSON-serialisable dict.
    bbox is always a [x, y, w, h] list (not a dict) for frontend compatibility.
    """
    x, y, w, h = (int(v) for v in region.bbox)
    return {
        "id": region.region_id,
        "type": region.manipulation_type,
        "bbox": [x, y, w, h],
        "confidence": round(float(region.confidence), 4),
        "evidence": [str(e) for e in region.evidence],
        "source_signals": [str(s) for s in region.source_signals],
        "corroborated": bool(region.corroborated),
    }


def _build_summary(regions: List[ScoredRegion]) -> Dict[str, Any]:
    if not regions:
        return {
            "highest_confidence": 0.0,
            "manipulation_types": [],
            "corroborated_regions": 0,
            "sources_used": [],
        }

    types_seen: List[str] = []
    for r in regions:
        if r.manipulation_type not in types_seen:
            types_seen.append(r.manipulation_type)

    sources_seen: List[str] = []
    for r in regions:
        for s in r.source_signals:
            if s not in sources_seen:
                sources_seen.append(s)

    return {
        "highest_confidence": round(float(regions[0].confidence), 4),
        "manipulation_types": sorted(types_seen),
        "corroborated_regions": sum(1 for r in regions if r.corroborated),
        "sources_used": sorted(sources_seen),
    }


def serialize_evidence(
    evidence_id: str,
    analysis_dir: Path,
    scored_regions: List[ScoredRegion],
) -> Dict[str, Any]:
    """
    Serialize scored regions to evidence_localization.json.

    Performs an atomic write: data is first written to a .tmp file,
    then renamed to the final path.

    Parameters
    ----------
    evidence_id     : The evidence UUID string.
    analysis_dir    : Directory where evidence_localization.json will be saved.
    scored_regions  : Output from confidence_scorer.score_regions()

    Returns
    -------
    The serialized dict (mirrors what was written to disk).
    """
    analysis_dir = Path(analysis_dir)
    analysis_dir.mkdir(parents=True, exist_ok=True)

    output: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": str(evidence_id),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "region_count": len(scored_regions),
        "summary": _build_summary(scored_regions),
        "regions": [_region_to_dict(r) for r in scored_regions],
    }

    out_path = analysis_dir / OUTPUT_FILENAME
    tmp_path = out_path.with_suffix(".tmp")

    try:
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(output, fh, indent=2, ensure_ascii=False, sort_keys=False)
        # Atomic rename
        tmp_path.replace(out_path)
    except Exception as exc:
        # Clean up temp file if rename failed
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise RuntimeError(
            f"evidence_localization: failed to write {out_path}: {exc}"
        ) from exc

    logger.info(
        "evidence_localization: saved %d regions → %s",
        len(scored_regions),
        out_path,
    )

    return output
