import { motion } from "framer-motion";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
} from "recharts";
import { Users, Scale, AlertTriangle, ThumbsDown } from "lucide-react";

import RiskGauge from "../ui/RiskGauge";
import AgentCard from "./AgentCard";
import AgentDisagreement from "./AgentDisagreement";
import InvestigationReport from "./InvestigationReport";

const AGENT_META = {
  vision: { role: "ELA, copy-move, wavelet & visual forensics" },
  metadata: { role: "EXIF, GPS, thumbnail & metadata forensics" },
  ocr: { role: "OCR consensus, layout, font & document anomalies" },
  video: { role: "Keyframe & temporal video forensics" },
  gan: { role: "AI generator & diffusion model detection" },
  deepfake: { role: "Face forensics & deepfake probability" },
  signature: { role: "Signature verification & forgery detection" },
};

const RISK_COLORS = {
  CRITICAL: "text-red-400 border-red-500/40 bg-red-500/10",
  HIGH: "text-orange-400 border-orange-500/40 bg-orange-500/10",
  MEDIUM: "text-yellow-400 border-yellow-500/40 bg-yellow-500/10",
  LOW: "text-emerald-400 border-emerald-500/40 bg-emerald-500/10",
};

const VOTE_COLORS = ["#ef4444", "#22c55e", "#94a3b8"];

