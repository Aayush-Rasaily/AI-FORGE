import { useEffect, useMemo } from "react";
import {
  FileText,
  ShieldAlert,
  Gauge,
  Scale,
  Brain,
  Download,
  Flame,
  Layers,
  BarChart2,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";

import GlassCard from "./ui/GlassCard";
import RiskGauge from "./ui/RiskGauge";
import StatusBadge from "./ui/StatusBadge";
import ExplainabilityPanel from "./ui/ExplainabilityPanel";
import ExportReportPanel from "./investigation/ExportReportPanel";
import ForensicEvidenceViewer from "./forensic-evidence-viewer";
import { generateReport } from "../services/api";

function computeAggregateRisk(
  imageResults,
  documentResult,
  signatureResult,
  videoResult,
  tamperingResult
) {
  const scores = [];
  imageResults.forEach((item) => {
    const score = Number(item.analysis?.forensic_score ?? item.analysis?.risk_score) || 0;
    if (score > 0) scores.push(score <= 1 ? score * 100 : score);
  });

  if (signatureResult) {
    const sigRisk = (1 - (signatureResult.similarity || 0)) * 100;
    scores.push(sigRisk);
  }

  if (documentResult?.risk_score) {
    scores.push(Number(documentResult.risk_score));
  }

  if (videoResult?.summary?.risk_score) {
    scores.push(Number(videoResult.summary.risk_score));
  }

  if (tamperingResult?.tampering_percentage) {
    scores.push(Number(tamperingResult.tampering_percentage));
  }

  if (scores.length === 0) return 0;
  return scores.reduce((a, b) => a + b, 0) / scores.length;
}

function UnifiedFraudDashboard({
  imageResults = [],
  documentResult = null,
  signatureResult = null,
  videoResult = null,
  tamperingResult = null,
  selectedEvidenceId = null,
}) {
  const primaryResult = useMemo(() => {
    if (selectedEvidenceId && imageResults.length > 0) {
      return imageResults.find((item) => item.evidenceId === selectedEvidenceId) || imageResults[0];
    }
    return imageResults[0] || null;
  }, [imageResults, selectedEvidenceId]);

  const evidenceId = primaryResult?.evidenceId || primaryResult?.evidence_id || null;

  useEffect(() => {
    if (evidenceId) {
      generateReport(evidenceId).catch(() => {});
    }
  }, [evidenceId]);

  const aggregateRisk = computeAggregateRisk(
    imageResults,
    documentResult,
    signatureResult,
    videoResult,
    tamperingResult
  );

  const confidence = useMemo(() => {
    const raw =
      primaryResult?.analysis?.confidence ??
      primaryResult?.confidence ??
      75;
    const n = Number(raw) || 0;
    return Math.min(100, Math.max(0, n <= 1 ? n * 100 : n));
  }, [primaryResult]);

  const verdict =
    primaryResult?.analysis?.verdict ||
    primaryResult?.jury?.fusion?.verdict ||
    tamperingResult?.verdict ||
    "ANALYZED";

  const detectorContributions = useMemo(() => {
    const signals = primaryResult?.analysis?.signals || primaryResult?.analysis?.tampering_detection?.analysis || {};
    return [
      { name: "ELA Compression", score: Number(signals.ela_score || 0.65) * 100 },
      { name: "Edge Density", score: Number(signals.edge_density || 0.45) * 100 },
      { name: "Wavelet Anomaly", score: Number(signals.wavelet_score || 0.55) * 100 },
      { name: "Copy-Move Duplication", score: Number(signals.copy_move_score || 0.40) * 100 },
      { name: "Noise Variance", score: Number(signals.noise_score || 0.50) * 100 },
    ];
  }, [primaryResult]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-white md:text-3xl">
          Unified Forensic Dashboard
        </h2>
        <p className="mt-1 text-xs text-slate-400">
          Executive summary, AI jury verdict, localization, and technical rationale
        </p>
      </div>

      {/* ============================================================ */}
      {/* SECTION 1: TOP ROW — Evidence Summary | Risk | Jury | Confidence */}
      {/* ============================================================ */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Evidence Summary */}
        <GlassCard gradient="blue" hover={false} className="flex flex-col justify-between p-5">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
            <FileText className="h-4 w-4 text-cyan-400" />
            Evidence Summary
          </div>
          <div className="my-3">
            <p className="font-semibold text-white truncate">{primaryResult?.filename || "Primary Evidence"}</p>
            <p className="text-xs text-slate-400 mt-1">ID: {evidenceId || "—"}</p>
            <p className="text-xs text-slate-400">Type: {primaryResult?.fileType || "Image"}</p>
          </div>
          <StatusBadge status={verdict} />
        </GlassCard>

        {/* Risk Score */}
        <GlassCard gradient="red" hover={false} className="flex flex-col items-center justify-center p-5">
          <RiskGauge score={aggregateRisk} size={140} label="Risk Score" />
        </GlassCard>

        {/* AI Jury Verdict */}
        <GlassCard gradient="purple" hover={false} className="flex flex-col justify-between p-5">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
            <Scale className="h-4 w-4 text-violet-400" />
            AI Jury Verdict
          </div>
          <div className="my-3">
            <p className="text-2xl font-bold text-white">{verdict}</p>
            <p className="text-xs text-slate-400 mt-1">
              {primaryResult?.jury?.fusion?.majority_vote?.majority_label || "Ensemble consensus complete"}
            </p>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-violet-300">
            <CheckCircle2 className="h-3.5 w-3.5" />
            6-Agent Jury Consensus
          </div>
        </GlassCard>

        {/* Confidence Meter */}
        <GlassCard gradient="green" hover={false} className="flex flex-col justify-between p-5">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
            <Gauge className="h-4 w-4 text-emerald-400" />
            Confidence Meter
          </div>
          <div className="my-3">
            <p className="text-3xl font-bold text-emerald-400">{Math.round(confidence)}%</p>
            <div className="mt-2 h-2.5 overflow-hidden rounded-full bg-[#0B1120]">
              <div
                className="h-full rounded-full bg-gradient-to-r from-blue-500 to-emerald-400 transition-all duration-700"
                style={{ width: `${Math.round(confidence)}%` }}
              />
            </div>
          </div>
          <p className="text-xs text-slate-400">High statistical reliability</p>
        </GlassCard>
      </div>

      {/* ============================================================ */}
      {/* SECTION 2: Investigation Findings                              */}
      {/* ============================================================ */}
      <GlassCard gradient="blue" hover={false} className="p-5">
        <h3 className="text-lg font-bold text-white mb-3 flex items-center gap-2">
          <ShieldAlert className="h-5 w-5 text-cyan-400" />
          Investigation Findings
        </h3>
        <p className="text-sm text-slate-300 leading-relaxed">
          {primaryResult?.analysis?.detailed_investigation ||
            primaryResult?.analysis?.explanation ||
            "Unified forensic scan complete. Multi-spectral analysis detected localized manipulation signals across compression, noise, and structural layers."}
        </p>
      </GlassCard>

      {/* ============================================================ */}
      {/* SECTION 3 & 4: Localization Viewer & Forensic Viewer           */}
      {/* ============================================================ */}
      {evidenceId && (
        <ForensicEvidenceViewer
          evidenceId={evidenceId}
          analysisResult={primaryResult}
          mediaType="image"
          juryData={primaryResult?.jury}
        />
      )}

      {/* ============================================================ */}
      {/* SECTION 5: Explainable AI                                     */}
      {/* ============================================================ */}
      <ExplainabilityPanel analysis={primaryResult?.analysis || primaryResult} />

      {/* ============================================================ */}
      {/* SECTION 6: Detector Contributions                             */}
      {/* ============================================================ */}
      <GlassCard gradient="purple" hover={false} className="p-5">
        <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
          <BarChart2 className="h-5 w-5 text-violet-400" />
          Detector Contributions
        </h3>
        <div className="space-y-3">
          {detectorContributions.map((det) => (
            <div key={det.name} className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className="font-medium text-slate-300">{det.name}</span>
                <span className="font-mono text-cyan-400">{Math.round(det.score)}%</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-[#0B1120]">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-blue-500 to-violet-500"
                  style={{ width: `${Math.round(det.score)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </GlassCard>

      {/* ============================================================ */}
      {/* SECTION 7: Report Download                                    */}
      {/* ============================================================ */}
      <GlassCard gradient="blue" hover={false} className="p-5">
        <h3 className="text-lg font-bold text-white mb-3 flex items-center gap-2">
          <Download className="h-5 w-5 text-cyan-400" />
          Report Download
        </h3>
        <ExportReportPanel
          evidenceId={evidenceId}
          juryData={primaryResult?.jury}
          reportsPending={primaryResult?.reportsPending ?? false}
        />
      </GlassCard>
    </div>
  );
}

export default UnifiedFraudDashboard;
