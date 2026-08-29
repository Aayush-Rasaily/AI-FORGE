import { motion } from "framer-motion";
import { useState } from "react";
import {
  FileText,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  ChevronDown,
  BookOpen,
} from "lucide-react";
import {
  translateVerdict,
  translateTechTerm,
} from "./forensicTranslator";

function XAICard({ exp, isSelected, onClick }) {
  const { title, page, severity, location, summary, reason, impact } = exp;

  let sevColor = "text-yellow-400";
  let sevBg = "bg-yellow-400/10";
  let sevBorder = "border-yellow-400/30";
  let Icon = AlertTriangle;

  if (severity === "Critical") {
    sevColor = "text-red-500";
    sevBg = "bg-red-500/10";
    sevBorder = "border-red-500/30";
    Icon = AlertTriangle;
  } else if (severity === "High") {
    sevColor = "text-orange-400";
    sevBg = "bg-orange-400/10";
    sevBorder = "border-orange-400/30";
  } else if (severity === "Low") {
    sevColor = "text-blue-400";
    sevBg = "bg-blue-400/10";
    sevBorder = "border-blue-400/30";
    Icon = HelpCircle;
  }

  return (
    <div
      onClick={onClick}
      className={`cursor-pointer transition-all duration-200 rounded-xl border ${isSelected ? `border-cyan-500 bg-[#1e293b]` : `${sevBorder} bg-[#0f172a]/80 hover:bg-[#1e293b]`} p-4`}
    >
      <div className="flex items-start gap-3">
        <div className={`mt-1 p-2 rounded-lg ${sevBg} ${sevColor}`}>
          <Icon className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex justify-between items-start">
            <h4 className="text-sm font-bold text-white mb-1">{title}</h4>
            <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${sevBg} ${sevColor}`}>
              Page {page} • {location}
            </span>
          </div>
          <p className="text-sm text-slate-300 font-medium mb-2">{summary}</p>
          <div className="space-y-2 mt-3 pt-3 border-t border-slate-700/50">
            <div>
              <span className="text-[10px] font-bold uppercase text-slate-500 block mb-0.5">Why AI Flagged It</span>
              <p className="text-[11px] text-slate-400">{reason}</p>
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase text-slate-500 block mb-0.5">Possible Consequence</span>
              <p className="text-[11px] text-amber-200/80">{impact}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * ForensicNarrativeReport
 *
 * A professional plain-language forensic investigation report.
 * Reads like an official police / court forensic document.
 * Every finding uses plain English — no technical AI jargon.
 */
function ForensicNarrativeReport({
  regions = [],
  findings = [],
  analysisResult = null,
  evidenceId = null,
  dashboard = null,
  selectedRegion = null,
  onSelectRegion,
}) {
  const [showTechDetails, setShowTechDetails] = useState(false);

  // Fetch explanations from XAI engine
  const explanations = dashboard?.jury?.fusion?.explanations || analysisResult?.jury?.fusion?.explanations || [];
  
  // Use explanations if they exist, otherwise fallback to empty to trigger no manipulation state
  const hasExplanations = explanations.length > 0;

  // Fix ReferenceError crashing the UI
  const plainVerdict = analysisResult?.forensic_dossier?.plain_verdict ?? analysisResult?.plainVerdict ?? {};
  const verdict = analysisResult?.jury?.verdict || analysisResult?.verdict || dashboard?.verdict || "Authentic";
  const { overallSeverity } = translateVerdict(verdict);
  
  const techExplanation = analysisResult?.jury?.fusion?.explanation || analysisResult?.explanation || dashboard?.explanation || "";

  // Consider it "having explanations" if either the XAI cards exist or we have a plainVerdict summary
  if (!hasExplanations && !plainVerdict?.summary && !techExplanation) {
    return (
      <div className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-5">
        <div className="flex items-center gap-2 mb-3">
          <FileText className="h-4 w-4 text-cyan-400" />
          <h3 className="text-sm font-semibold text-white">Investigation Report</h3>
        </div>
        <p className="text-sm text-slate-500">
          Run analysis to generate the investigation report.
        </p>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 overflow-hidden shadow-xl"
    >
      {/* Report header */}
      <div className="border-b border-[#1F2937] bg-[#0F172A]/80 px-5 py-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-cyan-500/10 border border-cyan-500/20">
              <BookOpen className="h-4.5 w-4.5 text-cyan-400" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white tracking-tight">
                Forensic Investigation Report
              </h3>
              {evidenceId && (
                <p className="text-[10px] font-mono text-slate-500 mt-0.5">
                  Ref: {evidenceId.slice(0, 16).toUpperCase()}
                </p>
              )}
            </div>
          </div>
          {/* Toggle: Plain / Technical */}
          <button
            type="button"
            id="report-toggle-view"
            onClick={() => setShowTechDetails((s) => !s)}
            className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-[10px] font-medium transition ${
              showTechDetails
                ? "border-violet-500/40 bg-violet-500/10 text-violet-300"
                : "border-[#1F2937] text-slate-500 hover:text-slate-300"
            }`}
          >
            {showTechDetails ? (
              <><BookOpen className="h-3 w-3" /> Plain Language</>
            ) : (
              <><ChevronDown className="h-3 w-3" /> Technical Details</>
            )}
          </button>
        </div>
      </div>

      <div className="space-y-4 p-5">
        {/* Overall verdict box */}
        {plainVerdict?.summary && (
          <div
            className={`rounded-xl border-2 px-4 py-3 ${overallSeverity?.borderClass || "border-slate-500"} ${overallSeverity?.bgClass || "bg-slate-500/10"}`}
          >
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">
              AI Assessment
            </p>
            <p className={`text-sm font-semibold leading-snug ${overallSeverity?.textClass || "text-slate-300"}`}>
              {plainVerdict?.summary ?? "No summary available"}
            </p>
            {plainVerdict?.confidence && (
              <p className="mt-2 text-xs text-slate-400">
                Confidence: <span className="font-bold text-white">{plainVerdict.confidence}%</span>
              </p>
            )}
          </div>
        )}

        {/* Explainable AI Cards */}
        {!showTechDetails && (
          <div className="space-y-3">
            {explanations.length > 0 ? (
              explanations.map((exp, i) => {
                const isSelected = selectedRegion?.id === exp.region_id || selectedRegion?.region_id === exp.region_id;
                return (
                  <XAICard
                    key={i}
                    exp={exp}
                    isSelected={isSelected}
                    onClick={() => {
                      // Try to find the exact region in the original list to select
                      const targetRegion = regions.find(r => r.id === exp.region_id || r.region_id === exp.region_id);
                      if (targetRegion && onSelectRegion) {
                        onSelectRegion(targetRegion);
                      }
                    }}
                  />
                );
              })
            ) : (
              <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4 flex items-start gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-400 mt-0.5" />
                <div>
                  <h4 className="text-sm font-bold text-emerald-400 mb-1">No confirmed manipulation was detected.</h4>
                  <p className="text-xs text-emerald-400/80">The system could not localize any distinct tampering artifacts.</p>
                </div>
              </div>
            )}
          </div>
        )}
        {showTechDetails && techExplanation && (
          <div className="space-y-2">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
              Technical AI Explanation
            </p>
            <div className="rounded-xl border border-[#1F2937] bg-[#0B1120] p-3.5 text-xs leading-relaxed text-slate-300 space-y-2">
              {String(techExplanation)
                .split(/\n+/)
                .map(p => p.trim())
                .filter(Boolean)
                .map((p, i) => (
                  <p key={i}>{p}</p>
                ))}
            </div>
          </div>
        )}

        {showTechDetails && findings.length > 0 && (
          <div className="space-y-2">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
              Region Technical Data
            </p>
            {findings.map((finding, i) => {
              const raw = finding.raw || {};
              const votes = raw.detector_votes || {};
              return (
                <div key={i} className="rounded-xl border border-[#1F2937] bg-[#0B1120] p-3 text-[11px] text-slate-400">
                  <p className="font-semibold text-slate-200 mb-1">Region {i + 1} — {finding.editType}</p>
                  {Object.keys(votes).length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mb-1">
                      {Object.entries(votes).map(([k, v]) => (
                        <span
                          key={k}
                          className={`rounded px-1.5 py-0.5 text-[9px] font-semibold ${
                            v ? "bg-emerald-500/15 text-emerald-400" : "bg-slate-800 text-slate-600 line-through"
                          }`}
                        >
                          {k}
                        </span>
                      ))}
                    </div>
                  )}
                  {raw.reason && <p className="text-slate-500">{translateTechTerm(raw.reason)}</p>}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </motion.div>
  );
}

export default ForensicNarrativeReport;
