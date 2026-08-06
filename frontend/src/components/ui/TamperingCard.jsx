import { motion } from "framer-motion";
import { ShieldAlert } from "lucide-react";
import ProgressBar from "./ProgressBar";
import SignalList from "./SignalList";

/* ========================================= */
/* Severity badge colors                       */
/* ========================================= */

function getSeverityStyle(severity) {
  const s = String(severity || "").toLowerCase();

  if (s === "high" || s === "critical") {
    return "bg-red-500/15 text-red-400 border-red-500/30";
  }
  if (s === "medium" || s === "moderate") {
    return "bg-orange-500/15 text-orange-400 border-orange-500/30";
  }
  if (s === "low") {
    return "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";
  }
  return "bg-slate-500/15 text-slate-400 border-slate-500/30";
}

function getVerdictStyle(verdict) {
  const v = String(verdict || "").toLowerCase();

  if (v.includes("manipulat") || v.includes("forg") || v.includes("fake")) {
    return "text-red-400";
  }
  if (v.includes("suspicious") || v.includes("potential")) {
    return "text-orange-400";
  }
  if (v.includes("authentic") || v.includes("genuine") || v.includes("clean")) {
    return "text-emerald-400";
  }
  return "text-slate-300";
}

function TamperingCard({ tampering = {} }) {
  const verdict = tampering.verdict || "Unknown";
  const severity = tampering.severity || "Unknown";
  const score = Number(tampering.tampering_score || 0) * 100;
  const confidence = Number(tampering.confidence || 0) * 100;
  const signals = tampering.signals || [];

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
      className="rounded-2xl border border-orange-500/20 bg-gradient-to-br from-orange-500/5 to-[#111827] p-6 shadow-xl"
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-orange-500/10 border border-orange-500/20">
          <ShieldAlert className="h-5 w-5 text-orange-400" />
        </div>
        <div>
          <h4 className="text-lg font-bold text-white">Tampering Detection</h4>
          <p className="text-xs text-slate-500">AI-powered manipulation analysis</p>
        </div>
      </div>

      {/* Verdict */}
      <div className="mb-6 rounded-xl border border-[#1F2937] bg-[#0B1120]/60 p-5 text-center">
        <p className="text-xs uppercase tracking-widest text-slate-500 mb-2">
          Verdict
        </p>
        <p className={`text-2xl font-bold uppercase tracking-wide ${getVerdictStyle(verdict)}`}>
          {verdict}
        </p>
      </div>

      {/* Metrics row */}
      <div className="grid gap-4 sm:grid-cols-3 mb-6">
        <div className="rounded-xl border border-[#1F2937] bg-[#0B1120]/60 p-4 text-center">
          <p className="text-xs text-slate-500 mb-1">Severity</p>
          <span
            className={`inline-block rounded-full border px-3 py-1 text-xs font-bold uppercase ${getSeverityStyle(severity)}`}
          >
            {severity}
          </span>
        </div>

        <div className="rounded-xl border border-[#1F2937] bg-[#0B1120]/60 p-4">
          <p className="text-xs text-slate-500 mb-2 text-center">Score</p>
          <ProgressBar value={score} color="orange" showPercent />
        </div>

        <div className="rounded-xl border border-[#1F2937] bg-[#0B1120]/60 p-4 text-center">
          <p className="text-xs text-slate-500 mb-1">Confidence</p>
          <p className="text-2xl font-bold text-cyan-400">
            {confidence.toFixed(0)}%
          </p>
          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-800">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${confidence}%` }}
              transition={{ duration: 1, ease: "easeOut" }}
              className="h-full rounded-full bg-cyan-500"
            />
          </div>
        </div>
      </div>

      {/* Signals */}
      <SignalList signals={signals} title="Signals" />
    </motion.div>
  );
}

export default TamperingCard;
