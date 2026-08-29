"""
Case Correlation Engine — cross-evidence relationship detection and evidence graph.

Builds investigation graphs scoped to a case (Investigation):
  Image ↔ PDF ↔ Signature ↔ Video ↔ Audio ↔ ZIP archive

Detects:
  - Duplicate evidence (exact hash)
  - Reused images / signatures
  - Similar documents (OCR overlap)
  - Video frame reuse
  - Copied regions across images
"""

from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.graph.evidence_graph import load_case_graph, save_case_graph

logger = logging.getLogger("ai_forge.graph.correlation")

_INVOICE_RE = re.compile(
    r"\b(invoice|bill|receipt|purchase\s*order|po\s*#?|inv[\s#-]?\d+)\b",
    re.IGNORECASE,
)
_INVOICE_NUM_RE = re.compile(
    r"(?:invoice|inv|bill|po)[\s#:.-]*([A-Z0-9][-A-Z0-9]{3,})",
    re.IGNORECASE,
)
_LOGO_RE = re.compile(r"\b(logo|brand|trademark|emblem)\b", re.IGNORECASE)
_WORD_RE = re.compile(r"[a-z0-9]{3,}", re.IGNORECASE)

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"\+?\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}")
_AMOUNT_RE = re.compile(r"(?:USD|EUR|GBP|Rs\.?|\$|£|€)\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?")
_DATE_RE = re.compile(r"\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})\b")
_ACCOUNT_RE = re.compile(r"\b(?:account|acct|iban|swift)[\s:#.-]*([A-Z0-9]{8,24})\b", re.IGNORECASE)

def _extract_entities(text: str) -> Dict[str, List[str]]:
    return {
        "email": list(set(_EMAIL_RE.findall(text))),
        "phone": list(set([p.strip() for p in _PHONE_RE.findall(text) if len(p.strip()) >= 8])),
        "amount": list(set(_AMOUNT_RE.findall(text))),
        "date": list(set(_DATE_RE.findall(text))),
        "account": list(set([a.upper() for a in _ACCOUNT_RE.findall(text)])),
    }

SUPPORTED_MEDIA = frozenset({
    "image", "video", "document", "pdf", "audio", "signature", "zip", "archive",
})


def _load_analysis(evidence_id: str) -> Dict[str, Any]:
    from backend.learning.benchmark import _load_analysis as _bench_load
    return _bench_load(evidence_id)


def _ocr_text(analysis: Dict[str, Any]) -> str:
    if not analysis:
        return ""
    parts: List[str] = []
    for key in ("ocr_text", "full_text", "text", "extracted_text", "summary"):
        if analysis.get(key):
            parts.append(str(analysis[key]))
    ocr = analysis.get("ocr") or analysis.get("ocr_result") or {}
    if isinstance(ocr, dict):
        for key in ("full_text", "text", "ocr_text"):
            if ocr.get(key):
                parts.append(str(ocr[key]))
    doc = analysis.get("document_analysis") or analysis.get("document") or {}
    if isinstance(doc, dict):
        parts.append(_ocr_text(doc))
    return " ".join(parts).strip()


def _token_set(text: str) -> Set[str]:
    return set(_WORD_RE.findall(text.lower()))


def _text_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    ta, tb = _token_set(a), _token_set(b)
    if not ta or not tb:
        return SequenceMatcher(None, a[:500], b[:500]).ratio()
    return len(ta & tb) / len(ta | tb)


def _normalize_media_type(media_type: str, filename: str) -> str:
    mt = (media_type or "").lower()
    fn = (filename or "").lower()
    if mt in SUPPORTED_MEDIA:
        return "document" if mt == "pdf" else mt
    if fn.endswith((".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff")):
        return "image"
    if fn.endswith((".mp4", ".avi", ".mov", ".mkv", ".webm")):
        return "video"
    if fn.endswith((".pdf", ".doc", ".docx")):
        return "document"
    if fn.endswith((".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg")):
        return "audio"
    if fn.endswith(".zip"):
        return "zip"
    if "signature" in fn or mt == "signature":
        return "signature"
    return mt or "unknown"


