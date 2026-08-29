"""
Forensic Reasoning Engine — evidence graph + inference over detector outputs.

Transforms raw detector scores into forensic conclusions:
  OCR → Font mismatch → ELA → Compression mismatch → Metadata → Photoshop → Invoice Amount Edited

Every conclusion cites supporting detector evidence. No hallucinated detectors.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.engines.contracts import DetectorOutput, FusionResult

logger = logging.getLogger("ai_forge.engines.reasoning")

_ELEVATED = 0.35
_STRONG = 0.55

_INVOICE_RE = re.compile(
    r"\b(invoice|bill|amount|total|subtotal|tax|gst|vat|due|payable|grand\s*total)\b",
    re.IGNORECASE,
)
_DATE_RE = re.compile(r"\b(date|dated|issue\s*date|due\s*date)\b", re.IGNORECASE)
_SIGNATURE_RE = re.compile(r"\b(signature|signed|authorised|authorized)\b", re.IGNORECASE)
_PHOTOSHOP_RE = re.compile(r"photoshop|adobe\s*photoshop|gimp|lightroom|paint\.net", re.IGNORECASE)


def _f(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _det_map(detectors: List[DetectorOutput]) -> Dict[str, DetectorOutput]:
    return {str(d.get("detector_name", "")).lower(): d for d in detectors if d.get("detector_name")}


def _is_elevated(d: Optional[DetectorOutput]) -> bool:
    if not d or d.get("status") not in (None, "ok"):
        return False
    return _f(d.get("score")) >= _ELEVATED


def _is_strong(d: Optional[DetectorOutput]) -> bool:
    if not d:
        return False
    return _f(d.get("score")) >= _STRONG


def _obs_id(kind: str, suffix: str = "") -> str:
    s = re.sub(r"[^a-z0-9_]+", "_", kind.lower()).strip("_")
    return f"evidence:{s}{'_' + suffix if suffix else ''}"


def _node(
    node_id: str,
    node_type: str,
    label: str,
    *,
    source: str = "",
    score: float = 0.0,
    confidence: float = 0.0,
    detail: str = "",
    metrics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "id": node_id,
        "type": node_type,
        "label": label,
        "source": source,
        "score": round(score, 4),
        "confidence": round(confidence, 4),
        "detail": detail,
        "metrics": metrics or {},
    }


def _edge(frm: str, to: str, relation: str, *, weight: float = 1.0) -> Dict[str, Any]:
    return {"from": frm, "to": to, "relation": relation, "weight": round(weight, 4)}


def _ocr_text(analysis: Dict[str, Any]) -> str:
    for key in ("ocr", "text_layout", "font_consistency"):
        block = analysis.get(key) or {}
        if isinstance(block, dict):
            for k in ("full_text", "text", "ocr_text", "extracted_text", "summary"):
                if block.get(k):
                    return str(block[k])
            words = block.get("words") or block.get("lines") or []
            if isinstance(words, list):
                return " ".join(
                    str(w.get("text", w) if isinstance(w, dict) else w) for w in words[:200]
                )
    return str(analysis.get("ocr_text") or "")


def _extract_observations(
    detectors: Dict[str, DetectorOutput],
    analysis: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Build evidence observation nodes + detector→evidence edges from detector outputs."""
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    ocr_text = _ocr_text(analysis)

    def add_obs(
        det_name: str,
        obs_kind: str,
        label: str,
        *,
        min_score: float = _ELEVATED,
        detail: str = "",
    ) -> Optional[str]:
        d = detectors.get(det_name)
        if not d or d.get("status") not in (None, "ok"):
            return None
        score = _f(d.get("score"))
        if score < min_score:
            return None
        conf = _f(d.get("confidence"), 0.5)
        nid = _obs_id(obs_kind, det_name)
        reason = detail or (d.get("technical_reason") or "").strip()
        nodes.append(_node(
            nid, "evidence", label,
            source=det_name, score=score, confidence=conf,
            detail=reason,
            metrics=d.get("metrics") or {},
        ))
        edges.append(_edge(f"detector:{det_name}", nid, "produces", weight=score))
        return nid

    # Detector source nodes
    for name, d in detectors.items():
        if d.get("status") not in (None, "ok"):
            continue
        nodes.append(_node(
            f"detector:{name}", "detector", name.replace("_", " ").title(),
            source=name,
            score=_f(d.get("score")),
            confidence=_f(d.get("confidence"), 0.5),
            detail=(d.get("technical_reason") or "").strip(),
            metrics=d.get("metrics") or {},
        ))

    # OCR / font observations
    font_d = detectors.get("font")
    ocr_d = detectors.get("ocr")
    font_block = analysis.get("font_consistency") or {}
    font_mismatch = (
        _is_elevated(font_d)
        or bool(font_block.get("mismatch_detected"))
        or bool(font_block.get("inconsistent_fonts"))
        or "font" in (ocr_d or {}).get("technical_reason", "").lower()
    )
    if font_mismatch:
        detail = ""
        if font_d and font_d.get("technical_reason"):
            detail = str(font_d["technical_reason"])
        elif font_block.get("explanation"):
            detail = str(font_block["explanation"])
        elif ocr_d and ocr_d.get("technical_reason"):
            detail = str(ocr_d["technical_reason"])
        src = "font" if _is_elevated(font_d) else "ocr"
        nid = add_obs(src, "font_mismatch", "Font mismatch", detail=detail or "Inconsistent typography in text region.")
        if nid and src == "ocr" and _is_elevated(font_d):
            edges.append(_edge("detector:font", nid, "corroborates", weight=_f(font_d.get("score"))))

    # ELA compression
    ela_d = detectors.get("ela")
    if _is_elevated(ela_d):
        reason = str(ela_d.get("technical_reason") or "")
        label = "Compression mismatch"
        if "recompression" in reason.lower() or "compression" in reason.lower():
            label = "Compression mismatch"
        add_obs("ela", "compression_mismatch", label, detail=reason)

    # Metadata editing software
    meta_d = detectors.get("metadata")
    if _is_elevated(meta_d):
        metrics = meta_d.get("metrics") or {}
        software = metrics.get("software") or analysis.get("signals", {}).get("software")
        suspicious = bool(metrics.get("suspicious"))
        reason = str(meta_d.get("technical_reason") or "")
        if software or suspicious or _PHOTOSHOP_RE.search(reason):
            sw = str(software or "")
            if _PHOTOSHOP_RE.search(reason) and not sw:
                m = _PHOTOSHOP_RE.search(reason)
                sw = m.group(0) if m else "editing software"
            label = f"Edited using {sw}" if sw else "Metadata editing indicators"
            add_obs("metadata", "metadata_editing", label, detail=reason)

    # Other forensic observations
    if _is_elevated(detectors.get("copy_move")):
        add_obs("copy_move", "cloned_region", "Duplicated / cloned region")
    if _is_elevated(detectors.get("noise")):
        add_obs("noise", "noise_inconsistency", "Noise pattern inconsistency")
    if _is_elevated(detectors.get("wavelet")):
        add_obs("wavelet", "frequency_anomaly", "Frequency-domain anomaly")
    if _is_elevated(detectors.get("deepfake")):
        add_obs("deepfake", "face_manipulation", "Face / identity manipulation")
    if _is_elevated(detectors.get("gan")):
        add_obs("gan", "ai_generated", "AI-generated content indicators")
    if _is_elevated(detectors.get("tampering")):
        add_obs("tampering", "structural_tampering", "Structural tampering detected")

    # Context flags (not detectors — derived from OCR text only)
    ctx_nodes: List[Dict[str, Any]] = []
    if _INVOICE_RE.search(ocr_text):
        ctx = _node("context:invoice", "context", "Invoice document context", detail=ocr_text[:200])
        ctx_nodes.append(ctx)
    if _DATE_RE.search(ocr_text):
        ctx_nodes.append(_node("context:date_field", "context", "Date field present", detail=""))
    if _SIGNATURE_RE.search(ocr_text):
        ctx_nodes.append(_node("context:signature", "context", "Signature field present", detail=""))

    return nodes + ctx_nodes, edges


