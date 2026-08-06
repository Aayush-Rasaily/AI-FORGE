"""
Professional PDF report export — resilient ReportLab pipeline.

Never crash on missing images, fonts, or Unicode. Full template embeds
forensic visuals when available; otherwise continues with placeholders.
"""

from __future__ import annotations

import logging
import re
import tempfile
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from backend.reports.charts import generate_all_charts

logger = logging.getLogger("ai_forge.reports.pdf")

BRAND_COLOR = colors.HexColor("#1e40af")
ACCENT = colors.HexColor("#0ea5e9")
MUTED = colors.HexColor("#6b7280")

# Built-in fonts only — never depend on custom TTF files
FONT_REG = "Helvetica"
FONT_BOLD = "Helvetica-Bold"

_SAFE_IMG_DIR = Path("data/temp/report_images")


def _styles():
    base = getSampleStyleSheet()
    # Avoid duplicate style registration across calls
    names = set(base.byName.keys())
    if "BrandTitle" not in names:
        base.add(ParagraphStyle(
            "BrandTitle",
            parent=base["Title"],
            fontName=FONT_BOLD,
            fontSize=22,
            textColor=BRAND_COLOR,
            spaceAfter=6,
        ))
    if "SectionHead" not in names:
        base.add(ParagraphStyle(
            "SectionHead",
            parent=base["Heading2"],
            fontName=FONT_BOLD,
            fontSize=14,
            textColor=BRAND_COLOR,
            spaceBefore=16,
            spaceAfter=8,
        ))
    if "BodyJustify" not in names:
        base.add(ParagraphStyle(
            "BodyJustify",
            parent=base["BodyText"],
            fontName=FONT_REG,
            alignment=TA_JUSTIFY,
            fontSize=10,
            leading=14,
        ))
    if "Footer" not in names:
        base.add(ParagraphStyle(
            "Footer",
            parent=base["Normal"],
            fontName=FONT_REG,
            fontSize=8,
            textColor=MUTED,
            alignment=TA_CENTER,
        ))
    if "SafeBody" not in names:
        base.add(ParagraphStyle(
            "SafeBody",
            parent=base["BodyText"],
            fontName=FONT_REG,
            fontSize=10,
            leading=13,
        ))
    return base


def _safe_text(value: Any, max_len: int = 4000) -> str:
    """Escape XML-sensitive chars for ReportLab Paragraph; strip unsupported control chars."""
    if value is None:
        return "—"
    text = str(value)
    # Remove control characters except newline/tab
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    if len(text) > max_len:
        text = text[: max_len - 1] + "…"
    try:
        return escape(text)
    except Exception:
        return escape(text.encode("ascii", "replace").decode("ascii"))


def _p(text: Any, style) -> Paragraph:
    """Create a Paragraph that never raises on bad Unicode/XML."""
    try:
        return Paragraph(_safe_text(text), style)
    except Exception:
        try:
            cleaned = re.sub(r"[^\x20-\x7E\n]", "?", str(text or ""))
            return Paragraph(escape(cleaned), style)
        except Exception:
            return Paragraph("—", style)


