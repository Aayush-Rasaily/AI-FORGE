import { motion } from "framer-motion";
import { MapPin, ZoomIn, CheckCircle2, ChevronDown, ChevronUp, AlertTriangle, ShieldCheck, HelpCircle, Cpu } from "lucide-react";
import { useState } from "react";
import {
  generatePlainFinding,
  translateDetectorName,
} from "./forensicTranslator";

const SEVERITY_ICONS = {
  red: AlertTriangle,
  orange: AlertTriangle,
  yellow: HelpCircle,
  green: ShieldCheck,
};

/**
 * PlainLanguageFindingCard
 *
 * A human-readable forensic finding card. Designed so that a non-technical
 * police officer immediately understands:
 *   — WHAT was changed
 *   — WHERE it was changed
 *   — WHY the AI believes it was changed
 *   — HOW serious it is
 */
function PlainLanguageFindingCard({ region, index = 0, active = false, onSelect, onZoom }) {
  const [showDetails, setShowDetails] = useState(false);

  if (!region) return null;

  const finding = generatePlainFinding(region);
  if (!finding) return null;

  const { severity, whatHappened, locationText, plainEnglish, reasons, confidence, verificationSteps, detectors } = finding;

  const SeverityIcon = SEVERITY_ICONS[severity.color] || AlertTriangle;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06 }}
      className={`group relative flex flex-col rounded-2xl border-2 transition-all duration-200 overflow-hidden ${severity.borderClass} ${
        active
          ? `${severity.bgClass} ring-2 ring-white/20 shadow-lg`
          : "bg-[#0B1120]/90 hover:bg-[#111827]/90"
      }`}
    >
      {/* Severity stripe */}
      <div
        className="h-1 w-full rounded-t-xl"
        style={{ backgroundColor: severity.hex }}
      />

      <div className="flex flex-col gap-3 p-4">
        {/* Header: severity + location */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-start gap-2.5 min-w-0">
            <div
              className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full"
              style={{ backgroundColor: severity.hex + "33", border: `1px solid ${severity.hex}66` }}
            >
              <SeverityIcon className="h-3.5 w-3.5" style={{ color: severity.hex }} />
            </div>
            <div className="min-w-0">
              <p className={`text-[10px] font-extrabold uppercase tracking-widest ${severity.textClass}`}>
                {severity.short}
              </p>
              <p className="flex items-center gap-1 text-[11px] text-slate-400 mt-0.5">
                <MapPin className="h-3 w-3 shrink-0" />
                {locationText}
              </p>
            </div>
          </div>
          {/* Confidence badge */}
          <div
            className="shrink-0 rounded-lg px-2.5 py-1 text-center"
            style={{ backgroundColor: severity.hex + "22", border: `1px solid ${severity.hex}44` }}
          >
            <p className="text-[10px] text-slate-400">AI Certainty</p>
            <p className={`text-base font-black tabular-nums ${severity.textClass}`}>
              {confidence}%
            </p>
          </div>
        </div>

        {/* Primary finding — WHAT happened */}
        <div className="rounded-xl bg-[#0B1120]/80 border border-[#1F2937] px-3.5 py-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">What was found</p>
          <p className="text-sm font-semibold text-white leading-snug">{whatHappened}</p>
          {plainEnglish && plainEnglish !== whatHappened && (
            <p className="mt-1.5 text-xs text-slate-300 leading-relaxed">{plainEnglish}</p>
          )}
        </div>

        {/* Additional evidence reasons */}
        {reasons.length > 1 && (
          <ul className="space-y-1">
            {reasons.slice(1).map((r, i) => (
              <li key={i} className="flex gap-2 text-[11px] text-slate-400 leading-snug">
                <span className="mt-0.5 text-cyan-500 shrink-0">•</span>
                <span>{r}</span>
              </li>
            ))}
          </ul>
        )}

        {/* Action buttons */}
        <div className="flex gap-2 pt-1">
          <button
            type="button"
            id={`finding-jump-${region.id || index}`}
            onClick={() => onSelect?.(region)}
            className="flex flex-1 items-center justify-center gap-1.5 rounded-xl border border-[#1F2937] bg-[#0B1120] px-3 py-2 text-[11px] font-medium text-slate-300 transition hover:border-cyan-500/40 hover:text-cyan-300"
          >
            <MapPin className="h-3.5 w-3.5" />
            Jump to Region
          </button>
          {onZoom && (
            <button
              type="button"
              id={`finding-zoom-${region.id || index}`}
              onClick={() => onZoom?.(region)}
              className="flex items-center justify-center gap-1.5 rounded-xl border border-[#1F2937] bg-[#0B1120] px-3 py-2 text-[11px] font-medium text-slate-300 transition hover:border-cyan-500/40 hover:text-cyan-300"
            >
              <ZoomIn className="h-3.5 w-3.5" />
              Zoom
            </button>
          )}
          <button
            type="button"
            id={`finding-details-${region.id || index}`}
            onClick={() => setShowDetails((s) => !s)}
            className="flex items-center justify-center gap-1 rounded-xl border border-[#1F2937] bg-[#0B1120] px-2.5 py-2 text-[11px] text-slate-500 transition hover:text-slate-300"
            title="Toggle technical details"
          >
            {showDetails ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          </button>
        </div>

        {/* Collapsible: verification + technical details */}
        {showDetails && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="space-y-3 border-t border-[#1F2937] pt-3 mt-1"
          >
            {/* Verification steps */}
            {verificationSteps.length > 0 && (
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wider text-amber-400 mb-1.5 flex items-center gap-1">
                  <CheckCircle2 className="h-3 w-3" />
                  Suggested Verification
                </p>
                <ul className="space-y-1">
                  {verificationSteps.map((step, i) => (
                    <li key={i} className="flex gap-2 text-[11px] text-slate-400 leading-snug">
                      <span className="text-amber-500 shrink-0">{i + 1}.</span>
                      <span>{step}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* AI detectors used */}
            {detectors.length > 0 && (
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1.5 flex items-center gap-1">
                  <Cpu className="h-3 w-3" />
                  AI Systems That Detected This
                </p>
                <div className="flex flex-wrap gap-1">
                  {detectors.map((d) => (
                    <span
                      key={d}
                      className="rounded-md bg-slate-800 px-2 py-0.5 text-[10px] font-medium text-cyan-300"
                    >
                      {translateDetectorName(d)}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}

export default PlainLanguageFindingCard;
