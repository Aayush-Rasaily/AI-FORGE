"""
HTML forensic report export — modern dark enterprise theme.
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any, Dict


def export_html(bundle: Dict[str, Any], output_path: Path) -> str:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    meta = bundle.get("meta", {})
    exec_sum = bundle.get("executive_summary", {})
    tech = bundle.get("technical_summary", {})
    evidence = bundle.get("evidence_summary", {})
    tampering = bundle.get("tampering") or tech.get("tampering") or {}
    jury = bundle.get("jury") or {}
    fusion = jury.get("fusion") or jury

    risk = exec_sum.get("risk_score", 0)
    risk_color = "#ef4444" if risk >= 61 else "#f97316" if risk >= 31 else "#22c55e"

    findings_html = "".join(
        f"<li>{html.escape(str(f))}</li>" for f in exec_sum.get("key_findings", [])
    )
    signals = tech.get("signals") or {}
    signals_rows = "".join(
        f"<tr><td>{html.escape(str(k))}</td><td>{html.escape(str(v))}</td></tr>"
        for k, v in list(signals.items())[:20]
    )

    artifact_imgs = ""
    for key, path in (bundle.get("artifacts") or {}).items():
        if Path(path).exists() and key in ("ela", "edges", "wavelet", "copy_move", "heatmap"):
            artifact_imgs += f"""
            <div class="artifact-card">
              <h4>{html.escape(key.replace('_', ' ').title())}</h4>
              <img src="file:///{Path(path).as_posix()}" alt="{html.escape(key)}" />
            </div>"""

    timeline_html = ""
    for ev in bundle.get("timeline", [])[:15]:
        timeline_html += f"""
        <div class="timeline-item">
          <span class="ts">{html.escape(str(ev.get('timestamp', ''))[:19])}</span>
          <strong>{html.escape(str(ev.get('type', '')))}</strong>
          <p>{html.escape(str(ev.get('description', '')))}</p>
        </div>"""

    content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>AI-FORGE Report — {html.escape(meta.get('evidence_id', ''))}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Segoe UI',system-ui,sans-serif;background:#0B1120;color:#e2e8f0;line-height:1.6}}
  .header{{background:linear-gradient(135deg,#1e40af,#0ea5e9);padding:2rem;text-align:center}}
  .header h1{{font-size:1.8rem;font-weight:700}}
  .header p{{opacity:.85;margin-top:.5rem}}
  .container{{max-width:900px;margin:0 auto;padding:2rem}}
  .card{{background:#111827;border:1px solid #1F2937;border-radius:12px;padding:1.5rem;margin-bottom:1.5rem}}
  .card h2{{color:#38bdf8;font-size:1.1rem;margin-bottom:1rem;border-bottom:1px solid #1F2937;padding-bottom:.5rem}}
  .risk-gauge{{text-align:center;padding:1.5rem}}
  .risk-score{{font-size:3rem;font-weight:700;color:{risk_color}}}
  table{{width:100%;border-collapse:collapse;font-size:.9rem}}
  td,th{{padding:.5rem .75rem;border:1px solid #1F2937;text-align:left}}
  th{{background:#1F2937;color:#94a3b8}}
  .artifacts{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem}}
  .artifact-card img{{width:100%;border-radius:8px;margin-top:.5rem}}
  .timeline-item{{border-left:2px solid #3b82f6;padding-left:1rem;margin-bottom:1rem}}
  .ts{{font-size:.75rem;color:#64748b}}
  .footer{{text-align:center;padding:2rem;color:#64748b;font-size:.8rem}}
  @media print{{body{{background:#fff;color:#000}}.card{{border:1px solid #ccc}}}}
</style>
</head>
<body>
<div class="header">
  <h1>AI-FORGE</h1>
  <p>Digital Forensic Investigation Report</p>
  <p style="font-size:.85rem;margin-top:.25rem">{html.escape(meta.get('report_id', ''))}</p>
</div>
<div class="container">
  <div class="card">
    <h2>Case Summary</h2>
    <table>
      <tr><th>Evidence ID</th><td>{html.escape(meta.get('evidence_id', '—'))}</td></tr>
      <tr><th>Filename</th><td>{html.escape(exec_sum.get('filename') or '—')}</td></tr>
      <tr><th>Generated</th><td>{html.escape(str(meta.get('generated_at', ''))[:19])}</td></tr>
      <tr><th>Verdict</th><td><strong>{html.escape(str(exec_sum.get('verdict', '—')))}</strong></td></tr>
      <tr><th>Confidence</th><td>{exec_sum.get('confidence', 0):.1f}%</td></tr>
    </table>
    <div class="risk-gauge">
      <div class="risk-score">{risk:.0f}</div>
      <div>Risk Score / 100 — {html.escape(exec_sum.get('risk_level', ''))}</div>
    </div>
  </div>
  <div class="card">
    <h2>Executive Summary</h2>
    <p>{html.escape(exec_sum.get('narrative') or exec_sum.get('recommendation', ''))}</p>
    <ul style="margin-top:1rem;padding-left:1.25rem">{findings_html}</ul>
  </div>
  <div class="card">
    <h2>Tampering Analysis</h2>
    <table>
      <tr><th>Verdict</th><td>{html.escape(str(tampering.get('verdict', '—')))}</td></tr>
      <tr><th>Severity</th><td>{html.escape(str(tampering.get('severity', '—')))}</td></tr>
      <tr><th>Score</th><td>{html.escape(str(tampering.get('tampering_score', tampering.get('score', '—'))))}</td></tr>
    </table>
  </div>
  {"<div class='card'><h2>AI Jury Verdict</h2><p><strong>" + html.escape(str(fusion.get('verdict') or fusion.get('final_verdict', '—'))) + "</strong> — Risk: " + html.escape(str(fusion.get('risk_level', '—'))) + "</p></div>" if fusion.get('verdict') or fusion.get('final_verdict') else ""}
  <div class="card">
    <h2>Forensic Signals</h2>
    <table>{signals_rows or '<tr><td colspan="2">No signals recorded</td></tr>'}</table>
  </div>
  {"<div class='card'><h2>Evidence Integrity</h2><table><tr><th>SHA-256</th><td style='word-break:break-all;font-family:monospace;font-size:.75rem'>" + html.escape(evidence.get('sha256') or '—') + "</td></tr></table></div>" if evidence.get('registered') else ""}
  {"<div class='card'><h2>Investigation Timeline</h2>" + timeline_html + "</div>" if timeline_html else ""}
  {"<div class='card'><h2>Forensic Artifacts</h2><div class='artifacts'>" + artifact_imgs + "</div></div>" if artifact_imgs else ""}
</div>
<div class="footer">
  <p>Generated by AI-FORGE Digital Forensics Platform v{html.escape(meta.get('version', '2.0'))}</p>
  <p>This report is AI-assisted and should be verified by a qualified forensic expert.</p>
</div>
</body>
</html>"""

    output_path.write_text(content, encoding="utf-8")
    return str(output_path)
