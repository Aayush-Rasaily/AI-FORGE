import { motion } from "framer-motion";
import { ScanFace, Eye, Sun, Sparkles, Activity, Smile } from "lucide-react";

import RiskGauge from "./RiskGauge";
import { getArtifactUrl } from "../../services/api";

const CHECK_META = {
  eye_blink: { icon: Eye, label: "Eye Blink" },
  head_pose: { icon: Activity, label: "Head Pose" },
  skin_texture: { icon: ScanFace, label: "Skin Texture" },
  lighting: { icon: Sun, label: "Lighting" },
  reflection: { icon: Sparkles, label: "Reflection" },
  emotion: { icon: Smile, label: "Emotion" },
};

function FaceForensicsPanel({ faceForensics = {}, evidenceId = "" }) {
  if (!faceForensics || Object.keys(faceForensics).length === 0) return null;

  const deepfakePct = Math.round(Number(faceForensics.deepfake_probability || 0) * 100);
  const authPct = Math.round(
    Number(faceForensics.face_authenticity_pct ?? (faceForensics.face_authenticity_score || 1) * 100)
  );
  const confidence = Math.round(Number(faceForensics.confidence || 0) * 100);
  const verdict = faceForensics.verdict || "Unknown";
  const reasoning = faceForensics.reasoning || faceForensics.explanation || "";
  const findings = faceForensics.findings || [];
  const facesDetected = faceForensics.faces_detected ?? 0;

  const heatmapPath = faceForensics.heatmap || faceForensics.artifacts?.heatmap;
  const heatmapUrl = heatmapPath ? getArtifactUrl(heatmapPath) : null;

  const consistencyChecks =
    faceForensics.face_analyses?.[0]?.models?.consistency?.checks || {};

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="overflow-hidden rounded-2xl border border-red-500/20 bg-gradient-to-br from-red-500/5 via-[#111827] to-orange-500/5"
    >
      <div className="border-b border-red-500/10 px-6 py-4">
        <div className="flex items-center gap-2">
          <ScanFace className="h-5 w-5 text-red-400" />
          <h4 className="text-lg font-semibold text-white">Face Forensics</h4>
        </div>
        <p className="mt-1 text-xs text-slate-500">
          FaceForensics++ · XceptionNet · MesoNet · Consistency Analysis
        </p>
      </div>

      <div className="grid gap-6 p-6 lg:grid-cols-3">
        <div className="flex flex-col items-center rounded-xl border border-red-500/10 bg-[#0B1120]/60 p-6">
          <RiskGauge score={deepfakePct} size={160} label="Deepfake Risk" />
          <p className="mt-3 text-xs text-slate-500">{facesDetected} face(s) analyzed</p>
        </div>

        <div className="flex flex-col items-center rounded-xl border border-emerald-500/10 bg-[#0B1120]/60 p-6">
          <RiskGauge score={authPct} size={160} label="Face Authenticity" invert />
          <p className="mt-3 text-center text-sm font-semibold text-white">{verdict}</p>
          <p className="mt-1 text-xs text-slate-500">Confidence: {confidence}%</p>
        </div>

        {heatmapUrl ? (
          <div className="rounded-xl border border-[#1F2937] bg-[#0B1120] p-3">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Visual Heatmap
            </p>
            <img
              src={heatmapUrl}
              alt="Face forensics heatmap"
              className="w-full rounded-lg object-contain"
            />
          </div>
        ) : (
          <div className="flex items-center justify-center rounded-xl border border-dashed border-[#1F2937] bg-[#0B1120]/40 p-6 text-center text-sm text-slate-500">
            {facesDetected === 0
              ? "No faces detected for heatmap generation"
              : "Heatmap generating…"}
          </div>
        )}
      </div>

      {Object.keys(consistencyChecks).length > 0 && (
        <div className="border-t border-red-500/10 px-6 py-4">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
            Consistency Checks
          </p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {Object.entries(consistencyChecks).map(([key, check]) => {
              const meta = CHECK_META[key] || { icon: ScanFace, label: key };
              const Icon = meta.icon;
              const score = Math.round(Number(check.score || 0) * 100);
              const risky = score >= 40;
              return (
                <div
                  key={key}
                  className={`rounded-lg border p-3 ${
                    risky ? "border-red-500/30 bg-red-500/5" : "border-[#1F2937] bg-[#0B1120]"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <Icon className={`h-4 w-4 ${risky ? "text-red-400" : "text-emerald-400"}`} />
                    <span className="text-sm text-white">{meta.label}</span>
                    <span className={`ml-auto text-xs font-mono ${risky ? "text-red-300" : "text-emerald-300"}`}>
                      {score}%
                    </span>
                  </div>
                  {check.explanation && (
                    <p className="mt-2 text-[11px] leading-relaxed text-slate-500 line-clamp-2">
                      {check.explanation}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {reasoning && (
        <div className="border-t border-red-500/10 px-6 py-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-red-400">
            Explainability
          </p>
          <p className="mt-2 text-sm leading-relaxed text-slate-300">{reasoning}</p>
        </div>
      )}

      {findings.length > 0 && (
        <div className="border-t border-red-500/10 px-6 py-4">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
            Detection Signals
          </p>
          <div className="space-y-2">
            {findings.slice(0, 6).map((f, i) => (
              <div key={i} className="rounded-lg border border-[#1F2937] bg-[#0B1120] px-4 py-3">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] uppercase text-red-400">{f.type}</span>
                  {f.score != null && (
                    <span className="text-[10px] text-slate-500">{Math.round(f.score * 100)}%</span>
                  )}
                </div>
                <p className="mt-1 text-sm text-slate-300">{f.what}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}

export default FaceForensicsPanel;
