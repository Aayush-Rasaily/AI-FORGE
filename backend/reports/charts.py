"""
Matplotlib chart generation for PDF/DOCX reports — risk gauge, bar charts.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ai_forge.reports.charts")

CHARTS_DIR = Path("data/temp/report_charts")


def _risk_color(score: float) -> str:
    if score >= 61:
        return "#ef4444"
    if score >= 31:
        return "#f97316"
    return "#22c55e"


def generate_risk_gauge(score: float, output_path: Path, label: str = "Risk Score") -> Optional[str]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        output_path.parent.mkdir(parents=True, exist_ok=True)
        score = min(100, max(0, float(score)))
        color = _risk_color(score)

        fig, ax = plt.subplots(figsize=(4, 3), subplot_kw={"projection": "polar"})
        theta = np.linspace(0.75 * np.pi, 2.25 * np.pi, 100)
        ax.plot(theta, [1] * 100, color="#e5e7eb", linewidth=20, solid_capstyle="round")
        fill_theta = np.linspace(0.75 * np.pi, 0.75 * np.pi + (score / 100) * 1.5 * np.pi, 100)
        ax.plot(fill_theta, [1] * len(fill_theta), color=color, linewidth=20, solid_capstyle="round")
        ax.set_ylim(0, 1.2)
        ax.axis("off")
        ax.text(0, 0, f"{score:.0f}", ha="center", va="center", fontsize=28, fontweight="bold", color=color)
        ax.text(0, -0.35, label, ha="center", va="center", fontsize=10, color="#6b7280")
        plt.tight_layout()
        plt.savefig(str(output_path), dpi=150, bbox_inches="tight", facecolor="white")
        plt.close()
        return str(output_path)
    except Exception as exc:
        logger.warning("Risk gauge generation failed: %s", exc)
        return None


def generate_module_bar_chart(
    modules: List[Dict[str, Any]],
    output_path: Path,
    title: str = "Forensic Module Scores",
) -> Optional[str]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        if not modules:
            return None

        output_path.parent.mkdir(parents=True, exist_ok=True)
        names = [m.get("module", "?")[:20] for m in modules[:12]]
        scores = [min(100, _safe(m.get("score", 0)) * (100 if _safe(m.get("score")) <= 1 else 1)) for m in modules[:12]]
        colors = [_risk_color(s) for s in scores]

        fig, ax = plt.subplots(figsize=(8, 4))
        bars = ax.barh(names, scores, color=colors, height=0.6)
        ax.set_xlim(0, 100)
        ax.set_xlabel("Score")
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.invert_yaxis()
        for bar, score in zip(bars, scores):
            ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                    f"{score:.0f}", va="center", fontsize=8)
        plt.tight_layout()
        plt.savefig(str(output_path), dpi=150, bbox_inches="tight", facecolor="white")
        plt.close()
        return str(output_path)
    except Exception as exc:
        logger.warning("Bar chart generation failed: %s", exc)
        return None


def generate_timeline_chart(timeline: List[Dict], output_path: Path) -> Optional[str]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        if not timeline:
            return None

        output_path.parent.mkdir(parents=True, exist_ok=True)
        events = timeline[:15]
        labels = [f"{e.get('type', '?')}" for e in events]
        y_pos = range(len(labels))

        fig, ax = plt.subplots(figsize=(8, max(3, len(labels) * 0.4)))
        ax.barh(list(y_pos), [1] * len(labels), color="#3b82f6", height=0.5)
        ax.set_yticks(list(y_pos))
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_xlim(0, 1.5)
        ax.set_xticks([])
        ax.set_title("Chain of Custody Timeline", fontsize=12, fontweight="bold")
        for i, ev in enumerate(events):
            ts = (ev.get("timestamp") or "")[:16]
            ax.text(1.05, i, ts, va="center", fontsize=7, color="#6b7280")
        plt.tight_layout()
        plt.savefig(str(output_path), dpi=150, bbox_inches="tight", facecolor="white")
        plt.close()
        return str(output_path)
    except Exception as exc:
        logger.warning("Timeline chart generation failed: %s", exc)
        return None


def generate_all_charts(bundle: Dict, evidence_id: str) -> Dict[str, str]:
    """Generate all chart images for a report bundle."""
    out_dir = CHARTS_DIR / evidence_id
    charts = {}
    risk = bundle.get("charts", {}).get("risk_score", 0)
    gauge = generate_risk_gauge(risk, out_dir / "risk_gauge.png")
    if gauge:
        charts["risk_gauge"] = gauge

    modules = bundle.get("charts", {}).get("module_scores", [])
    bar = generate_module_bar_chart(modules, out_dir / "module_scores.png")
    if bar:
        charts["module_scores"] = bar

    timeline = generate_timeline_chart(bundle.get("timeline", []), out_dir / "timeline.png")
    if timeline:
        charts["timeline"] = timeline

    return charts


def _safe(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default
