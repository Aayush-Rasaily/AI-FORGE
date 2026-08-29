import { motion } from "framer-motion";
import { FileSearch, BookOpen, ChevronDown } from "lucide-react";
import { useState } from "react";
import { translateTechTerm } from "./forensicTranslator";

function InvestigationReportPanel({
  explanation,
  selectedRegion,
  analysisResult,
  dashboard,
  findings = [],
}) {
  const [showTech, setShowTech] = useState(false);

  const text =
    selectedRegion?.investigation ||
    explanation ||
    dashboard?.explanation ||
    analysisResult?.analysis?.explanation ||
    null;

  const paragraphs = String(text || "")
    .split(/\n+/)
    .map((p) => p.trim())
    .filter(Boolean);

  // Apply plain-language translation to each paragraph
  const translatedParagraphs = showTech
    ? paragraphs
    : paragraphs.map((p) => translateTechTerm(p) !== p ? translateTechTerm(p) : p);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-5"
    >
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileSearch className="h-4 w-4 text-cyan-400" />
          <h3 className="text-sm font-semibold text-white">AI Investigation Report</h3>
        </div>
        <button
          type="button"
          id="report-panel-toggle-tech"
          onClick={() => setShowTech(s => !s)}
          className={`flex items-center gap-1.5 rounded-lg border px-2 py-1 text-[10px] font-medium transition ${
            showTech
              ? "border-violet-500/40 bg-violet-500/10 text-violet-300"
              : "border-[#1F2937] text-slate-500 hover:text-slate-300"
          }`}
        >
          <ChevronDown className="h-3 w-3" />
          {showTech ? "Plain Language" : "Technical"}
        </button>
      </div>
      {!translatedParagraphs.length ? (
        <p className="text-sm text-slate-500">
          Run analysis to generate a detailed investigation narrative.
        </p>
      ) : (
        <div className="space-y-2 text-sm leading-relaxed text-slate-300">
          {translatedParagraphs.map((p, i) => {
            const isHeading =
              /^(Evidence|Conclusion|Confidence|Detailed Investigation|Finding|Summary|Assessment)/i.test(p) ||
              (p.length < 40 && !p.includes("•") && i > 0);
            if (p.startsWith("•") || p.startsWith("-")) {
              return (
                <p key={i} className="pl-1 text-slate-300">
                  <span className="text-cyan-500">{p.slice(0, 1)}</span>
                  {p.slice(1)}
                </p>
              );
            }
            if (isHeading) {
              return (
                <p key={i} className="pt-2 text-xs font-semibold uppercase tracking-wider text-cyan-400/90">
                  {p}
                </p>
              );
            }
            return (
              <p key={i} className="text-slate-200">
                {p}
              </p>
            );
          })}
        </div>
      )}
    </motion.div>
  );
}

export default InvestigationReportPanel;