def _header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(FONT_REG, 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(inch, 0.5 * inch, "AI-FORGE Digital Forensics Platform — Confidential")
    canvas.drawRightString(A4[0] - inch, 0.5 * inch, f"Page {doc.page}")
    canvas.restoreState()


def _info_table(rows: List[List[str]], col_widths=None) -> Table:
    safe_rows = [[_safe_text(c, 500) for c in row] for row in rows]
    t = Table(safe_rows, colWidths=col_widths or [2.2 * inch, 4.3 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f3f4f6")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
        ("FONTNAME", (0, 0), (0, -1), FONT_BOLD),
        ("FONTNAME", (1, 0), (1, -1), FONT_REG),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def _section(styles, title: str, story: list):
    story.append(_p(title, styles["SectionHead"]))


def _prepare_image(path: Path, evidence_id: str, key: str) -> Optional[Path]:
    """
    Convert / resize image to a ReportLab-safe RGB JPEG.
    Returns None if missing or unreadable — never raises.
    """
    path = Path(path)
    if not path.exists() or path.stat().st_size <= 0:
        return None
    try:
        from PIL import Image as PILImage

        out_dir = _SAFE_IMG_DIR / evidence_id
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / f"{key}_safe.jpg"

        with PILImage.open(path) as im:
            im = im.convert("RGB")
            # Cap dimensions to keep PDF size reasonable and avoid ReportLab crashes
            max_side = 1600
            w, h = im.size
            if max(w, h) > max_side:
                scale = max_side / float(max(w, h))
                resample = getattr(getattr(PILImage, "Resampling", PILImage), "LANCZOS", PILImage.LANCZOS)
                im = im.resize((int(w * scale), int(h * scale)), resample)
            im.save(dest, format="JPEG", quality=82, optimize=True)

        if dest.exists() and dest.stat().st_size > 0:
            return dest
    except Exception as exc:
        logger.warning("[PDF] Image prepare failed for %s: %s", path, exc)
    return None


def _add_image(story, styles, path: Any, evidence_id: str, key: str, width=5.5 * inch, height=3.5 * inch):
    """Embed image if available; otherwise write 'Image unavailable'."""
    try:
        src = Path(str(path)) if path else None
        if not src or not src.exists():
            story.append(_p(f"{key}: Image unavailable", styles["SafeBody"]))
            return

        safe = _prepare_image(src, evidence_id, key)
        if not safe:
            story.append(_p(f"{key}: Image unavailable", styles["SafeBody"]))
            return

        story.append(Image(str(safe), width=width, height=height))
    except Exception as exc:
        logger.warning("[PDF] Image embed failed for %s: %s", key, exc)
        story.append(_p(f"{key}: Image unavailable", styles["SafeBody"]))


def export_pdf(bundle: Dict[str, Any], output_path: Path) -> str:
    """
    Build a forensic PDF at output_path using ReportLab.
    Never raises for missing assets — logs and continues.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("[PDF] Creating report")
    logger.info("[PDF] Creating report → %s", output_path)

    styles = _styles()
    story: list = []
    meta = bundle.get("meta", {}) or {}
    exec_sum = bundle.get("executive_summary", {}) or {}
    tech = bundle.get("technical_summary", {}) or {}
    evidence = bundle.get("evidence_summary", {}) or {}
    template = str(meta.get("template", "full")).lower()
    evidence_id = str(meta.get("evidence_id", "unknown"))

    try:
        charts = generate_all_charts(bundle, evidence_id) or {}
    except Exception as exc:
        logger.warning("[PDF] Chart generation failed: %s", exc)
        charts = {}

    # ── Cover ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 1.5 * inch))
    story.append(_p("AI-FORGE", styles["BrandTitle"]))
    story.append(_p("Digital Forensic Investigation Report", styles["Heading2"]))
    story.append(Spacer(1, 0.3 * inch))

    risk_score = exec_sum.get("risk_score", 0) or 0
    confidence = exec_sum.get("confidence", 0) or 0
    try:
        risk_score = float(risk_score)
    except (TypeError, ValueError):
        risk_score = 0.0
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.0

    cover_rows = [
        ["Report ID", meta.get("report_id", "—")],
        ["Evidence ID", evidence_id],
        ["Generated", str(meta.get("generated_at", datetime.now().isoformat()))[:19]],
        ["Template", template.upper()],
        ["Verdict", str(exec_sum.get("verdict", "—"))],
        ["Risk Score", f"{risk_score:.1f} / 100 ({exec_sum.get('risk_level', '')})"],
        ["Confidence", f"{confidence:.1f}%"],
    ]
    if evidence.get("sha256"):
        cover_rows.append(["SHA-256", str(evidence["sha256"])[:32] + "…"])
    story.append(_info_table(cover_rows))
    story.append(PageBreak())

    # ── Case / Executive Summary ─────────────────────────────────────────
    _section(styles, "Case Summary", story)
    if exec_sum.get("narrative"):
        story.append(_p(exec_sum["narrative"], styles["BodyJustify"]))
        story.append(Spacer(1, 0.15 * inch))
    story.append(_p(f"Recommendation: {exec_sum.get('recommendation', '—')}", styles["SafeBody"]))
    for finding in exec_sum.get("key_findings", []) or []:
        story.append(_p(f"• {finding}", styles["SafeBody"]))

    # ── Fraud Risk Gauge ─────────────────────────────────────────────────
    _section(styles, "Fraud Risk Gauge", story)
    if charts.get("risk_gauge"):
        _add_image(story, styles, charts["risk_gauge"], evidence_id, "risk_gauge", 3 * inch, 2.2 * inch)
    else:
        story.append(_p(f"Risk score: {risk_score:.1f} / 100 — gauge image unavailable", styles["SafeBody"]))

    # ── Technical / module scores ────────────────────────────────────────
    if template in ("full", "technical", "court"):
        story.append(PageBreak())
        _section(styles, "Technical Summary", story)
        story.append(_p(
            f"Scan mode: {tech.get('scan_mode', 'deep')} | "
            f"Spectral fusion score: {tech.get('spectral_fusion_score', 0)}",
            styles["SafeBody"],
        ))
        if charts.get("module_scores"):
            story.append(Spacer(1, 0.15 * inch))
            _add_image(
                story, styles, charts["module_scores"], evidence_id, "module_scores",
                6.5 * inch, 3.2 * inch,
            )

        tampering = tech.get("tampering") or {}
        if tampering:
            story.append(Spacer(1, 0.15 * inch))
            story.append(_info_table([
                ["Tampering Verdict", str(tampering.get("verdict", "—"))],
                ["Severity", str(tampering.get("severity", "—"))],
                ["Score", str(tampering.get("score", "—"))],
            ]))

    # ── Evidence / Metadata ──────────────────────────────────────────────
    story.append(PageBreak())
    _section(styles, "Metadata & Evidence Integrity", story)
    ev_rows = [
        ["Filename", evidence.get("original_filename", "—")],
        ["Media Type", evidence.get("media_type", "—")],
        ["Size", f"{evidence.get('size_bytes', 0):,} bytes"],
        ["SHA-256", evidence.get("sha256", "—")],
        ["SHA-512", (str(evidence.get("sha512") or "—")[:48] + "…") if evidence.get("sha512") else "—"],
        ["Intake", str(evidence.get("intake_timestamp", "—"))[:19]],
        ["Custody Events", str(evidence.get("custody_events", 0))],
        ["Chain Verified", "YES" if evidence.get("chain_verified") else "NO"],
    ]
    story.append(_info_table(ev_rows))

    # ── Timeline ─────────────────────────────────────────────────────────
    timeline = bundle.get("timeline", []) or []
    story.append(PageBreak())
    _section(styles, "Investigation Timeline", story)
    if charts.get("timeline"):
        height = min(6.0, max(2.0, len(timeline) * 0.25)) * inch
        _add_image(story, styles, charts["timeline"], evidence_id, "timeline", 6.5 * inch, height)
    if timeline:
        for event in timeline[:20]:
            ts = str(event.get("timestamp") or "")[:19]
            story.append(_p(
                f"{event.get('type')} [{ts}] — {event.get('description', '')} "
                f"({event.get('actor', '')})",
                styles["SafeBody"],
            ))
    else:
        story.append(_p("No timeline events recorded.", styles["SafeBody"]))

    # ── Chain of Custody ─────────────────────────────────────────────────
    custody = bundle.get("custody_chain") or []
    story.append(PageBreak())
    _section(styles, "Chain of Custody", story)
    if custody:
        for i, event in enumerate(custody[:30], 1):
            story.append(_p(
                f"{i}. {event.get('event_type', 'EVENT')} — "
                f"{event.get('action_description', '')} "
                f"[{str(event.get('event_timestamp') or '')[:19]}] "
                f"by {event.get('actor_name') or event.get('actor_id') or 'system'}",
                styles["SafeBody"],
            ))
    else:
        story.append(_p("No custody events recorded.", styles["SafeBody"]))

    court = bundle.get("court_certification")
    if court:
        story.append(Spacer(1, 0.2 * inch))
        _section(styles, "Court Report Certification", story)
        story.append(_p(court.get("certification", ""), styles["BodyJustify"]))
        story.append(Spacer(1, 0.1 * inch))
        story.append(_p(court.get("chain_of_custody_attestation", ""), styles["BodyJustify"]))
        att = court.get("hash_attestation") or {}
        if att.get("sha256"):
            story.append(_p(
                f"Evidence Hash Attestation — SHA-256: {att['sha256']} | "
                f"SHA-512: {att.get('sha512', '—')}",
                styles["SafeBody"],
            ))

    # ── Forensic Visualizations (ELA / Edge / Wavelet / Copy-Move / Heatmaps)
    artifacts = bundle.get("artifacts") or {}
    preferred = ["ela", "edges", "wavelet", "copy_move", "heatmap"]
    viz_keys = [k for k in preferred if k in artifacts] + [
        k for k in artifacts if k not in preferred and (
            "heatmap" in k or k.startswith("explain_")
        )
    ]

    if template in ("full", "technical"):
        story.append(PageBreak())
        _section(styles, "Forensic Visualizations", story)
        if not viz_keys:
            story.append(_p("No forensic visualization artifacts available.", styles["SafeBody"]))
        for key in viz_keys[:8]:
            story.append(_p(key.replace("_", " ").title(), styles["SafeBody"]))
            _add_image(story, styles, artifacts.get(key), evidence_id, key)
            story.append(Spacer(1, 0.12 * inch))

    # ── AI Jury Verdict ──────────────────────────────────────────────────
    jury = bundle.get("jury") or {}
    fusion = jury.get("fusion") or jury
    story.append(PageBreak())
    _section(styles, "AI Jury Verdict", story)
    verdict = fusion.get("verdict") or fusion.get("final_verdict") or "—"
    story.append(_p(
        f"Verdict: {verdict} | Risk: {fusion.get('risk_level', '—')} | "
        f"Confidence: {fusion.get('confidence', confidence)}",
        styles["SafeBody"],
    ))
    if fusion.get("majority_opinion"):
        story.append(_p(fusion["majority_opinion"], styles["BodyJustify"]))

    # ── Recommendations ──────────────────────────────────────────────────
    _section(styles, "Recommendations", story)
    recs = fusion.get("recommendations") or []
    if not recs and exec_sum.get("recommendation"):
        recs = [exec_sum["recommendation"]]
    if recs:
        for rec in recs[:8]:
            story.append(_p(f"• {rec}", styles["SafeBody"]))
    else:
        story.append(_p("No additional recommendations.", styles["SafeBody"]))

    story.append(Spacer(1, 0.5 * inch))
    story.append(_p(
        "This report is AI-assisted and should be verified by a qualified forensic expert. "
        "Generated by AI-FORGE Digital Forensic Platform.",
        styles["Footer"],
    ))

    print("[PDF] Saving report")
    logger.info("[PDF] Saving report → %s", output_path)

    try:
        # Atomic write via temp file in same directory
        tmp = output_path.with_suffix(".pdf.tmp")
        doc = SimpleDocTemplate(
            str(tmp),
            pagesize=A4,
            rightMargin=inch,
            leftMargin=inch,
            topMargin=inch,
            bottomMargin=0.75 * inch,
            title=f"AI-FORGE Report {evidence_id}",
            author="AI-FORGE",
        )
        doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
        if output_path.exists():
            output_path.unlink(missing_ok=True)
        tmp.replace(output_path)
        print("[PDF] Saved successfully")
        logger.info("[PDF] Saved successfully (%s bytes)", output_path.stat().st_size)
    except Exception:
        print("[PDF] Generation failed")
        logger.error("[PDF] Generation failed\n%s", traceback.format_exc())
        # Clean temp
        try:
            Path(str(output_path) + ".tmp").unlink(missing_ok=True)
            output_path.with_suffix(".pdf.tmp").unlink(missing_ok=True)
        except OSError:
            pass
        raise

    return str(output_path)


def ensure_report_pdf(evidence_id: str, analysis_dir: Path, jury_data: Optional[Dict] = None) -> Path:
    """
    Ensure analysis_dir/report.pdf exists — generate if missing.
    Uses pathlib; never hardcodes absolute paths.
    """
    analysis_dir = Path(analysis_dir)
    analysis_dir.mkdir(parents=True, exist_ok=True)
    dest = analysis_dir / "report.pdf"

    if dest.is_file() and dest.stat().st_size > 1000:
        print("[PDF] File found")
        logger.info("[PDF] File found → %s", dest)
        return dest

    print("[PDF] Creating report")
    logger.info("[PDF] report.pdf missing — regenerating for %s", evidence_id)

    from backend.reports.report_builder import build_report_bundle

    bundle = build_report_bundle(evidence_id, template="full", jury_data=jury_data)
    export_pdf(bundle, dest)

    # Clear stale exporter cache entry so future exports refresh
    try:
        from backend.reports import exporter as exp

        for key in list(exp._file_cache.keys()):
            if key.startswith(f"{evidence_id}:pdf:"):
                exp._file_cache.pop(key, None)
    except Exception:
        pass

    return dest
