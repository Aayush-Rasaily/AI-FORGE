import {
  Boxes,
  Smile,
  Type,
  PenLine,
  Database,
  Percent,
  Activity,
} from "lucide-react";

function Stat({ icon: Icon, label, value, tone = "text-slate-200" }) {
  return (
    <div className="rounded-xl border border-[#1F2937] bg-[#0B1120]/70 p-3">
      <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-slate-500">
        <Icon className="h-3 w-3" />
        {label}
      </div>
      <p className={`mt-1.5 text-lg font-semibold tabular-nums ${tone}`}>{value}</p>
    </div>
  );
}

function InvestigationStatsPanel({ panel, analysisResult }) {
  const p = panel || {};
  const analysis = analysisResult?.analysis || analysisResult || {};

  const objects = p.detected_objects ?? analysis.objects?.length ?? "—";
  const faces = p.detected_faces ?? analysis.faces?.length ?? "—";
  const text = p.detected_text_regions ?? "—";
  const modified = p.modified_areas ?? "—";
  const meta = p.metadata_changes ? "Changed" : p.metadata_changes === false ? "Stable" : "—";
  const forgery = p.forgery_probability != null ? `${p.forgery_probability}%` : "—";
  const detConf = p.detector_confidence != null ? `${p.detector_confidence}%` : "—";

  const forgeryTone =
    Number(p.forgery_probability) >= 70
      ? "text-red-400"
      : Number(p.forgery_probability) >= 40
        ? "text-orange-400"
        : "text-emerald-400";

  return (
    <div className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-5">
      <div className="mb-3 flex items-center gap-2">
        <Activity className="h-4 w-4 text-cyan-400" />
        <h3 className="text-sm font-semibold text-white">Investigation Panel</h3>
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
        <Stat icon={Boxes} label="Detected Objects" value={objects} />
        <Stat icon={Smile} label="Detected Faces" value={faces} />
        <Stat icon={Type} label="Detected Text" value={text} />
        <Stat icon={PenLine} label="Modified Areas" value={modified} />
        <Stat icon={Database} label="Metadata Changes" value={meta} />
        <Stat icon={Percent} label="Forgery Probability" value={forgery} tone={forgeryTone} />
        <Stat icon={Activity} label="Detector Confidence" value={detConf} />
      </div>
      {Array.isArray(p.layers_active) && p.layers_active.length > 0 && (
        <p className="mt-3 text-[11px] text-slate-500">
          Active detectors: {p.layers_active.join(" · ")}
        </p>
      )}
    </div>
  );
}

export default InvestigationStatsPanel;
