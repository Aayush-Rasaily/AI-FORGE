import { motion } from "framer-motion";
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { useState } from "react";

function isRiskVerdict(verdict) {
  const v = String(verdict || "").toLowerCase();
  return (
    v.includes("manipul") ||
    v.includes("suspicious") ||
    v.includes("forg") ||
    v.includes("altered")
  );
}

function AgentCard({ agent, icon: Icon, role, index = 0 }) {
  const [expanded, setExpanded] = useState(false);
  const confidence = Math.round((agent.confidence || 0) * 100);
  const isRisk = isRiskVerdict(agent.verdict);
  const findings = agent.findings || [];

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06 }}
      className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-5 backdrop-blur-sm"
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-500/10">
            <Icon className="h-5 w-5 text-purple-400" />
          </div>
          <div>
            <p className="text-sm font-semibold text-white">
              {agent.agent_name || agent.name}
            </p>
            <p className="text-[10px] text-slate-500">{role}</p>
          </div>
        </div>
        {isRisk ? (
          <XCircle className="h-5 w-5 text-red-400" />
        ) : agent.verdict === "Inconclusive" ? (
          <AlertTriangle className="h-5 w-5 text-amber-400" />
        ) : (
          <CheckCircle className="h-5 w-5 text-emerald-400" />
        )}
      </div>

      <div className="mt-4 flex items-center justify-between">
        <span
          className={`text-sm font-bold ${
            isRisk
              ? "text-red-400"
              : agent.verdict === "Inconclusive"
                ? "text-amber-400"
                : "text-emerald-400"
          }`}
        >
          {agent.verdict}
        </span>
        <div className="flex items-center gap-2">
          {agent.vote && agent.vote !== "abstain" && (
            <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${
              agent.vote === "risk" ? "bg-red-500/20 text-red-300" : "bg-emerald-500/20 text-emerald-300"
            }`}>
              {agent.vote}
            </span>
          )}
          {agent.abstained && (
            <span className="rounded bg-slate-700 px-1.5 py-0.5 text-[10px] text-slate-400">abstain</span>
          )}
          <span className="text-sm text-slate-400">{confidence}%</span>
        </div>
      </div>

      <p className="mt-3 text-xs leading-relaxed text-slate-400">
        {agent.explanation}
      </p>

      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-800">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${confidence}%` }}
          transition={{ delay: 0.3 + index * 0.05, duration: 0.8 }}
          className={`h-full rounded-full ${isRisk ? "bg-red-500" : "bg-emerald-500"}`}
        />
      </div>

      {findings.length > 0 && (
        <div className="mt-4">
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="flex w-full items-center justify-between text-xs font-medium text-purple-400 hover:text-purple-300"
          >
            <span>Explainable findings ({findings.length})</span>
            {expanded ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </button>

          {expanded && (
            <div className="mt-3 space-y-3">
              {findings.map((f, i) => (
                <div
                  key={`${f.module}-${i}`}
                  className="rounded-lg border border-[#1F2937] bg-[#0B1220] p-3"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[10px] uppercase tracking-wider text-purple-400">
                      {f.module}
                    </span>
                    <span className="text-[10px] text-slate-500">
                      {Math.round((f.confidence || 0) * 100)}% conf.
                    </span>
                  </div>
                  <p className="mt-1 text-xs font-medium text-white">{f.what}</p>
                  <p className="mt-1 text-[11px] leading-relaxed text-slate-500">
                    {f.why}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
}

export default AgentCard;