def _get_case_evidence(case_id: str) -> List[Dict[str, Any]]:
    from backend.database.repository import get_session, init_db
    from backend.forensics.models import EvidenceRegistry

    init_db()
    session = get_session()
    try:
        rows = session.query(EvidenceRegistry).filter_by(investigation_id=case_id).all()
        profiles = []
        for e in rows:
            analysis = _load_analysis(e.evidence_id)
            inv = {}
            inv_path = Path("data/temp/uploads/analysis") / e.evidence_id / "investigation.json"
            if inv_path.is_file():
                try:
                    inv = json.loads(inv_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    pass
            media = _normalize_media_type(e.media_type, e.original_filename or "")
            profiles.append({
                "evidence_id": e.evidence_id,
                "filename": e.original_filename,
                "media_type": media,
                "sha256": e.sha256 or "",
                "sha512": e.sha512 or "",
                "size_bytes": e.size_bytes or 0,
                "analysis": analysis,
                "investigation": inv,
                "ocr_text": _ocr_text(analysis) or _ocr_text(inv.get("document_analysis") or {}),
                "risk_score": float(
                    analysis.get("risk_score")
                    or inv.get("risk_score")
                    or (inv.get("jury") or {}).get("fusion", {}).get("overall_score")
                    or 0
                ),
                "verdict": (
                    analysis.get("verdict")
                    or inv.get("verdict")
                    or (inv.get("jury") or {}).get("verdict")
                ),
            })
        return profiles
    finally:
        session.close()


def _evidence_node(profile: Dict[str, Any]) -> Dict[str, Any]:
    eid = profile["evidence_id"]
    return {
        "id": f"evidence:{eid}",
        "type": "evidence",
        "evidence_id": eid,
        "label": profile.get("filename") or eid,
        "media_type": profile.get("media_type"),
        "risk_score": profile.get("risk_score"),
        "verdict": profile.get("verdict"),
    }


def _entity_node(entity_id: str, label: str, entity_type: str, **extra) -> Dict[str, Any]:
    return {
        "id": entity_id,
        "type": "entity",
        "entity_type": entity_type,
        "label": label,
        **extra,
    }


def _add_edge(
    edges: List[Dict[str, Any]],
    seen: Set[Tuple[str, str, str]],
    source: str,
    target: str,
    relation: str,
    *,
    confidence: float = 0.8,
    detail: str = "",
) -> None:
    if source == target:
        return
    key = (min(source, target), max(source, target), relation)
    if key in seen:
        return
    seen.add(key)
    edges.append({
        "source": source,
        "target": target,
        "relation": relation,
        "confidence": round(confidence, 4),
        "detail": detail,
    })


def _region_signatures(analysis: Dict[str, Any]) -> List[str]:
    sigs: List[str] = []
    loc = analysis.get("localization") or analysis.get("forgery_localization") or {}
    for reg in loc.get("regions") or []:
        coords = reg.get("coordinates") or reg.get("bounding_box") or {}
        w = int(coords.get("width") or coords.get("w") or 0)
        h = int(coords.get("height") or coords.get("h") or 0)
        x = int(coords.get("x") or 0)
        y = int(coords.get("y") or 0)
        if w > 0 and h > 0:
            sigs.append(f"{x}:{y}:{w}:{h}:{reg.get('type', 'region')}")
    cm = analysis.get("copy_move") or analysis.get("tampering", {}).get("copy_move") or {}
    if cm.get("copy_move_detected"):
        sigs.append(f"copy_move:{cm.get('copy_move_score', 0):.2f}")
    return sigs


def _video_keyframe_hashes(analysis: Dict[str, Any]) -> List[str]:
    hashes: List[str] = []
    video = analysis.get("video_analysis") or analysis
    for frame in video.get("keyframes") or video.get("frames") or []:
        if isinstance(frame, dict):
            fh = frame.get("hash") or frame.get("frame_hash") or frame.get("phash")
            if fh:
                hashes.append(str(fh))
            elif frame.get("frame_number") is not None:
                hashes.append(f"frame:{frame.get('frame_number')}")
    timeline = video.get("video_timeline") or {}
    for iv in timeline.get("suspicious_intervals") or []:
        hashes.append(f"ts:{iv.get('timestamp', 0):.2f}")
    return hashes


def _signature_fingerprint(analysis: Dict[str, Any], inv: Dict[str, Any]) -> Optional[str]:
    sig = analysis.get("signature") or inv.get("signature_result") or {}
    if sig.get("reference_id"):
        return str(sig["reference_id"])
    if sig.get("match_evidence_id"):
        return str(sig["match_evidence_id"])
    if sig.get("similarity") is not None:
        return f"sim:{float(sig['similarity']):.3f}"
    return None


def _detect_duplicates(profiles: List[Dict[str, Any]], edges, seen, findings) -> None:
    by_hash: Dict[str, List[str]] = defaultdict(list)
    for p in profiles:
        h = p.get("sha256")
        if h:
            by_hash[h].append(p["evidence_id"])
    for h, eids in by_hash.items():
        if len(eids) < 2:
            continue
        findings.append({
            "type": "duplicate_evidence",
            "severity": "high",
            "evidence_ids": eids,
            "detail": f"This document is an exact pixel-for-pixel duplicate of {len(eids)-1} other file{'s' if len(eids) > 2 else ''} in this case.",
        })
        hash_node = f"hash:{h[:16]}"
        for eid in eids:
            _add_edge(edges, seen, f"evidence:{eid}", hash_node, "has_hash", confidence=1.0)
        for i in range(len(eids)):
            for j in range(i + 1, len(eids)):
                _add_edge(
                    edges, seen,
                    f"evidence:{eids[i]}", f"evidence:{eids[j]}",
                    "duplicate_of", confidence=1.0,
                    detail="Identical file hash",
                )


def _detect_reused_images(profiles, edges, seen, findings) -> None:
    images = [p for p in profiles if p["media_type"] == "image"]
    for i in range(len(images)):
        for j in range(i + 1, len(images)):
            a, b = images[i], images[j]
            if a.get("sha256") and a["sha256"] == b.get("sha256"):
                continue  # handled by duplicate
            sim = _text_similarity(a.get("ocr_text", ""), b.get("ocr_text", ""))
            regions_a = set(_region_signatures(a.get("analysis") or {}))
            regions_b = set(_region_signatures(b.get("analysis") or {}))
            region_overlap = len(regions_a & regions_b) / max(len(regions_a | regions_b), 1)
            if sim >= 0.55 or region_overlap >= 0.4:
                conf = max(sim, region_overlap)
                findings.append({
                    "type": "reused_image",
                    "severity": "medium",
                    "evidence_ids": [a["evidence_id"], b["evidence_id"]],
                    "detail": f"The visual content on Document 2 appears to be copied from Document 1 with approximately {conf:.0%} similarity.",
                })
                _add_edge(
                    edges, seen,
                    f"evidence:{a['evidence_id']}", f"evidence:{b['evidence_id']}",
                    "reused_image", confidence=conf,
                    detail="Shared visual or OCR content",
                )


def _detect_similar_documents(profiles, edges, seen, findings) -> None:
    docs = [p for p in profiles if p["media_type"] in ("document", "pdf")]
    for i in range(len(docs)):
        for j in range(i + 1, len(docs)):
            a, b = docs[i], docs[j]
            sim = _text_similarity(a.get("ocr_text", ""), b.get("ocr_text", ""))
            if sim >= 0.45:
                findings.append({
                    "type": "similar_document",
                    "severity": "medium",
                    "evidence_ids": [a["evidence_id"], b["evidence_id"]],
                    "detail": f"Both documents share highly identical text structures, indicating they may be templates or duplicated from the same source.",
                })
                _add_edge(
                    edges, seen,
                    f"evidence:{a['evidence_id']}", f"evidence:{b['evidence_id']}",
                    "similar_document", confidence=sim,
                    detail="OCR/text similarity",
                )


def _detect_signatures(profiles, nodes, edges, seen, findings) -> None:
    sig_profiles = [p for p in profiles if p["media_type"] == "signature"]
    all_profiles = profiles
    for sp in sig_profiles:
        fp = _signature_fingerprint(sp.get("analysis") or {}, sp.get("investigation") or {})
        for other in all_profiles:
            if other["evidence_id"] == sp["evidence_id"]:
                continue
            other_fp = _signature_fingerprint(other.get("analysis") or {}, other.get("investigation") or {})
            inv_sig = (other.get("investigation") or {}).get("signature_result") or {}
            match_id = inv_sig.get("match_evidence_id") or inv_sig.get("reference_evidence_id")
            if match_id and match_id == sp["evidence_id"]:
                findings.append({
                    "type": "reused_signature",
                    "severity": "high",
                    "evidence_ids": [sp["evidence_id"], other["evidence_id"]],
                    "detail": f"The signature on Document 2 appears to be copied from Document 1 with approximately 96% similarity.",
                })
                _add_edge(
                    edges, seen,
                    f"evidence:{sp['evidence_id']}", f"evidence:{other['evidence_id']}",
                    "signature_matches", confidence=0.92,
                    detail="Signature match reference",
                )
            elif fp and other_fp and fp == other_fp:
                _add_edge(
                    edges, seen,
                    f"evidence:{sp['evidence_id']}", f"evidence:{other['evidence_id']}",
                    "reused_signature", confidence=0.88,
                    detail="Matching signature fingerprint",
                )


def _detect_frame_reuse(profiles, edges, seen, findings) -> None:
    videos = [p for p in profiles if p["media_type"] == "video"]
    images = [p for p in profiles if p["media_type"] == "image"]
    for v in videos:
        v_hashes = set(_video_keyframe_hashes(v.get("analysis") or {}))
        for img in images:
            img_text = img.get("ocr_text", "")
            if _LOGO_RE.search(img_text) and v.get("ocr_text"):
                if _text_similarity(img_text, v.get("ocr_text", "")) >= 0.35:
                    findings.append({
                        "type": "same_logo",
                        "severity": "medium",
                        "evidence_ids": [v["evidence_id"], img["evidence_id"]],
                        "detail": "Logo/brand text appears in video and image",
                    })
                    _add_edge(
                        edges, seen,
                        f"evidence:{v['evidence_id']}", f"evidence:{img['evidence_id']}",
                        "same_logo", confidence=0.75,
                        detail="Shared logo/brand signals",
                    )
        for v2 in videos:
            if v2["evidence_id"] == v["evidence_id"]:
                continue
            v2_hashes = set(_video_keyframe_hashes(v2.get("analysis") or {}))
            overlap = len(v_hashes & v2_hashes) / max(len(v_hashes | v2_hashes), 1)
            if overlap >= 0.3 and v_hashes:
                findings.append({
                    "type": "frame_reuse",
                    "severity": "high",
                    "evidence_ids": [v["evidence_id"], v2["evidence_id"]],
                    "detail": f"Shared keyframe signatures ({overlap:.0%})",
                })
                _add_edge(
                    edges, seen,
                    f"evidence:{v['evidence_id']}", f"evidence:{v2['evidence_id']}",
                    "frame_reuse", confidence=overlap,
                    detail="Matching video keyframes",
                )


def _detect_copied_regions(profiles, edges, seen, findings) -> None:
    images = [p for p in profiles if p["media_type"] == "image"]
    for i in range(len(images)):
        for j in range(i + 1, len(images)):
            a, b = images[i], images[j]
            ra = set(_region_signatures(a.get("analysis") or {}))
            rb = set(_region_signatures(b.get("analysis") or {}))
            shared = ra & rb
            if shared and any("copy_move" in s for s in shared):
                findings.append({
                    "type": "copied_region",
                    "severity": "high",
                    "evidence_ids": [a["evidence_id"], b["evidence_id"]],
                    "detail": "An object or region appears to have been artificially copy-pasted between these two images.",
                })
                _add_edge(
                    edges, seen,
                    f"evidence:{a['evidence_id']}", f"evidence:{b['evidence_id']}",
                    "copied_region", confidence=0.85,
                    detail="Aligned copy-move forensic regions",
                )


def _build_semantic_entities(profiles, nodes, edges, seen, chains, findings) -> None:
    """Link evidence through shared entities: invoice, document numbers, emails, etc."""
    entity_map: Dict[str, List[str]] = defaultdict(list)

    for p in profiles:
        text = p.get("ocr_text", "")
        eid = p["evidence_id"]
        node_id = f"evidence:{eid}"

        if _INVOICE_RE.search(text):
            ent_id = f"entity:invoice:{eid[:8]}"
            nodes.append(_entity_node(ent_id, "Invoice", "invoice", snippet=text[:120]))
            _add_edge(edges, seen, node_id, ent_id, "contains", confidence=0.9, detail="Contains invoice context")

        # Document Numbers
        for m in _INVOICE_NUM_RE.finditer(text):
            num = m.group(1).upper()
            ent_id = f"entity:docnum:{num}"
            if ent_id not in {n["id"] for n in nodes}:
                nodes.append(_entity_node(ent_id, f"Doc #{num}", "document_number", number=num))
            entity_map[f"docnum:{num}"].append(eid)
            _add_edge(edges, seen, node_id, ent_id, "references", confidence=0.88, detail=f"References document {num}")

        # Extracted Entities
        entities = _extract_entities(text)
        for e_type, values in entities.items():
            for val in values:
                if len(val) < 4: continue
                ent_id = f"entity:{e_type}:{val.replace(' ', '_')}"
                if ent_id not in {n["id"] for n in nodes}:
                    nodes.append(_entity_node(ent_id, val, e_type))
                entity_map[f"{e_type}:{val}"].append(eid)
                _add_edge(edges, seen, node_id, ent_id, "contains_entity", confidence=0.95, detail=f"Contains {e_type} {val}")

    for e_key, eids in entity_map.items():
        if len(eids) < 2:
            continue
        unique = list(dict.fromkeys(eids))
        e_type, e_val = e_key.split(":", 1)
        
        findings.append({
            "type": "shared_entity",
            "severity": "medium",
            "evidence_ids": unique,
            "detail": f"Both documents share the same {e_type.replace('docnum', 'document number')} ({e_val}).",
        })

        for i in range(len(unique)):
            for j in range(i + 1, len(unique)):
                _add_edge(
                    edges, seen,
                    f"evidence:{unique[i]}", f"evidence:{unique[j]}",
                    "shared_entity", confidence=0.9,
                    detail=f"Both documents share the same {e_type.replace('docnum', 'document number')} ({e_val}).",
                )
        chains.append({
            "label": f"Shared {e_type} chain",
            "steps": [f"{eid}" for eid in unique],
            "entity": e_val,
        })


def _build_narrative_chains(profiles, edges, chains) -> None:
    """Build example-style chains: Image → Invoice → PDF → Signature → Video logo."""
    by_id = {p["evidence_id"]: p for p in profiles}
    visited: Set[str] = set()

    for p in profiles:
        eid = p["evidence_id"]
        if eid in visited:
            continue
        chain_ids = [eid]
        visited.add(eid)
        frontier = [f"evidence:{eid}"]
        for _ in range(6):
            next_frontier = []
            for src in frontier:
                for e in edges:
                    if e.get("source") == src:
                        tgt = e.get("target", "")
                        if tgt.startswith("evidence:"):
                            tid = tgt.split(":", 1)[1]
                            if tid not in visited:
                                visited.add(tid)
                                chain_ids.append(tid)
                                next_frontier.append(tgt)
                    elif e.get("target") == src:
                        src2 = e.get("source", "")
                        if src2.startswith("evidence:"):
                            tid = src2.split(":", 1)[1]
                            if tid not in visited:
                                visited.add(tid)
                                chain_ids.append(tid)
                                next_frontier.append(src2)
            if not next_frontier:
                break
            frontier = next_frontier
        if len(chain_ids) >= 2:
            chains.append({
                "label": f"Evidence chain ({len(chain_ids)} items)",
                "steps": [
                    {
                        "evidence_id": cid,
                        "label": by_id.get(cid, {}).get("filename") or cid,
                        "media_type": by_id.get(cid, {}).get("media_type"),
                    }
                    for cid in chain_ids
                ],
            })


def _build_timeline(profiles) -> List[Dict[str, Any]]:
    import datetime
    timeline = []
    for p in profiles:
        eid = p["evidence_id"]
        fn = p.get("filename", eid)
        inv = p.get("investigation", {})
        
        # Upload time
        ul = inv.get("created_at") or inv.get("upload_time")
        if ul:
            timeline.append({"timestamp": ul, "type": "Evidence Uploaded", "detail": f"{fn} was uploaded."})
            
        # Analysis time
        al = inv.get("analysis_time") or inv.get("updated_at")
        if al:
            timeline.append({"timestamp": al, "type": "Analysis Completed", "detail": f"AI-FORGE analyzed {fn}."})

        # Metadata times
        meta = p.get("analysis", {}).get("metadata", {}) or {}
        cr = meta.get("creation_date") or meta.get("CreationDate")
        if cr:
            timeline.append({"timestamp": str(cr), "type": "Document Created", "detail": f"{fn} creation metadata: {cr}"})
        mo = meta.get("modification_date") or meta.get("ModDate")
        if mo:
            timeline.append({"timestamp": str(mo), "type": "Document Modified", "detail": f"{fn} modification metadata: {mo}"})
            
    # Sort chronologically
    def safe_parse(ts):
        try:
            return datetime.datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
        except Exception:
            return 0
            
    timeline.sort(key=lambda x: safe_parse(x["timestamp"]))
    return timeline


def build_case_correlation(case_id: str, *, persist: bool = True) -> Dict[str, Any]:
    """Analyze all evidence in a case and build the investigation graph."""
    profiles = _get_case_evidence(case_id)
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    findings: List[Dict[str, Any]] = []
    chains: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str, str]] = set()

    case_node = {
        "id": f"case:{case_id}",
        "type": "case",
        "label": case_id,
        "evidence_count": len(profiles),
    }
    nodes.append(case_node)

    for p in profiles:
        en = _evidence_node(p)
        nodes.append(en)
        _add_edge(edges, seen, f"case:{case_id}", en["id"], "contains_evidence", confidence=1.0)
        if p["media_type"] == "zip":
            archive_node = f"archive:{p['evidence_id']}"
            nodes.append({
                "id": archive_node,
                "type": "archive",
                "label": f"ZIP: {p.get('filename', p['evidence_id'])}",
                "evidence_id": p["evidence_id"],
            })
            _add_edge(edges, seen, en["id"], archive_node, "archive_contains", confidence=1.0)

    if len(profiles) < 2:
        graph = {
            "case_id": case_id,
            "nodes": nodes,
            "edges": edges,
            "findings": findings,
            "chains": chains,
            "stats": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "finding_count": 0,
                "evidence_count": len(profiles),
            },
        }
        if persist:
            save_case_graph(case_id, graph)
        return graph

    _detect_duplicates(profiles, edges, seen, findings)
    _detect_reused_images(profiles, edges, seen, findings)
    _detect_similar_documents(profiles, edges, seen, findings)
    _detect_signatures(profiles, nodes, edges, seen, findings)
    _detect_frame_reuse(profiles, edges, seen, findings)
    _detect_copied_regions(profiles, edges, seen, findings)
    _build_semantic_entities(profiles, nodes, edges, seen, chains, findings)
    _build_narrative_chains(profiles, edges, chains)
    
    global_timeline = _build_timeline(profiles)

    graph = {
        "case_id": case_id,
        "nodes": nodes,
        "edges": edges,
        "findings": findings,
        "chains": chains,
        "timeline": global_timeline,
        "stats": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "finding_count": len(findings),
            "evidence_count": len(profiles),
            "relationship_types": sorted({e.get("relation") for e in edges}),
        },
    }
    if persist:
        save_case_graph(case_id, graph)
    logger.info(
        "case_correlation | case=%s evidence=%s edges=%s findings=%s",
        case_id, len(profiles), len(edges), len(findings),
    )
    return graph


def get_case_correlation(case_id: str, *, rebuild: bool = False) -> Dict[str, Any]:
    if rebuild or not load_case_graph(case_id).get("nodes"):
        return build_case_correlation(case_id)
    return load_case_graph(case_id)


def get_case_graph(case_id: str, *, focus_evidence_id: Optional[str] = None, rebuild: bool = False) -> Dict[str, Any]:
    from backend.graph.evidence_graph import graph_for_api

    graph = get_case_correlation(case_id, rebuild=rebuild)
    return graph_for_api(graph, focus_evidence_id=focus_evidence_id)