def _obs_labels(nodes: List[Dict[str, Any]]) -> Set[str]:
    return {
        n["id"].split(":", 1)[-1] if ":" in n["id"] else n["id"]
        for n in nodes if n.get("type") == "evidence"
    }


def _has_obs_kind(obs_kinds: Set[str], prefix: str) -> bool:
    return any(k == prefix or k.startswith(f"{prefix}_") for k in obs_kinds)


def _infer_findings(
    evidence_nodes: List[Dict[str, Any]],
    context_nodes: List[Dict[str, Any]],
    detectors: Dict[str, DetectorOutput],
    fusion: FusionResult,
    analysis: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Correlate evidence nodes into forensic findings."""
    obs_ids = {n["id"] for n in evidence_nodes if n.get("type") == "evidence"}
    obs_kinds = _obs_labels(evidence_nodes)
    ctx_kinds = {n["id"] for n in context_nodes}
    findings: List[Dict[str, Any]] = []

    def supporting_for(*kinds: str) -> List[Dict[str, Any]]:
        out = []
        for n in evidence_nodes:
            if n.get("type") != "evidence":
                continue
            kind = n["id"].split(":", 1)[-1]
            if not any(kind.startswith(k) or k in kind for k in kinds):
                continue
            out.append({
                "detector": n.get("source", ""),
                "observation": n.get("label", ""),
                "detail": n.get("detail", ""),
                "score": n.get("score", 0),
                "confidence": n.get("confidence", 0),
            })
        return out

    def confidence_from(supporting: List[Dict[str, Any]], base: float = 0.5) -> float:
        if not supporting:
            return base
        weights = [
            _f(s.get("score")) * _f(s.get("confidence"), 0.5)
            for s in supporting
        ]
        mean_w = sum(weights) / len(weights)
        boost = min(0.25, 0.05 * len(supporting))
        return min(0.995, base + mean_w * 0.45 + boost)

    def contradictory() -> List[Dict[str, Any]]:
        contra: List[Dict[str, Any]] = []
        low_detectors = [
            name for name, d in detectors.items()
            if d.get("status") in (None, "ok") and 0.05 < _f(d.get("score")) < _ELEVATED
        ]
        for name in low_detectors[:4]:
            d = detectors[name]
            contra.append({
                "detector": name,
                "observation": f"{name.replace('_', ' ').title()} below manipulation threshold",
                "detail": d.get("technical_reason", ""),
                "score": _f(d.get("score")),
            })
        # Strong negative: metadata not suspicious while others fire
        meta = detectors.get("metadata")
        if meta and not _is_elevated(meta) and len(obs_kinds) >= 2:
            contra.append({
                "detector": "metadata",
                "observation": "Metadata appears consistent with capture device",
                "detail": meta.get("technical_reason", ""),
                "score": _f(meta.get("score")),
            })
        return contra

    def add_finding(
        finding_id: str,
        title: str,
        supporting_kinds: Tuple[str, ...],
        *,
        base_conf: float = 0.55,
        recommendation: str = "",
        priority: int = 0,
    ) -> None:
        support = supporting_for(*supporting_kinds)
        if not support:
            return
        conf = confidence_from(support, base_conf)
        contra = contradictory()
        findings.append({
            "id": finding_id,
            "finding": title,
            "supporting_evidence": support,
            "confidence": round(conf * 100, 1),
            "contradictory_evidence": contra[:5],
            "recommendation": recommendation or _default_recommendation(title, conf),
            "priority": priority,
            "evidence_node_ids": [
                n["id"] for n in evidence_nodes
                if n.get("type") == "evidence"
                and any(k in n["id"] for k in supporting_kinds)
            ],
        })

    has_invoice_ctx = "context:invoice" in ctx_kinds
    has_font = _has_obs_kind(obs_kinds, "font_mismatch")
    has_compression = _has_obs_kind(obs_kinds, "compression_mismatch")
    has_meta_edit = _has_obs_kind(obs_kinds, "metadata_editing")

    # Primary chained inference (user example)
    if has_font and has_compression and (has_meta_edit or has_invoice_ctx):
        add_finding(
            "finding:invoice_amount_edited",
            "Invoice Amount Edited",
            ("font_mismatch", "compression_mismatch", "metadata_editing"),
            base_conf=0.72,
            recommendation="Verify invoice totals against source accounting records and issuer API.",
            priority=100,
        )
    elif has_font and has_compression and has_invoice_ctx:
        add_finding(
            "finding:invoice_text_edited",
            "Invoice Text Field Edited",
            ("font_mismatch", "compression_mismatch"),
            base_conf=0.68,
            recommendation="Compare numeric and textual fields with issuer originals.",
            priority=90,
        )

    if has_font and "context:date_field" in ctx_kinds:
        add_finding(
            "finding:date_altered",
            "Document Date Altered",
            ("font_mismatch", "compression_mismatch"),
            base_conf=0.65,
            recommendation="Cross-check document date against metadata timestamps and issuer records.",
            priority=80,
        )

    if "cloned_region" in obs_kinds or _has_obs_kind(obs_kinds, "cloned_region"):
        add_finding(
            "finding:region_spliced",
            "Region Spliced or Cloned",
            ("cloned_region", "compression_mismatch"),
            base_conf=0.70,
            recommendation="Inspect cloned regions for source provenance and duplicate block alignment.",
            priority=85,
        )

    if _has_obs_kind(obs_kinds, "face_manipulation") or _has_obs_kind(obs_kinds, "ai_generated"):
        add_finding(
            "finding:synthetic_content",
            "Synthetic or Deepfake Content",
            ("face_manipulation", "ai_generated"),
            base_conf=0.75,
            recommendation="Perform frame-level provenance analysis and source device verification.",
            priority=95,
        )

    if _has_obs_kind(obs_kinds, "noise_inconsistency") and has_compression:
        add_finding(
            "finding:localized_retouch",
            "Localized Retouching Detected",
            ("noise_inconsistency", "compression_mismatch"),
            base_conf=0.62,
            recommendation="Review localized noise and compression boundaries under ELA overlay.",
            priority=70,
        )

    if "context:signature" in ctx_kinds and (has_font or has_compression):
        add_finding(
            "finding:signature_anomaly",
            "Signature Region Anomaly",
            ("font_mismatch", "compression_mismatch", "noise_inconsistency"),
            base_conf=0.64,
            recommendation="Compare signature against authenticated specimens and pressure dynamics.",
            priority=75,
        )

    # Fallback: multi-detector convergence without specific template
    elevated = [n for n in evidence_nodes if n.get("type") == "evidence"]
    if not findings and len(elevated) >= 2:
        kinds = tuple(obs_kinds)
        add_finding(
            "finding:multi_detector_manipulation",
            "Multi-Detector Manipulation Indicators",
            kinds,
            base_conf=0.58,
            recommendation="Conduct full investigator review across all elevated forensic modules.",
            priority=50,
        )
    elif not findings and elevated:
        n = elevated[0]
        findings.append({
            "id": "finding:single_detector",
            "finding": f"{n.get('label', 'Forensic Anomaly')} Detected",
            "supporting_evidence": [{
                "detector": n.get("source", ""),
                "observation": n.get("label", ""),
                "detail": n.get("detail", ""),
                "score": n.get("score", 0),
                "confidence": n.get("confidence", 0),
            }],
            "confidence": round(_f(n.get("score")) * _f(n.get("confidence"), 0.5) * 100 + 40, 1),
            "contradictory_evidence": contradictory()[:3],
            "recommendation": _default_recommendation(n.get("label", "anomaly"), 0.5),
            "priority": 40,
            "evidence_node_ids": [n["id"]],
        })

    # Overall finding from fusion when nothing else
    if not findings:
        verdict = fusion.get("verdict") or "No significant anomaly"
        findings.append({
            "id": "finding:baseline",
            "finding": str(verdict),
            "supporting_evidence": [],
            "confidence": round(_f(fusion.get("confidence", 0)), 1),
            "contradictory_evidence": [],
            "recommendation": "Routine verification sufficient unless new evidence emerges.",
            "priority": 10,
            "evidence_node_ids": [],
        })

    findings.sort(key=lambda f: (-f.get("priority", 0), -f.get("confidence", 0)))
    return findings


def _default_recommendation(finding: str, conf: float) -> str:
    if conf >= 0.85:
        return f"Treat '{finding}' as high-confidence; preserve originals and escalate to senior examiner."
    if conf >= 0.65:
        return f"'{finding}' warrants targeted verification against source records and chain-of-custody notes."
    return f"Corroborate '{finding}' with additional modules before adjudication."


def run_forensic_reasoning(
    detectors: List[DetectorOutput],
    fusion: FusionResult,
    analysis: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build evidence graph and infer forensic findings from detector outputs.
    """
    analysis = analysis or {}
    det = _det_map(detectors)
    all_nodes, edges = _extract_observations(det, analysis)

    evidence_nodes = [n for n in all_nodes if n.get("type") in ("detector", "evidence")]
    context_nodes = [n for n in all_nodes if n.get("type") == "context"]

    findings = _infer_findings(evidence_nodes, context_nodes, det, fusion, analysis)

    # Link findings to evidence nodes in graph
    for f in findings:
        fid = f["id"]
        all_nodes.append(_node(
            fid, "finding", f["finding"],
            score=f.get("confidence", 0) / 100.0,
            confidence=f.get("confidence", 0) / 100.0,
            detail=f.get("recommendation", ""),
        ))
        for eid in f.get("evidence_node_ids") or []:
            edges.append(_edge(eid, fid, "supports", weight=f.get("confidence", 0) / 100.0))

    primary = findings[0] if findings else {}
    narrative = build_reasoning_narrative({
        "findings": findings,
        "graph": {"nodes": all_nodes, "edges": edges},
        "primary_finding": primary,
        "fusion": fusion,
    })

    return {
        "version": 1,
        "primary_finding": primary.get("finding", ""),
        "primary_confidence": primary.get("confidence", 0),
        "findings": findings,
        "graph": {
            "nodes": all_nodes,
            "edges": edges,
            "node_count": len(all_nodes),
            "edge_count": len(edges),
        },
        "narrative": narrative,
        "recommendation": primary.get("recommendation", ""),
        "inference_chain": _build_inference_chain(primary, evidence_nodes),
    }


def _build_inference_chain(
    finding: Dict[str, Any],
    evidence_nodes: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """Human-readable inference chain for reports (detector → observation → finding)."""
    chain: List[Dict[str, str]] = []
    support = finding.get("supporting_evidence") or []
    for s in support:
        det = s.get("detector", "").replace("_", " ").title()
        obs = s.get("observation", "")
        chain.append({"step": det, "observation": obs, "arrow": "->"})
    if finding.get("finding"):
        chain.append({
            "step": "Inference",
            "observation": finding["finding"],
            "arrow": "",
        })
    return chain


def build_reasoning_narrative(reasoning: Dict[str, Any]) -> str:
    """Investigator-facing narrative derived from reasoning output (not raw detectors)."""
    findings = reasoning.get("findings") or []
    primary = reasoning.get("primary_finding") or (findings[0].get("finding") if findings else "")
    conf = reasoning.get("primary_confidence") or (findings[0].get("confidence") if findings else 0)

    lines = ["Forensic Reasoning Report", ""]
    if primary:
        lines.append(f"Primary Finding: {primary}")
        lines.append(f"Confidence: {conf}%")
    lines.append("")

    chain = reasoning.get("inference_chain") or []
    if chain:
        lines.append("Inference Chain")
        for step in chain:
            if step.get("arrow"):
                lines.append(f"  {step['step']}")
                lines.append(f"  {step['arrow']}")
                lines.append(f"  {step['observation']}")
            else:
                lines.append(f"  {step['step']}: {step['observation']}")
        lines.append("")

    for i, f in enumerate(findings[:5], 1):
        lines.append(f"Finding {i}: {f.get('finding', '—')}")
        lines.append(f"Confidence: {f.get('confidence', '—')}%")
        lines.append("Supporting Evidence")
        for s in f.get("supporting_evidence") or []:
            det = s.get("detector", "").replace("_", " ").title()
            lines.append(f"  • {det} — {s.get('observation', '')}")
            if s.get("detail"):
                lines.append(f"    {s['detail'][:240]}")
        contra = f.get("contradictory_evidence") or []
        if contra:
            lines.append("Contradictory Evidence")
            for c in contra[:4]:
                lines.append(f"  • {c.get('detector', '').replace('_', ' ').title()} — {c.get('observation', '')}")
        rec = f.get("recommendation")
        if rec:
            lines.append(f"Recommendation: {rec}")
        lines.append("")

    return "\n".join(lines).strip()


def save_forensic_reasoning(
    evidence_id: str,
    reasoning: Dict[str, Any],
    analysis_dir: Optional[Path] = None,
) -> Path:
    from backend.evidence.paths import get_analysis_dir

    adir = Path(analysis_dir) if analysis_dir else get_analysis_dir(evidence_id, create=True)
    adir.mkdir(parents=True, exist_ok=True)
    path = adir / "forensic_reasoning.json"
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(reasoning, f, indent=2, default=str)
    if path.exists():
        path.unlink(missing_ok=True)
    tmp.replace(path)
    return path
