"""
OCR consensus engine — weighted voting across engine outputs.
"""

from __future__ import annotations

import re
from collections import Counter
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

ENGINE_WEIGHTS = {
    "paddleocr": 0.30,
    "easyocr": 0.25,
    "tesseract": 0.20,
    "trocr": 0.25,
}


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _text_similarity(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, _normalize_text(a), _normalize_text(b)).ratio()


def _bbox_iou(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    x1 = max(a.get("left", 0), b.get("left", 0))
    y1 = max(a.get("top", 0), b.get("top", 0))
    x2 = min(a.get("right", 0), b.get("right", 0))
    y2 = min(a.get("bottom", 0), b.get("bottom", 0))
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = max(1, a.get("width", 1) * a.get("height", 1))
    area_b = max(1, b.get("width", 1) * b.get("height", 1))
    return inter / (area_a + area_b - inter + 1e-6)


def _cluster_detections(all_dets: List[Tuple[str, Dict[str, Any]]]) -> List[List[Tuple[str, Dict[str, Any]]]]:
    clusters: List[List[Tuple[str, Dict[str, Any]]]] = []
    used = set()
    for i, (eng_i, det_i) in enumerate(all_dets):
        if i in used:
            continue
        cluster = [(eng_i, det_i)]
        used.add(i)
        for j, (eng_j, det_j) in enumerate(all_dets):
            if j in used or eng_i == eng_j:
                continue
            if _bbox_iou(det_i, det_j) > 0.3:
                cluster.append((eng_j, det_j))
                used.add(j)
        clusters.append(cluster)
    return clusters


def _vote_text(cluster: List[Tuple[str, Dict[str, Any]]]) -> Tuple[str, float]:
    votes: Counter = Counter()
    weight_sum = 0.0
    for eng, det in cluster:
        w = ENGINE_WEIGHTS.get(eng, 0.15) * float(det.get("confidence", 0.5))
        text = str(det.get("text", "")).strip()
        if text:
            votes[text] += w
            weight_sum += w
    if not votes:
        return "", 0.0
    winner, score = votes.most_common(1)[0]
    confidence = score / weight_sum if weight_sum > 0 else 0.5
    return winner, min(1.0, confidence)


def build_consensus(multi_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fuse multi-engine OCR into a single result via voting.

    Compares character, word, and layout confidence across engines.
    """
    engine_results = multi_result.get("engine_results", {})
    succeeded = {k: v for k, v in engine_results.items() if v.get("success")}

    if not succeeded:
        return {
            "success": False,
            "full_text": "",
            "text": "",
            "detections": [],
            "engine": "consensus",
            "primary_engine": None,
            "ocr_confidence": 0.0,
            "character_confidence": 0.0,
            "word_confidence": 0.0,
            "layout_confidence": 0.0,
            "detected_language": "unknown",
            "consensus": {
                "engines_run": multi_result.get("engines_run", []),
                "engines_succeeded": [],
                "reasoning": "All OCR engines failed or timed out.",
            },
            "engine_results": engine_results,
        }

    fastest_engine = multi_result.get("fastest_engine")
    fastest_result = multi_result.get("fastest_result") or {}

    # Single engine succeeded — use fastest result directly
    if len(succeeded) == 1:
        only_name = next(iter(succeeded))
        only = succeeded[only_name]
        return _package_result(
            only, only_name, only, engine_results, multi_result,
            mismatch_regions=[], agreement=1.0,
        )

    # Pick primary engine by weighted score (+ speed tie-breaker for fastest)
    best_engine = None
    best_score = -1.0
    for name, res in succeeded.items():
        w = ENGINE_WEIGHTS.get(name, 0.15)
        score = (
            float(res.get("word_confidence", 0)) * 0.4
            + float(res.get("character_confidence", 0)) * 0.3
            + float(res.get("layout_confidence", 0)) * 0.3
        ) * w
        if score > best_score:
            best_score = score
            best_engine = name

    # Prefer fastest engine when scores are close (within 8%)
    if fastest_engine and fastest_engine in succeeded:
        fastest_res = succeeded[fastest_engine]
        fastest_score = (
            float(fastest_res.get("word_confidence", 0)) * 0.4
            + float(fastest_res.get("character_confidence", 0)) * 0.3
            + float(fastest_res.get("layout_confidence", 0)) * 0.3
        ) * ENGINE_WEIGHTS.get(fastest_engine, 0.15)
        if best_score > 0 and fastest_score >= best_score * 0.92:
            best_engine = fastest_engine

    # Cluster and vote on detections
    all_dets: List[Tuple[str, Dict[str, Any]]] = []
    for eng, res in succeeded.items():
        for det in res.get("detections", []):
            all_dets.append((eng, det))

    consensus_dets: List[Dict[str, Any]] = []
    mismatch_regions: List[Dict[str, Any]] = []

    if all_dets:
        for cluster in _cluster_detections(all_dets):
            texts = [det["text"] for _, det in cluster]
            winner_text, vote_conf = _vote_text(cluster)
            if not winner_text:
                continue
            # Use bbox from highest-confidence detection in cluster
            _, best_det = max(cluster, key=lambda x: float(x[1].get("confidence", 0)))
            merged = dict(best_det)
            merged["text"] = winner_text
            merged["confidence"] = vote_conf
            merged["engines_agreed"] = len(set(texts))
            merged["engines_total"] = len(cluster)
            consensus_dets.append(merged)

            unique_texts = set(_normalize_text(t) for t in texts if t)
            if len(unique_texts) > 1:
                mismatch_regions.append({
                    "bbox": merged.get("bbox"),
                    "texts": list(texts),
                    "winner": winner_text,
                    "disagreement": 1.0 - vote_conf,
                })
    else:
        # Full-page engines (TrOCR) — vote on full text
        texts = [res.get("full_text", "") for res in succeeded.values() if res.get("full_text")]
        if texts:
            counter = Counter(_normalize_text(t) for t in texts)
            winner_norm = counter.most_common(1)[0][0]
            for t in texts:
                if _normalize_text(t) == winner_norm:
                    consensus_dets = succeeded[best_engine].get("detections", [])
                    break

    consensus_dets.sort(key=lambda d: (d.get("top", 0), d.get("left", 0)))
    if consensus_dets:
        full_text = " ".join(d["text"] for d in consensus_dets)
    elif fastest_result.get("full_text"):
        full_text = fastest_result["full_text"]
    else:
        full_text = succeeded[best_engine].get("full_text", "")

    char_confs = [float(r.get("character_confidence", 0)) for r in succeeded.values()]
    word_confs = [float(r.get("word_confidence", 0)) for r in succeeded.values()]
    layout_confs = [float(r.get("layout_confidence", 0)) for r in succeeded.values()]

    char_conf = sum(char_confs) / len(char_confs)
    word_conf = sum(word_confs) / len(word_confs)
    layout_conf = sum(layout_confs) / len(layout_confs)

    # Agreement boost
    texts = [r.get("full_text", "") for r in succeeded.values()]
    if len(texts) >= 2:
        sims = [_text_similarity(texts[i], texts[j]) for i in range(len(texts)) for j in range(i + 1, len(texts))]
        agreement = sum(sims) / len(sims) if sims else 0.5
    else:
        agreement = 0.7

    ocr_confidence = min(1.0, (char_conf * 0.3 + word_conf * 0.4 + layout_conf * 0.3) * (0.7 + agreement * 0.3))

    langs = [r.get("detected_language", "en") for r in succeeded.values()]
    detected_language = Counter(langs).most_common(1)[0][0] if langs else "en"

    reasoning_parts = [
        f"Consensus from {len(succeeded)}/{len(engine_results)} engines.",
        f"Primary: {best_engine}.",
        f"Agreement: {agreement:.0%}.",
    ]
    if fastest_engine:
        reasoning_parts.append(f"Fastest: {fastest_engine} ({fastest_result.get('elapsed_ms', 0):.0f}ms).")
    if mismatch_regions:
        reasoning_parts.append(f"{len(mismatch_regions)} region(s) with engine disagreement.")

    return _package_result(
        {
            "full_text": full_text,
            "detections": consensus_dets,
            "character_confidence": round(char_conf, 4),
            "word_confidence": round(word_conf, 4),
            "layout_confidence": round(layout_conf, 4),
            "detected_language": detected_language,
            "ocr_confidence": round(ocr_confidence, 4),
            "word_count": len(full_text.split()),
            "mismatch_regions": mismatch_regions,
        },
        best_engine,
        succeeded[best_engine],
        engine_results,
        multi_result,
        mismatch_regions=mismatch_regions,
        agreement=agreement,
        reasoning_parts=reasoning_parts,
    )


def _package_result(
    payload: Dict[str, Any],
    primary_engine: str,
    primary: Dict[str, Any],
    engine_results: Dict[str, Any],
    multi_result: Dict[str, Any],
    *,
    mismatch_regions: List[Dict[str, Any]],
    agreement: float,
    reasoning_parts: Optional[List[str]] = None,
) -> Dict[str, Any]:
    reasoning = reasoning_parts or [
        f"Consensus from engines. Primary: {primary_engine}.",
    ]
    return {
        "success": True,
        "full_text": payload.get("full_text", primary.get("full_text", "")),
        "text": payload.get("full_text", primary.get("full_text", "")),
        "detections": payload.get("detections", primary.get("detections", [])),
        "engine": "consensus",
        "primary_engine": primary_engine,
        "ocr_confidence": payload.get("ocr_confidence", primary.get("word_confidence", 0.5)),
        "character_confidence": payload.get("character_confidence", primary.get("character_confidence", 0.5)),
        "word_confidence": payload.get("word_confidence", primary.get("word_confidence", 0.5)),
        "layout_confidence": payload.get("layout_confidence", primary.get("layout_confidence", 0.5)),
        "detected_language": payload.get("detected_language", primary.get("detected_language", "en")),
        "word_count": payload.get("word_count", len((payload.get("full_text") or "").split())),
        "mismatch_regions": payload.get("mismatch_regions", mismatch_regions),
        "consensus": {
            "engines_run": multi_result.get("engines_run", []),
            "engines_succeeded": [
                name for name, r in engine_results.items() if r.get("success")
            ],
            "fastest_engine": multi_result.get("fastest_engine"),
            "primary_engine": primary_engine,
            "agreement_score": round(agreement, 4),
            "mismatch_count": len(mismatch_regions),
            "reasoning": " ".join(reasoning),
            "engine_scores": {
                name: {
                    "word_confidence": r.get("word_confidence"),
                    "character_confidence": r.get("character_confidence"),
                    "layout_confidence": r.get("layout_confidence"),
                    "elapsed_ms": r.get("elapsed_ms"),
                }
                for name, r in engine_results.items()
                if r.get("success")
            },
        },
        "engine_results": engine_results,
    }
