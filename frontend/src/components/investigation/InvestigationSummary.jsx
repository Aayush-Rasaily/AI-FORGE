import { motion } from "framer-motion";
import { ClipboardList, Layers, Scale, FileWarning } from "lucide-react";

/**
 * Investigation Summary — replaces Evidence Timeline clutter.
 * Surfaces WHAT / WHERE / WHY / CONFIDENCE from engine outputs.
 */
function InvestigationSummary({
  analysisResult,
  verdict,
  riskScore,
  confidence,
  explanation,
}) {
  const analysis = analysisResult?.analysis || analysisResult || {};
  const fusion = analysis.evidence_fusion || analysis.risk_fusion || {};
  const contributions = fusion.detector_contributions || analysis.detector_outputs || [];
  const elevated =
    fusion.elevated_detectors ||
    fusion.elevated_modules ||
    contributions.filter((c) => Number(c.score) >= 0.28).map((c) => c.detector_name || c.detector) ||
    [];

  const narrative =
    explanation ||
    analysis.detailed_investigation ||
    analysis.explanation ||
    "Run analysis to generate a cite-only investigation narrative.";

  const lines = String(narrative)
    .split(/\n+/)
    .map((l) => l.trim())
    .filter(Boolean)
    .slice(0, 14);

  return (
    <motion.section
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mb-6 space-y-4 rounded-2xl border border-[#1F2937] bg-[#111827]/85 p-5 backdrop-blur-xl"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <ClipboardList className="h-4 w-4 text-cyan-400" />
          <div>
            <h3 className="text-sm font-semibold text-white">Investigation Summary</h3>
            <p className="text-[11px] text-slate-500">
              What changed · Where · Why · How detected · Confidence
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2 text-[11px]">
          <span className="rounded-lg border border-[#1F2937] bg-[#0B1120] px-2.5 py-1 text-slate-300">
            Risk {Math.round(Number(riskScore) || 0)}%
          </span>
          <span className="rounded-lg border border-[#1F2937] bg-[#0B1120] px-2.5 py-1 text-slate-300">
            Confidence {Math.round(Number(confidence) || 0)}%
          </span>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <div className="rounded-xl border border-[#1F2937] bg-[#0B1120]/70 p-3">
          <div className="mb-1 flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-slate-500">
            <Scale className="h-3 w-3" /> Verdict
          </div>
          <p className="text-sm font-semibold text-white">{verdict || fusion.verdict || "Pending"}</p>
        </div>
        <div className="rounded-xl border border-[#1F2937] bg-[#0B1120]/70 p-3 md:col-span-2">
          <div className="mb-1 flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-slate-500">
            <Layers className="h-3 w-3" /> Elevated detectors
          </div>
          <p className="text-xs text-slate-300">
            {elevated.length ? elevated.join(" · ") : "None above threshold"}
          </p>
        </div>
      </div>

      <div className="rounded-xl border border-[#1F2937] bg-[#0B1120]/50 p-4">
        <div className="mb-2 flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-slate-500">
          <FileWarning className="h-3 w-3" /> Cite-only AI explanation
        </div>
        <div className="space-y-1.5 text-sm leading-relaxed text-slate-300">
          {lines.map((line, i) => {
            if (/^(Evidence|Conclusion|Confidence|Detailed)/i.test(line)) {
              return (
                <p key={i} className="pt-1 text-[11px] font-semibold uppercase tracking-wider text-cyan-400/90">
                  {line}
                </p>
              );
            }
            return <p key={i}>{line}</p>;
          })}
        </div>
      </div>

      {Array.isArray(contributions) && contributions.length > 0 && (
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {contributions.slice(0, 9).map((c, idx) => {
            const name = c.detector_name || c.detector || `detector-${idx}`;
            const score = Number(c.score ?? c.contribution ?? 0);
            const conf = Number(c.confidence ?? 0);
            const tone =
              score >= 0.42 ? "border-red-500/30 text-red-300" : score >= 0.28 ? "border-orange-400/30 text-orange-300" : "border-emerald-500/20 text-emerald-300";
            return (
              <div key={name} className={`rounded-lg border bg-[#0B1120]/60 px-3 py-2 ${tone}`}>
                <p className="text-xs font-semibold capitalize">{String(name).replace(/_/g, " ")}</p>
                <p className="mt-0.5 text-[10px] text-slate-500">
                  score {(score <= 1 ? score * 100 : score).toFixed(0)}% · conf{" "}
                  {(conf <= 1 ? conf * 100 : conf).toFixed(0)}%
                </p>
                {c.technical_reason && (
                  <p className="mt-1 line-clamp-2 text-[11px] text-slate-400">{c.technical_reason}</p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </motion.section>
  );
}

export default InvestigationSummary;
