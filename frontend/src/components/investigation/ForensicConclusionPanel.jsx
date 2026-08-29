/**
 * ForensicConclusionPanel.jsx
 *
 * Overall forensic verdict synthesis panel — shown after all finding cards.
 *
 * Answers per section 14 of the forensic brief:
 *   - Overall verdict (LIKELY TAMPERED / SUSPICIOUS / NO ANOMALIES)
 *   - Numbered list of primary findings
 *   - Combined evidence assessment narrative
 *   - Legal disclaimer
 *
 * FORENSIC PRINCIPLE:
 *   Never exaggerates certainty.
 *   Always uses hedged, evidence-based language.
 *   Explicitly states when evidence is insufficient for a conclusive determination.
 */

import { useMemo } from "react";
import { motion } from "framer-motion";
import {
  ShieldAlert,
  ShieldCheck,
  ShieldQuestion,
  AlertTriangle,
  FileWarning,
  Scale,
  CheckCircle2,
} from "lucide-react";
import { buildOverallConclusion } from "../forensic-evidence-viewer/forensicFindingSchema";
import { buildStandardFinding } from "../forensic-evidence-viewer/forensicFindingSchema";

// ─── Verdict display config ───────────────────────────────────────────────────

function getVerdictConfig(level) {
  switch (level) {
    case "critical":
    case "high":
      return {
        Icon: ShieldAlert,
        bg: "bg-[#1a0808]",
        border: "border-red-900/60",
        stripe: "#dc2626",
        badgeBg: "bg-red-600",
        titleColor: "text-red-400",
        subtitleColor: "text-red-200/60",
        label: "LIKELY TAMPERED",
      };
    case "medium":
      return {
        Icon: ShieldQuestion,
        bg: "bg-[#1a1200]",
        border: "border-yellow-900/50",
        stripe: "#ca8a04",
        badgeBg: "bg-yellow-600",
        titleColor: "text-yellow-400",
        subtitleColor: "text-yellow-200/60",
        label: "SUSPICIOUS",
      };
    case "low":
      return {
        Icon: AlertTriangle,
        bg: "bg-[#0e1420]",
        border: "border-blue-900/40",
        stripe: "#3b82f6",
        badgeBg: "bg-blue-600",
        titleColor: "text-blue-400",
        subtitleColor: "text-blue-200/60",
        label: "ANOMALIES DETECTED",
      };
    default:
      return {
        Icon: ShieldCheck,
        bg: "bg-[#031509]",
        border: "border-emerald-900/40",
        stripe: "#16a34a",
        badgeBg: "bg-emerald-600",
        titleColor: "text-emerald-400",
        subtitleColor: "text-emerald-200/60",
        label: "NO ANOMALIES DETECTED",
      };
  }
}

// ─── Severity dot ─────────────────────────────────────────────────────────────

function SeverityDot({ severity }) {
  const colors = {
    CRITICAL: "bg-red-500",
    HIGH: "bg-orange-500",
    MEDIUM: "bg-yellow-500",
    LOW: "bg-emerald-500",
  };
  return (
    <span
      className={`inline-block h-2 w-2 shrink-0 rounded-full mt-1.5 ${colors[severity] || "bg-slate-500"}`}
    />
  );
}

// ─── Main ForensicConclusionPanel ─────────────────────────────────────────────

