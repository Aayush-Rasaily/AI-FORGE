"""Human-readable reports, evidence chains, and confidence graphs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _severity(score: float) -> str:
    if score >= 0.7:
        return "critical"
    if score >= 0.45:
        return "high"
    if score >= 0.25:
        return "medium"
    return "low"


def build_evidence_chain(
    verdict: str,
    risk_score: float,
    signals: Dict[str, Any],
    evidence: List[Dict[str, Any]],
    explainers: Dict[str, Dict[str, Any]],
    suspicious_regions: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Build ordered evidence chain — every step explains WHY."""
    chain: List[Dict[str, Any]] = []
    step = 1

    chain.append({
        "step": step,
        "stage": "verdict",
        "module": "ensemble",
        "prediction": verdict,
        "score": round(risk_score / 100.0, 4),
        "confidence": round(float(signals.get("tampering_confidence", 0.75)), 4),
        "why": (
            f"Weighted ensemble produced {verdict} with {risk_score:.1f}% risk "
            f"after fusing {len(evidence)} forensic modules."
        ),
    })
    step += 1

    for ev in evidence:
        score = float(ev.get("score", 0))
        if score < 0.15:
            continue
        mod = ev.get("module", "unknown")
        chain.append({
            "step": step,
            "stage": "module",
            "module": mod,
            "prediction": f"{mod} anomaly",
            "score": round(score, 4),
            "confidence": round(float(ev.get("confidence", 0.7)), 4),
            "severity": ev.get("severity", _severity(score)),
            "why": ev.get("reason") or f"{mod} contributed {score:.0%} to the risk score.",
            "location": ev.get("location"),
        })
        step += 1

    for name, result in explainers.items():
        if not result or result.get("error"):
            continue
        chain.append({
            "step": step,
            "stage": "explainer",
            "module": name,
            "prediction": f"{name} saliency",
            "score": round(float(result.get("score", 0)), 4),
            "confidence": round(float(result.get("confidence", 0.6)), 4),
            "why": result.get("why", f"{name} highlighted regions influencing the prediction."),
            "artifacts": {
                k: result.get(k)
                for k in ("heatmap", "overlay")
                if result.get(k)
            },
        })
        step += 1

    for i, region in enumerate(suspicious_regions[:5]):
        chain.append({
            "step": step,
            "stage": "region",
            "module": "fused_overlay",
            "prediction": f"Suspicious region R{i + 1}",
            "score": round(float(region.get("confidence", 0)), 4),
            "confidence": round(float(region.get("confidence", 0)), 4),
            "bbox": region.get("bbox"),
            "why": (
                f"Region R{i + 1} at {region.get('bbox')} scored {region.get('confidence', 0):.0%} "
                "across GradCAM, SHAP, LIME, and attention fusion."
            ),
        })
        step += 1

    return chain


def build_confidence_graph(
    evidence: List[Dict[str, Any]],
    explainers: Dict[str, Dict[str, Any]],
    signals: Dict[str, Any],
) -> Dict[str, Any]:
    """Nodes and edges for confidence visualization."""
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    nodes.append({
        "id": "ensemble",
        "label": "Ensemble Verdict",
        "score": round(float(signals.get("tampering_score", signals.get("ela_score", 0))), 4),
        "confidence": 0.85,
        "type": "root",
    })

    for ev in evidence:
        score = float(ev.get("score", 0))
        if score < 0.1:
            continue
        mod_id = str(ev.get("module", "mod")).lower().replace(" ", "_")
        nodes.append({
            "id": mod_id,
            "label": ev.get("module", mod_id),
            "score": round(score, 4),
            "confidence": round(float(ev.get("confidence", 0.7)), 4),
            "type": "module",
            "why": ev.get("reason", ""),
        })
        edges.append({
            "source": mod_id,
            "target": "ensemble",
            "weight": round(score * float(ev.get("confidence", 0.7)), 4),
        })

    for name, result in explainers.items():
        if not result:
            continue
        nodes.append({
            "id": name,
            "label": name.upper(),
            "score": round(float(result.get("score", 0)), 4),
            "confidence": round(float(result.get("confidence", 0.6)), 4),
            "type": "explainer",
            "why": result.get("why", ""),
        })
        edges.append({
            "source": name,
            "target": "ensemble",
            "weight": round(float(result.get("score", 0)) * float(result.get("confidence", 0.6)), 4),
        })

    return {"nodes": nodes, "edges": edges}


