import { AlertTriangle } from "lucide-react";

function AgentDisagreement({ disagreements = [] }) {
  if (!disagreements.length) {
    return (
      <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-5">
        <p className="text-sm text-emerald-400">
          All agents reached consistent conclusions.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <h4 className="flex items-center gap-2 text-sm font-semibold text-amber-400">
        <AlertTriangle className="h-4 w-4" />
        Agent Disagreements ({disagreements.length})
      </h4>
      {disagreements.map((d, i) => (
        <div
          key={i}
          className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4"
        >
          <p className="text-xs font-semibold text-amber-300">{d.issue}</p>
          <p className="mt-1 text-xs text-slate-400">{d.details}</p>
          {d.agents?.length > 0 && (
            <p className="mt-2 text-[10px] text-slate-500">
              Involved: {d.agents.join(", ")}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

export default AgentDisagreement;