function ConfidenceDistributionChart({ distribution = {} }) {
  const data = Object.entries(distribution)
    .filter(([, v]) => !v.abstained)
    .map(([id, v]) => ({
      name: (v.agent_name || id).replace(" Agent", ""),
      confidence: v.confidence_pct ?? Math.round((v.confidence || 0) * 100),
      risk: v.risk_pct ?? Math.round((v.risk_score || 0) * 100),
      weight: Math.round((v.weight || 0) * 1000) / 10,
    }))
    .sort((a, b) => b.confidence - a.confidence);

  if (!data.length) return null;

  return (
    <div className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 9 }} interval={0} angle={-20} textAnchor="end" height={50} />
          <YAxis domain={[0, 100]} tick={{ fill: "#94a3b8", fontSize: 10 }} />
          <Tooltip
            contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }}
            formatter={(v, name) => [`${v}%`, name === "confidence" ? "Confidence" : "Risk"]}
          />
          <Bar dataKey="confidence" name="confidence" fill="#a78bfa" radius={[4, 4, 0, 0]} />
          <Bar dataKey="risk" name="risk" fill="#f97316" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function MajorityVoteChart({ majority = {} }) {
  const data = [
    { name: "Risk", value: majority.risk_votes || 0 },
    { name: "Authentic", value: majority.authentic_votes || 0 },
    { name: "Abstain", value: majority.abstained || 0 },
  ].filter((d) => d.value > 0);

  if (!data.length) return null;

  return (
    <div className="flex items-center gap-4">
      <div className="h-36 w-36">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              cx="50%"
              cy="50%"
              innerRadius={35}
              outerRadius={55}
              paddingAngle={3}
            >
              {data.map((_, i) => (
                <Cell key={i} fill={VOTE_COLORS[i % VOTE_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip contentStyle={{ background: "#111827", border: "1px solid #374151" }} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="space-y-2 text-sm">
        <p className="font-bold text-white">{majority.majority_label || "Pending"}</p>
        <p className="text-red-400">{majority.risk_votes || 0} risk votes</p>
        <p className="text-emerald-400">{majority.authentic_votes || 0} authentic votes</p>
        {majority.abstained > 0 && (
          <p className="text-slate-500">{majority.abstained} abstained</p>
        )}
        <p className="text-xs text-slate-500">Margin: {majority.margin ?? 0}</p>
      </div>
    </div>
  );
}

function JuryDashboard({ juryResult, agentIcons = {} }) {
  const fusion = juryResult?.fusion || {};
  const agents = juryResult?.agents || {};
  const majority = juryResult?.majority_vote || fusion.majority_vote || {};
  const minority = juryResult?.minority_opinion || fusion.minority_opinion || [];
  const distribution = juryResult?.confidence_distribution || fusion.confidence_distribution || {};
  const riskLevel = juryResult?.risk_level || fusion.risk_level || "LOW";
  const riskScore = Math.round(fusion.risk_score_pct ?? (fusion.risk_score || 0) * 100);
  const confidence = Math.round(fusion.confidence_pct ?? (fusion.confidence || 0) * 100);

  const agentOrder = ["vision", "metadata", "ocr", "video", "gan", "deepfake", "signature"];

  return (
    <div className="space-y-8">
      {/* Verdict header */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-2xl border border-purple-500/20 bg-gradient-to-br from-purple-500/5 to-[#111827] p-8"
      >
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs uppercase tracking-widest text-purple-400">
              AI Jury — 7 Independent Agents
            </p>
            <h3 className="mt-2 text-3xl font-bold text-white">
              {fusion.final_verdict || "Pending"}
            </h3>
            <div className="mt-3 flex flex-wrap gap-2">
              <span className={`rounded-full border px-3 py-1 text-xs font-bold ${RISK_COLORS[riskLevel] || RISK_COLORS.LOW}`}>
                {riskLevel} RISK
              </span>
              <span className="rounded-full border border-purple-500/30 bg-purple-500/10 px-3 py-1 text-xs text-purple-300">
                Weighted confidence {confidence}%
              </span>
            </div>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-slate-400">
              {juryResult?.reasoning || fusion.reasoning}
            </p>
          </div>
          <RiskGauge score={riskScore} size={170} label="Fraud Probability" />
        </div>
      </motion.div>

      {/* Majority + distribution */}
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-6">
          <div className="mb-4 flex items-center gap-2">
            <Users className="h-5 w-5 text-violet-400" />
            <h4 className="font-semibold text-white">Majority Vote</h4>
          </div>
          <MajorityVoteChart majority={majority} />
        </div>

        <div className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-6">
          <div className="mb-4 flex items-center gap-2">
            <Scale className="h-5 w-5 text-cyan-400" />
            <h4 className="font-semibold text-white">Confidence Distribution</h4>
          </div>
          <ConfidenceDistributionChart distribution={distribution} />
        </div>
      </div>

      {/* Minority opinion */}
      {minority.length > 0 && (
        <div className="rounded-2xl border border-amber-500/20 bg-amber-500/5 p-6">
          <div className="mb-4 flex items-center gap-2">
            <ThumbsDown className="h-5 w-5 text-amber-400" />
            <h4 className="font-semibold text-amber-300">
              Minority Opinion ({minority.length})
            </h4>
          </div>
          <div className="space-y-3">
            {minority.map((m, i) => (
              <div key={i} className="rounded-xl border border-amber-500/20 bg-[#0B1120] p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold text-white">{m.agent_name}</span>
                  <span className="text-xs text-amber-400">{m.verdict}</span>
                  <span className="font-mono text-xs text-slate-500">
                    {Math.round((m.confidence || 0) * 100)}% conf.
                  </span>
                </div>
                <p className="mt-2 text-sm text-amber-200/80">{m.opinion}</p>
                {m.why && <p className="mt-1 text-xs text-slate-500">{m.why}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Agent grid */}
      <div>
        <h4 className="mb-4 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
          <AlertTriangle className="h-4 w-4" />
          Independent Agent Votes
        </h4>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {agentOrder.map((id, i) => {
            const agent = agents[id];
            const meta = AGENT_META[id] || {};
            const Icon = agentIcons[id];
            if (!agent) return null;
            return (
              <AgentCard
                key={id}
                agent={agent}
                icon={Icon}
                role={meta.role}
                index={i}
              />
            );
          })}
        </div>
      </div>

      <AgentDisagreement disagreements={fusion.disagreements} />
      <InvestigationReport fusion={fusion} />
    </div>
  );
}

export default JuryDashboard;
