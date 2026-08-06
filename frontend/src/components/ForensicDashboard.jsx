import { motion } from "framer-motion";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import {
  Shield,
  AlertTriangle,
  Sparkles,
  Fingerprint,
  Brain,
  Clock,
} from "lucide-react";
import RiskGauge from "./ui/RiskGauge";

const SCORE_COLORS = ["#22c55e", "#f97316", "#ef4444", "#a855f7"];

function ScoreBar({ label, value, delay = 0 }) {
  const pct = Math.min(100, Math.max(0, Number(value) || 0));
  const color = pct >= 70 ? "#ef4444" : pct >= 45 ? "#f97316" : "#22c55e";
  return (
    <motion.div
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay }}
      className="space-y-1"
    >
      <div className="flex justify-between text-xs">
        <span className="text-slate-400">{label}</span>
        <span className="font-mono" style={{ color }}>{pct.toFixed(1)}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-800">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ delay: delay + 0.1, duration: 0.7 }}
          className="h-full rounded-full"
          style={{ background: color }}
        />
      </div>
    </motion.div>
  );
}

function ExplainCard({ text, index }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08 }}
      className="flex gap-3 rounded-xl border border-[#1F2937] bg-[#0B1120]/60 p-4"
    >
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
      <p className="text-sm leading-relaxed text-slate-300">{text}</p>
    </motion.div>
  );
}

/**
 * Interactive forensic dashboard — animated gauges, module scores, explainability.
 */
function ForensicDashboard({ analysis = {} }) {
  const fusion = analysis.risk_fusion || analysis.ensemble || {};
  const aiGen = analysis.ai_generation || analysis.gan_detection || {};
  const signals = analysis.signals || {};
  const timing = analysis.timing || {};

  const fraudRisk = fusion.overall_fraud_risk ?? analysis.risk_score ?? 0;
  const authenticity = fusion.authenticity_score ?? (100 - fraudRisk);
  const manipulation = fusion.manipulation_score ?? fraudRisk * 0.6;
  const aiScore = fusion.ai_generation_score
    ?? (aiGen.ai_generated_probability != null ? aiGen.ai_generated_probability * 100 : 0);
  const confidence = fusion.confidence ?? analysis.confidence ?? 0;
  const explainability = fusion.explainability || [];
  const verdict = fusion.verdict || analysis.verdict || "Unknown";

  const moduleScores = [
    { name: "ELA", value: (signals.ela_score || 0) * 100 },
    { name: "Wavelet", value: (signals.wavelet_score || 0) * 100 },
    { name: "Copy-Move", value: (signals.copy_move_score || 0) * 100 },
    { name: "Edge", value: (signals.edge_density || 0) * 100 },
    { name: "Metadata", value: (signals.metadata_risk_score || 0) * 100 },
    { name: "AI Gen", value: aiScore },
    { name: "Deepfake", value: (signals.deepfake_probability || 0) * 100 },
  ].filter((m) => m.value > 0);

  const timingEntries = Object.entries(timing)
    .filter(([k]) => !k.startsWith("_"))
    .slice(0, 8);

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6 rounded-2xl border border-cyan-500/20 bg-gradient-to-br from-[#111827] via-[#0B1120] to-blue-950/30 p-6 backdrop-blur-xl"
    >
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500/10">
            <Shield className="h-5 w-5 text-cyan-400" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Forensic Intelligence Dashboard</h3>
            <p className="text-xs text-slate-500">{verdict}</p>
          </div>
        </div>
        <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 px-4 py-2 text-center">
          <p className="text-[10px] uppercase tracking-wide text-cyan-400">Confidence</p>
          <p className="text-xl font-bold text-white">{Number(confidence).toFixed(1)}%</p>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="flex flex-col items-center rounded-xl border border-[#1F2937] bg-[#111827]/80 p-4">
          <RiskGauge score={fraudRisk} size={140} label="Fraud Risk" />
        </div>
        <div className="flex flex-col items-center rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
          <RiskGauge score={authenticity} size={140} label="Authenticity" invert />
        </div>
        <div className="flex flex-col items-center rounded-xl border border-orange-500/20 bg-orange-500/5 p-4">
          <RiskGauge score={manipulation} size={140} label="Manipulation" />
        </div>
        <div className="flex flex-col items-center rounded-xl border border-violet-500/20 bg-violet-500/5 p-4">
          <RiskGauge score={aiScore} size={140} label="AI Generation" />
        </div>
      </div>

      {aiGen.ai_generated_probability != null && (
        <div className="grid gap-3 rounded-xl border border-violet-500/20 bg-violet-500/5 p-4 sm:grid-cols-3">
          <div className="text-center">
            <Sparkles className="mx-auto h-4 w-4 text-violet-400" />
            <p className="mt-1 text-[10px] text-slate-500">AI Generated</p>
            <p className="text-lg font-bold text-violet-300">
              {(aiGen.ai_generated_probability * 100).toFixed(1)}%
            </p>
          </div>
          <div className="text-center">
            <Fingerprint className="mx-auto h-4 w-4 text-emerald-400" />
            <p className="mt-1 text-[10px] text-slate-500">Human Photo</p>
            <p className="text-lg font-bold text-emerald-300">
              {((aiGen.human_photo_probability ?? (1 - aiGen.ai_generated_probability)) * 100).toFixed(1)}%
            </p>
          </div>
          <div className="text-center">
            <Brain className="mx-auto h-4 w-4 text-fuchsia-400" />
            <p className="mt-1 text-[10px] text-slate-500">Synthetic Artifacts</p>
            <p className="text-lg font-bold text-fuchsia-300">
              {((aiGen.synthetic_artifact_confidence ?? 0) * 100).toFixed(1)}%
            </p>
          </div>
        </div>
      )}

      {moduleScores.length > 0 && (
        <div className="rounded-xl border border-[#1F2937] bg-[#111827]/60 p-4">
          <h4 className="mb-4 text-sm font-semibold text-white">Module Signal Strength</h4>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={moduleScores} layout="vertical" margin={{ left: 10, right: 20 }}>
                <XAxis type="number" domain={[0, 100]} tick={{ fill: "#64748b", fontSize: 10 }} />
                <YAxis type="category" dataKey="name" width={80} tick={{ fill: "#94a3b8", fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ background: "#111827", border: "1px solid #1F2937", borderRadius: 8 }}
                  formatter={(v) => [`${Number(v).toFixed(1)}%`, "Score"]}
                />
                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                  {moduleScores.map((entry, i) => (
                    <Cell key={entry.name} fill={SCORE_COLORS[i % SCORE_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {explainability.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-sm font-semibold text-white">Why This Verdict?</h4>
          {explainability.map((reason, i) => (
            <ExplainCard key={i} text={reason} index={i} />
          ))}
        </div>
      )}

      {timingEntries.length > 0 && (
        <div className="rounded-xl border border-[#1F2937] bg-[#111827]/60 p-4">
          <div className="mb-3 flex items-center gap-2">
            <Clock className="h-4 w-4 text-cyan-400" />
            <h4 className="text-sm font-semibold text-white">Analysis Timeline</h4>
          </div>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {timingEntries.map(([module, ms], i) => (
              <motion.div
                key={module}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: i * 0.05 }}
                className="rounded-lg bg-[#0B1120] px-3 py-2"
              >
                <p className="text-[10px] text-slate-500">{module.replace(/_/g, " ")}</p>
                <p className="font-mono text-sm text-cyan-300">
                  {typeof ms === "number" ? `${ms.toFixed(0)}ms` : String(ms)}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}

export default ForensicDashboard;
