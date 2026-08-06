import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  Brain,
  Eye,
  Layers,
  GitBranch,
  Sparkles,
  FileText,
  Link2,
  MapPin,
  AlertTriangle,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

import { getArtifactUrl } from "../../services/api";

const METHOD_TABS = [
  { id: "fused", label: "Fused Overlay", icon: Layers },
  { id: "gradcam", label: "GradCAM", icon: Eye },
  { id: "attention", label: "Attention", icon: Sparkles },
  { id: "shap", label: "SHAP", icon: GitBranch },
  { id: "lime", label: "LIME", icon: Brain },
];

const BAR_COLORS = ["#22d3ee", "#a78bfa", "#f97316", "#ef4444", "#eab308", "#34d399"];

function ConfidenceGraph({ graph = {} }) {
  const data = useMemo(() => {
    return (graph.nodes || [])
      .filter((n) => n.id !== "ensemble")
      .map((n) => ({
        name: n.label || n.id,
        score: Math.round(Number(n.score || 0) * 100),
        confidence: Math.round(Number(n.confidence || 0) * 100),
        why: n.why || "",
      }))
      .sort((a, b) => b.score - a.score)
      .slice(0, 10);
  }, [graph]);

  if (!data.length) return null;

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16 }}>
          <XAxis type="number" domain={[0, 100]} tick={{ fill: "#94a3b8", fontSize: 10 }} />
          <YAxis
            type="category"
            dataKey="name"
            width={90}
            tick={{ fill: "#94a3b8", fontSize: 10 }}
          />
          <Tooltip
            contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }}
            formatter={(v, name) => [`${v}%`, name === "score" ? "Risk" : "Confidence"]}
            labelFormatter={(label) => label}
          />
          <Bar dataKey="score" radius={[0, 4, 4, 0]}>
            {data.map((_, i) => (
              <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function ExplainabilityPanel({ explainability = {} }) {
  const [activeTab, setActiveTab] = useState("fused");

  if (!explainability || Object.keys(explainability).length === 0) return null;

  const artifacts = explainability.artifacts || {};
  const methods = explainability.forensic_report?.methods || {
    gradcam: explainability.gradcam,
    attention: explainability.attention,
    shap: explainability.shap,
    lime: explainability.lime,
  };

  const tabImages = {
    fused: artifacts.fused_overlay || artifacts.boxed_regions,
    gradcam: artifacts.gradcam_overlay,
    attention: artifacts.attention_overlay,
    shap: artifacts.shap_overlay,
    lime: artifacts.lime_overlay,
  };

  const activeImage = tabImages[activeTab];
  const activeMethod = methods[activeTab] || explainability[activeTab];
  const evidenceChain = explainability.evidence_chain || [];
  const predictions = explainability.predictions || [];
  const suspiciousRegions = explainability.suspicious_regions || [];
  const confidenceGraph = explainability.confidence_graph || {};

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="overflow-hidden rounded-2xl border border-indigo-500/20 bg-gradient-to-br from-indigo-500/5 via-[#111827] to-violet-500/5"
    >
      <div className="border-b border-indigo-500/10 px-6 py-4">
        <div className="flex items-center gap-2">
          <Brain className="h-5 w-5 text-indigo-400" />
          <h4 className="text-lg font-semibold text-white">Explainable AI Forensics</h4>
        </div>
        <p className="mt-1 text-xs text-slate-500">
          GradCAM · Attention Maps · SHAP · LIME · Every prediction explains WHY
        </p>
      </div>

      <div className="grid gap-6 p-6 lg:grid-cols-2">
        {/* Overlay viewer */}
        <div>
          <div className="mb-3 flex flex-wrap gap-2">
            {METHOD_TABS.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                    activeTab === tab.id
                      ? "bg-indigo-500/20 text-indigo-300 ring-1 ring-indigo-500/40"
                      : "bg-slate-800 text-slate-400 hover:bg-slate-700"
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {tab.label}
                </button>
              );
            })}
          </div>

          <div className="overflow-hidden rounded-xl border border-slate-800 bg-black">
            {activeImage ? (
              <img
                src={getArtifactUrl(activeImage)}
                alt={`${activeTab} overlay`}
                className="max-h-[400px] w-full object-contain"
              />
            ) : (
              <div className="flex h-48 items-center justify-center text-sm text-slate-500">
                Overlay not available for {activeTab}
              </div>
            )}
          </div>

          {activeMethod?.why && (
            <div className="mt-3 rounded-lg border border-indigo-500/20 bg-indigo-500/5 p-3">
              <p className="text-xs font-semibold uppercase tracking-wider text-indigo-400">Why</p>
              <p className="mt-1 text-sm leading-relaxed text-slate-300">{activeMethod.why}</p>
            </div>
          )}

          {suspiciousRegions.length > 0 && activeTab === "fused" && (
            <div className="mt-3 space-y-2">
              <p className="text-xs font-semibold text-slate-500">Suspicious Regions</p>
              {suspiciousRegions.slice(0, 4).map((r, i) => (
                <div key={i} className="flex items-center gap-2 text-xs text-slate-400">
                  <MapPin className="h-3 w-3 text-red-400" />
                  R{i + 1}: {JSON.stringify(r.bbox)} — {Math.round((r.confidence || 0) * 100)}%
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Confidence graph + report */}
        <div className="space-y-4">
          <div className="rounded-xl border border-slate-800 bg-[#0B1120] p-4">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Confidence Graph
            </p>
            <ConfidenceGraph graph={confidenceGraph} />
          </div>

          {explainability.human_readable_report && (
            <div className="rounded-xl border border-slate-800 bg-[#0B1120] p-4">
              <div className="mb-2 flex items-center gap-2">
                <FileText className="h-4 w-4 text-cyan-400" />
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Human-Readable Report
                </p>
              </div>
              <pre className="max-h-40 overflow-y-auto whitespace-pre-wrap text-xs leading-relaxed text-slate-400">
                {explainability.human_readable_report}
              </pre>
            </div>
          )}
        </div>
      </div>

      {/* Evidence chain */}
      {evidenceChain.length > 0 && (
        <div className="border-t border-indigo-500/10 px-6 py-5">
          <div className="mb-4 flex items-center gap-2">
            <Link2 className="h-4 w-4 text-violet-400" />
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Evidence Chain — Every Step Explains WHY
            </p>
          </div>
          <div className="space-y-3">
            {evidenceChain.slice(0, 10).map((step) => (
              <div
                key={step.step}
                className="flex gap-3 rounded-lg border border-slate-800 bg-slate-950/60 p-3"
              >
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-indigo-500/20 text-xs font-bold text-indigo-300">
                  {step.step}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-semibold text-white">{step.module}</span>
                    <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-500">
                      {step.stage}
                    </span>
                    {step.score != null && (
                      <span className="font-mono text-xs text-cyan-400">
                        {Math.round(Number(step.score) * 100)}%
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-xs leading-relaxed text-slate-400">{step.why}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Predictions with WHY */}
      {predictions.length > 0 && (
        <div className="border-t border-indigo-500/10 px-6 py-5">
          <div className="mb-3 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-400" />
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Predictions with Explanations
            </p>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            {predictions.slice(0, 8).map((pred, i) => (
              <div key={i} className="rounded-lg border border-slate-800 bg-slate-950 p-3">
                <p className="text-sm font-medium text-white">{pred.prediction}</p>
                <p className="mt-1 text-[11px] text-slate-500">{pred.module}</p>
                <p className="mt-2 text-xs text-slate-400">{pred.why}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}

export default ExplainabilityPanel;
