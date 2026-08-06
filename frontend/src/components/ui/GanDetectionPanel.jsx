import { motion } from "framer-motion";
import { Sparkles, Cpu, Brain, Radio, Zap } from "lucide-react";

import RiskGauge from "./RiskGauge";

const DETECTOR_ICONS = {
  cnn: Cpu,
  vit: Brain,
  clip: Sparkles,
  frequency: Radio,
};

function GeneratorBar({ label, score, delay = 0 }) {
  const pct = Math.min(100, Math.max(0, Number(score || 0) * 100));
  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay }}
      className="space-y-1"
    >
      <div className="flex justify-between text-xs">
        <span className="text-slate-400">{label}</span>
        <span className="font-mono text-violet-300">{pct.toFixed(1)}%</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-slate-800">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ delay: delay + 0.15, duration: 0.8 }}
          className="h-full rounded-full bg-gradient-to-r from-violet-500 to-fuchsia-400"
        />
      </div>
    </motion.div>
  );
}

function GanDetectionPanel({ ganDetection = {}, aiGeneration }) {
  const data = aiGeneration || ganDetection;
  const fusion = data.fusion || data;
  const detectors = data.detectors || {};
  const aiScore = Number(
    fusion.ai_generated_score ?? data.ai_generated_score ?? data.ai_generated_probability ?? 0
  ) * (data.ai_generated_probability != null && data.ai_generated_probability <= 1 ? 100 : 1);
  const humanPct = Number(data.human_photo_probability ?? (1 - (data.ai_generated_probability ?? aiScore / 100))) * 100;
  const confidence = Math.round(Number(fusion.confidence ?? data.confidence ?? 0) * (data.confidence <= 1 ? 100 : 1));
  const prediction = fusion.generator_prediction || data.generator_prediction || "Unknown";
  const reasoning = fusion.reasoning || data.reasoning || "";
  const generatorScores = fusion.generator_scores || data.generator_scores || {};

  if (!data || Object.keys(data).length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="overflow-hidden rounded-2xl border border-violet-500/20 bg-gradient-to-br from-violet-500/5 via-[#111827] to-fuchsia-500/5"
    >
      <div className="border-b border-violet-500/10 px-6 py-4">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-violet-400" />
          <h4 className="text-lg font-semibold text-white">AI Generator Detection</h4>
        </div>
        <p className="mt-1 text-xs text-slate-500">
          CNN · ViT · CLIP · Frequency fingerprints · GPU-accelerated
        </p>
      </div>

      <div className="grid gap-6 p-6 lg:grid-cols-2">
        <div className="flex flex-col items-center justify-center rounded-xl border border-violet-500/10 bg-[#0B1120]/60 p-6">
          <RiskGauge score={aiScore} size={180} label="AI-Generated Risk" />
          <div className="mt-4 text-center">
            <p className="text-xs uppercase tracking-widest text-violet-400">Generator Prediction</p>
            <p className="mt-1 text-xl font-bold text-white">{prediction}</p>
            <p className="mt-1 text-sm text-slate-400">Confidence: {confidence}%</p>
          </div>
        </div>

        <div className="space-y-5">
          <div>
            <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Model Detectors
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              {Object.entries(detectors).map(([key, det], i) => {
                const Icon = DETECTOR_ICONS[key] || Zap;
                return (
                  <div
                    key={key}
                    className="rounded-lg border border-[#1F2937] bg-[#0B1120] p-3"
                  >
                    <div className="flex items-center gap-2">
                      <Icon className="h-4 w-4 text-violet-400" />
                      <span className="text-xs font-medium uppercase text-slate-400">{key}</span>
                      <span className="ml-auto font-mono text-sm text-white">
                        {Math.round(Number(det.score || 0) * 100)}%
                      </span>
                    </div>
                    {det.explanation && (
                      <p className="mt-2 text-[11px] leading-relaxed text-slate-500 line-clamp-2">
                        {det.explanation}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {Object.keys(generatorScores).length > 0 && (
            <div>
              <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                Generator Likelihood
              </p>
              <div className="space-y-2">
                {Object.entries(generatorScores)
                  .sort(([, a], [, b]) => b - a)
                  .slice(0, 5)
                  .map(([name, score], i) => (
                    <GeneratorBar key={name} label={name} score={score} delay={i * 0.06} />
                  ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {reasoning && (
        <div className="border-t border-violet-500/10 px-6 py-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-violet-400">
            Explainability
          </p>
          <p className="mt-2 text-sm leading-relaxed text-slate-300">{reasoning}</p>
        </div>
      )}
    </motion.div>
  );
}

export default GanDetectionPanel;