function ForensicConclusionPanel({ regions = [], juryData = null, analysisResult = null }) {
  const findings = useMemo(
    () =>
      regions
        .map((r, i) => buildStandardFinding(r, i))
        .filter(Boolean),
    [regions]
  );

  const conclusion = useMemo(
    () => buildOverallConclusion(findings, juryData, analysisResult),
    [findings, juryData, analysisResult]
  );

  if (findings.length === 0 && !conclusion.juryNarrative) return null;

  const cfg = getVerdictConfig(conclusion.verdictLevel);
  const VerdictIcon = cfg.Icon;

  return (
    <motion.section
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.1 }}
      className={`conclusion-panel overflow-hidden rounded-xl border ${cfg.border} ${cfg.bg}`}
    >
      {/* Top color stripe */}
      <div className="h-1 w-full" style={{ background: cfg.stripe }} />

      <div className="p-6 space-y-5">
        {/* ── Verdict Banner ── */}
        <div className="flex items-center gap-4">
          <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${cfg.badgeBg}`}>
            <VerdictIcon className="h-6 w-6 text-white" />
          </div>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
              Overall Forensic Verdict
            </p>
            <p className={`text-xl font-bold tracking-wide ${cfg.titleColor}`}>
              {conclusion.overallVerdict}
            </p>
          </div>

          {/* Finding counts */}
          <div className="ml-auto flex gap-3">
            {conclusion.criticalCount > 0 && (
              <div className="text-center">
                <p className="text-lg font-bold text-red-400">{conclusion.criticalCount}</p>
                <p className="text-[10px] text-slate-500">Critical</p>
              </div>
            )}
            {conclusion.highCount > 0 && (
              <div className="text-center">
                <p className="text-lg font-bold text-orange-400">{conclusion.highCount}</p>
                <p className="text-[10px] text-slate-500">High</p>
              </div>
            )}
            {conclusion.mediumCount > 0 && (
              <div className="text-center">
                <p className="text-lg font-bold text-yellow-400">{conclusion.mediumCount}</p>
                <p className="text-[10px] text-slate-500">Medium</p>
              </div>
            )}
            {conclusion.lowCount > 0 && (
              <div className="text-center">
                <p className="text-lg font-bold text-emerald-400">{conclusion.lowCount}</p>
                <p className="text-[10px] text-slate-500">Low</p>
              </div>
            )}
          </div>
        </div>

        {/* ── Primary Findings List ── */}
        {conclusion.primaryFindings.length > 0 && (
          <div className="rounded-lg border border-slate-800/60 bg-black/20 p-4">
            <p className="mb-3 flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-slate-400">
              <Scale className="h-3.5 w-3.5" />
              Primary Findings
            </p>
            <ol className="space-y-2">
              {conclusion.primaryFindings.map((f, i) => (
                <li
                  key={f.findingId}
                  className="flex items-start gap-2.5 text-sm text-slate-200"
                >
                  <span className="mt-0.5 shrink-0 text-[11px] font-bold text-slate-500">
                    {i + 1}.
                  </span>
                  <SeverityDot severity={f.severity} />
                  <span>{f.title}</span>
                  <span className="ml-auto shrink-0 text-[10px] text-slate-600">
                    {f.findingId}
                  </span>
                </li>
              ))}
            </ol>
          </div>
        )}

        {/* ── Combined Assessment ── */}
        <div className="rounded-lg border border-slate-800/60 bg-black/15 p-4">
          <p className="mb-2 flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-slate-400">
            <FileWarning className="h-3.5 w-3.5" />
            Combined Assessment
          </p>
          <p className="text-sm leading-relaxed text-slate-300">
            {conclusion.combinedAssessment}
          </p>
        </div>

        {/* ── Jury Narrative (if available and different) ── */}
        {conclusion.juryNarrative &&
          conclusion.juryNarrative !== conclusion.combinedAssessment && (
          <div className="rounded-lg border border-violet-500/20 bg-violet-500/5 p-4">
            <p className="mb-2 flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-violet-400/80">
              <Scale className="h-3.5 w-3.5" />
              AI Jury Narrative
            </p>
            <p className="text-xs leading-relaxed text-slate-400 italic">
              "{conclusion.juryNarrative}"
            </p>
          </div>
        )}

        {/* ── Legal Disclaimer ── */}
        {conclusion.disclaimer && (
          <div className="rounded-lg border border-slate-800 bg-slate-900/30 p-3">
            <p className="text-[11px] leading-relaxed text-slate-500">
              <span className="font-semibold text-slate-400">Investigator Note: </span>
              {conclusion.disclaimer}
            </p>
          </div>
        )}

        {/* Clean state */}
        {conclusion.verdictLevel === "clean" && (
          <div className="flex items-center gap-3 rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3">
            <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
            <p className="text-xs text-slate-300">
              Forensic analysis found no indicators of digital manipulation in the submitted evidence.
            </p>
          </div>
        )}
      </div>
    </motion.section>
  );
}

export default ForensicConclusionPanel;