def generate_human_report(
    verdict: str,
    risk_score: float,
    confidence: float,
    evidence_chain: List[Dict[str, Any]],
    suspicious_regions: List[Dict[str, Any]],
    signals: Dict[str, Any],
) -> str:
    """Plain-language forensic report."""
    lines = [
        f"FORENSIC ANALYSIS REPORT",
        f"Verdict: {verdict}",
        f"Risk Score: {risk_score:.1f}% | Confidence: {confidence:.1f}%",
        "",
        "SUMMARY",
    ]

    high_steps = [s for s in evidence_chain if float(s.get("score", 0)) >= 0.45]
    if high_steps:
        lines.append(
            f"The analysis flagged {len(high_steps)} significant signal(s). "
            f"Primary concern: {high_steps[0].get('why', 'see evidence chain')}."
        )
    else:
        lines.append("No strong manipulation signals were detected across forensic modules.")

    if suspicious_regions:
        lines.append(
            f"\nSUSPICIOUS REGIONS: {len(suspicious_regions)} area(s) highlighted by "
            "GradCAM, SHAP, LIME, and attention fusion."
        )
        for i, r in enumerate(suspicious_regions[:3]):
            lines.append(f"  • Region {i + 1}: bbox {r.get('bbox')} — {r.get('confidence', 0):.0%} confidence")

    lines.append("\nKEY FINDINGS")
    for step in evidence_chain[:8]:
        if step.get("stage") in ("module", "explainer", "region"):
            lines.append(f"  [{step.get('module')}] {step.get('why', '')}")

    # Metadata / GAN / face callouts
    if signals.get("metadata_suspicious"):
        lines.append(f"\n  • Metadata: editing software or stripped EXIF — {signals.get('software', 'unknown')}.")
    if float(signals.get("gan_ai_score", 0)) >= 0.4:
        lines.append(f"  • GAN detection: AI-generated probability {float(signals.get('gan_ai_score', 0)):.0%}.")
    if float(signals.get("deepfake_probability", 0)) >= 0.35:
        lines.append(f"  • Face forensics: deepfake probability {float(signals.get('deepfake_probability', 0)):.0%}.")

    return "\n".join(lines)


def generate_ai_explanation(
    verdict: str,
    risk_score: float,
    evidence_chain: List[Dict[str, Any]],
    explainers: Dict[str, Dict[str, Any]],
) -> str:
    """Structured AI explanation with causal reasoning."""
    parts = [
        f"The system predicts **{verdict}** ({risk_score:.0f}% risk) because:"
    ]

    module_steps = [s for s in evidence_chain if s.get("stage") == "module" and float(s.get("score", 0)) >= 0.3]
    for step in module_steps[:4]:
        parts.append(
            f"- **{step['module']}** (score {float(step['score']):.0%}, "
            f"confidence {float(step.get('confidence', 0)):.0%}): {step.get('why', '')}"
        )

    explainer_steps = [s for s in evidence_chain if s.get("stage") == "explainer"]
    if explainer_steps:
        parts.append("\nSpatial explainability confirms:")
        for step in explainer_steps:
            parts.append(f"- **{step['module'].upper()}**: {step.get('why', '')}")

    region_steps = [s for s in evidence_chain if s.get("stage") == "region"]
    if region_steps:
        parts.append(
            f"\n{len(region_steps)} suspicious region(s) overlap across explainability methods, "
            "indicating localized manipulation rather than global recompression."
        )

    if len(parts) == 1:
        parts.append("- Forensic modules show consistent, low-risk signals with no dominant anomaly driver.")

    return "\n".join(parts)


def generate_explainability_report(
    context: Dict[str, Any],
    gradcam: Dict[str, Any],
    attention: Dict[str, Any],
    shap: Dict[str, Any],
    lime: Dict[str, Any],
    overlay: Dict[str, Any],
) -> Dict[str, Any]:
    """Full explainability report package."""
    verdict = context.get("verdict", "UNKNOWN")
    risk_score = float(context.get("risk_score", 0))
    confidence = float(context.get("confidence", 75))
    signals = context.get("signals", {})
    evidence = context.get("evidence", [])

    explainers = {
        "gradcam": gradcam,
        "attention": attention,
        "shap": shap,
        "lime": lime,
    }
    suspicious_regions = overlay.get("suspicious_regions", [])

    evidence_chain = build_evidence_chain(
        verdict, risk_score, signals, evidence, explainers, suspicious_regions,
    )
    confidence_graph = build_confidence_graph(evidence, explainers, signals)
    human_report = generate_human_report(
        verdict, risk_score, confidence, evidence_chain, suspicious_regions, signals,
    )
    ai_explanation = generate_ai_explanation(verdict, risk_score, evidence_chain, explainers)

    predictions = []
    for step in evidence_chain:
        predictions.append({
            "prediction": step.get("prediction"),
            "module": step.get("module"),
            "score": step.get("score"),
            "confidence": step.get("confidence"),
            "why": step.get("why"),
            "severity": step.get("severity"),
            "bbox": step.get("bbox"),
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "human_readable_report": human_report,
        "ai_explanation": ai_explanation,
        "evidence_chain": evidence_chain,
        "confidence_graph": confidence_graph,
        "predictions": predictions,
        "suspicious_regions": suspicious_regions,
        "overlay": overlay,
        "methods": explainers,
    }
