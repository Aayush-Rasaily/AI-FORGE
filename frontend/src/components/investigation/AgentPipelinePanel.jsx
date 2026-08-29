import { useMemo } from "react";
import { motion } from "framer-motion";
import { Bot, CheckCircle2, Loader2, SkipForward, XCircle } from "lucide-react";

const STATUS_STYLE = {
  completed: { icon: CheckCircle2, color: "text-emerald-400", label: "Done" },
  running: { icon: Loader2, color: "text-cyan-400", label: "Running" },
  skipped: { icon: SkipForward, color: "text-slate-500", label: "Skipped" },
  failed: { icon: XCircle, color: "text-red-400", label: "Failed" },
  pending: { icon: Loader2, color: "text-amber-400", label: "Pending" },
};

function AgentPipelinePanel({ investigation }) {
  const agents = useMemo(() => {
    const raw = investigation?.agents || {};
    return Object.values(raw);
  }, [investigation]);

  const plan = investigation?.plan;
  const calibration = investigation?.confidence_calibration || {};
  const timeline = investigation?.timeline || [];

  if (!investigation) {
    return (
      <div className="rounded-2xl border border-[#1F2937] bg-[#111827]/60 p-5">
        <div className="flex items-center gap-2 text-slate-400">
          <Bot className="h-4 w-4" />
          <p className="text-sm">Run Autonomous Investigate to activate the agent pipeline.</p>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-5 backdrop-blur-xl"
    >
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Bot className="h-4 w-4 text-cyan-400" />
          <h3 className="text-sm font-semibold text-white">Agent Pipeline</h3>
        </div>
        <span className="rounded-full bg-cyan-500/10 px-2.5 py-1 text-[10px] font-medium uppercase tracking-wide text-cyan-300">
          {investigation.verdict || "—"}
        </span>
      </div>

      {plan && (
        <p className="mb-3 text-xs text-slate-400">
          Profile <span className="text-slate-200">{plan.profile}</span>
          {" · "}
          {plan.modules?.length || 0} modules
          {" · "}
          est. {plan.estimated_seconds}s
        </p>
      )}

      <div className="mb-4 space-y-2">
        {agents.map((agent) => {
          const style = STATUS_STYLE[agent.status] || STATUS_STYLE.pending;
          const Icon = style.icon;
          return (
            <div
              key={agent.agent_id}
              className="flex items-start gap-3 rounded-xl border border-[#1F2937] bg-[#0B1120]/70 px-3 py-2"
            >
              <Icon
                className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${style.color} ${
                  agent.status === "running" ? "animate-spin" : ""
                }`}
              />
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <p className="truncate text-xs font-medium text-white">{agent.agent_name}</p>
                  <span className={`text-[10px] ${style.color}`}>{style.label}</span>
                </div>
                <p className="mt-0.5 text-[11px] text-slate-500">
                  conf {Math.round((agent.confidence || 0) * 100)}% · risk{" "}
                  {Math.round((agent.risk_score || 0) * 100)}%
                  {agent.duration_ms != null ? ` · ${Math.round(agent.duration_ms)}ms` : ""}
                </p>
                {(agent.reason || agent.error) && (
                  <p className="mt-1 line-clamp-2 text-[11px] text-slate-400">
                    {agent.reason || agent.error}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {calibration?.components && (
        <div className="mb-4 rounded-xl border border-[#1F2937] bg-[#0B1120]/60 p-3">
          <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-slate-500">
            Confidence Calibration
          </p>
          <div className="grid grid-cols-2 gap-1.5">
            {Object.entries(calibration.components).map(([k, v]) => (
              <div key={k} className="flex justify-between text-[11px] text-slate-400">
                <span className="capitalize">{k}</span>
                <span className="text-slate-200">{v}%</span>
              </div>
            ))}
          </div>
          <p className="mt-2 text-xs font-semibold text-cyan-300">
            Final Fraud Confidence: {calibration.final_percent}%
          </p>
        </div>
      )}

      {timeline.length > 0 && (
        <div>
          <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-slate-500">
            Investigation Timeline
          </p>
          <div className="max-h-40 space-y-1.5 overflow-y-auto pr-1">
            {timeline.map((ev, i) => (
              <div key={`${ev.stage}-${i}`} className="flex gap-2 text-[11px]">
                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-cyan-500/70" />
                <div>
                  <p className="text-slate-300">{ev.message}</p>
                  <p className="text-slate-600">{ev.agent || ev.stage}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}

export default AgentPipelinePanel;
