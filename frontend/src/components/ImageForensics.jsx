import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Scan,
  GitBranch,
  Waves,
  Copy,
  Fingerprint,
  Loader2,
  Palette,
  Grid3x3,
  Radio,
} from "lucide-react";

import ArtifactCard from "./ArtifactCard";
import RiskGauge from "./ui/RiskGauge";
import TamperingCard from "./ui/TamperingCard";
import ProgressCard from "./ui/ProgressCard";
import StatusBadge from "./ui/StatusBadge";
import GanDetectionPanel from "./ui/GanDetectionPanel";
import FaceForensicsPanel from "./ui/FaceForensicsPanel";
import MetadataForensicsPanel from "./ui/MetadataForensicsPanel";
import ExplainabilityPanel from "./ui/ExplainabilityPanel";
import { downloadPDF, getArtifactUrl, getUnifiedArtifactUrl, getArtifactsStatus } from "../services/api";
import { Download } from "lucide-react";
import ForensicViewer from "./ForensicViewer";
import ForensicDashboard from "./ForensicDashboard";

/* ========================================= */
/* Forensic report for a single evidence item */
/* ========================================= */

function ForensicReport({ item, index }) {
  const filename = item.filename || `Evidence ${index + 1}`;
  const evidenceId = item.evidenceId || item.evidence_id || "";
  const dashboard = item.dashboard || {};
  const juryData = item.jury || {};
  const juryFusion = juryData.fusion || juryData;
  const [analysis, setAnalysis] = useState(() => ({
    ...(item.analysis || {}),
    risk_score: item.risk ?? item.analysis?.risk_score,
    confidence: item.confidence ?? item.analysis?.confidence,
    verdict: item.analysis?.verdict || dashboard.verdict,
    explanation: item.analysis?.explanation || dashboard.explanation,
    recommendation: item.analysis?.recommendation || dashboard.recommendation,
  }));
  const [artifactsPending, setArtifactsPending] = useState(
    item.artifactsPending ?? false
  );
  const [reportsPending, setReportsPending] = useState(item.reportsPending ?? true);
  const [reportDownloading, setReportDownloading] = useState(false);
  const [reportError, setReportError] = useState("");
  const tampering = item.tampering || {};
  const signals = analysis.signals || {};
  const multispectral = analysis.multispectral || {};
  const spectralFusion = multispectral.fusion || {};
  const spectralDetectors = multispectral.detectors || {};
  const ganDetection = analysis.ai_generation || analysis.gan_detection || {};
  const faceForensics = analysis.face_forensics || {};
  const metadataForensics = analysis.metadata_forensics || {};
  const explainability = analysis.explainability || {};
  const artifacts = { ...(item.artifacts || {}), ...(analysis.artifacts || {}) };

  const riskScore = Math.min(
    100,
    Math.max(Number(item.risk ?? analysis.risk_score ?? dashboard.risk_score ?? 0), 0)
  );
  const verdict = analysis.verdict || dashboard.verdict || "Unknown";
  const scanMode = analysis.scan_mode || item.scanMode;

  useEffect(() => {
    setAnalysis({
      ...(item.analysis || {}),
      risk_score: item.risk ?? item.analysis?.risk_score,
      confidence: item.confidence ?? item.analysis?.confidence,
      verdict: item.analysis?.verdict || dashboard.verdict,
      explanation: item.analysis?.explanation || dashboard.explanation,
      recommendation: item.analysis?.recommendation || dashboard.recommendation,
      artifacts: { ...(item.artifacts || {}), ...(item.analysis?.artifacts || {}) },
    });
    setArtifactsPending(item.artifactsPending ?? false);
    setReportsPending(item.reportsPending ?? true);
  }, [item, dashboard.verdict, dashboard.explanation, dashboard.recommendation]);

  useEffect(() => {
    if (!artifactsPending || !evidenceId) return undefined;

    let cancelled = false;
    let attempts = 0;
    const maxAttempts = 12;

    const poll = async () => {
      if (cancelled || attempts >= maxAttempts) {
        if (attempts >= maxAttempts) setArtifactsPending(false);
        return;
      }
      attempts += 1;
      try {
        const status = await getArtifactsStatus(evidenceId);
        if (cancelled) return;
        if (status.status === "ready" && status.artifacts) {
          setArtifactsPending(false);
          setAnalysis((prev) => ({
            ...prev,
            artifacts: { ...(prev.artifacts || {}), ...status.artifacts },
            artifacts_pending: false,
          }));
        }
      } catch {
        /* retry */
      }
    };

    poll();
    const interval = setInterval(poll, 2500);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [artifactsPending, evidenceId]);

  useEffect(() => {
    if (!reportsPending || !evidenceId) return undefined;

    let cancelled = false;
    let attempts = 0;
    const maxAttempts = 10;

    const poll = async () => {
      if (cancelled || attempts >= maxAttempts) {
        if (attempts >= maxAttempts) setReportsPending(false);
        return;
      }
      attempts += 1;
      try {
        const { getReportStatus, generateReport } = await import("../services/api");
        if (attempts === 1) await generateReport(evidenceId);
        const status = await getReportStatus(evidenceId);
        if (cancelled) return;
        if (status.status === "completed" || status.report_ready || status.ready) {
          setReportsPending(false);
        } else if (status.status === "failed") {
          setReportsPending(false);
        }
      } catch {
        /* retry */
      }
    };

    poll();
    const interval = setInterval(poll, 800);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [reportsPending, evidenceId]);

  const moduleScores = [
    {
      icon: Scan,
      title: "ELA",
      score: Number(signals.ela_score || 0) * 100,
    },
    {
      icon: GitBranch,
      title: "Edge Detection",
      score: Number(signals.edge_density || 0) * 100,
    },
    {
      icon: Waves,
      title: "Wavelet",
      score: Number(signals.wavelet_score || 0) * 100,
    },
    {
      icon: Copy,
      title: "Copy-Move",
      score: Number(signals.copy_move_score || 0) * 100,
    },
  ];

  const spectralScores = [
    { icon: Palette, title: "RGB", key: "rgb" },
    { icon: Palette, title: "HSV", key: "hsv" },
    { icon: Palette, title: "LAB", key: "lab" },
    { icon: Palette, title: "YCbCr", key: "ycbcr" },
    { icon: Radio, title: "Frequency", key: "frequency" },
    { icon: Grid3x3, title: "JPEG Block", key: "jpeg_block" },
  ].map((mod) => ({
    ...mod,
    score: Number(
      spectralDetectors[mod.key]?.score ??
        signals[`${mod.key}_score`] ??
        0
    ) * 100,
    explanation: spectralDetectors[mod.key]?.explanation || "",
  }));

  const artifactUrl = (type) => {
    const fromAnalysis = artifacts[type];
    if (fromAnalysis) return getArtifactUrl(fromAnalysis);
    if (evidenceId) return getUnifiedArtifactUrl(evidenceId, type);
    return "";
  };

  const artifactItems = [
    { key: "ela", title: "Error Level Analysis", description: "Compression anomaly heatmap" },
    { key: "edges", title: "Edge Detection", description: "Structural boundary overlay" },
    { key: "wavelet", title: "Wavelet Analysis", description: "Frequency manipulation map" },
    { key: "copy_move", title: "Copy-Move Detection", description: "Matched keypoint visualization" },
  ].map((item) => ({
    ...item,
    url: artifactUrl(item.key),
  }));

  const explanation = analysis.explanation || analysis.recommendation || "";

  const handleDownloadPdf = async () => {
    if (!evidenceId || reportDownloading) return;
    setReportDownloading(true);
    setReportError("");
    try {
      await downloadPDF(evidenceId, "full");
    } catch (err) {
      setReportError(err.message || "Unable to generate report.");
    } finally {
      setReportDownloading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, duration: 0.5 }}
      className="space-y-8"
    >
      {/* Header */}
      <div className="flex flex-col gap-4 rounded-2xl border border-[#1F2937] bg-[#111827] p-6 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-500/10 border border-blue-500/20">
            <Fingerprint className="h-6 w-6 text-blue-400" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-white">{filename}</h3>
            {evidenceId && (
              <p className="mt-0.5 font-mono text-xs text-slate-500">
                {evidenceId}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3">
          {evidenceId && (
            <button
              type="button"
              onClick={handleDownloadPdf}
              disabled={reportDownloading}
              className="flex items-center gap-2 rounded-xl border border-cyan-500/30 bg-cyan-500/10 px-4 py-2 text-sm font-medium text-cyan-400 transition hover:bg-cyan-500/20 disabled:opacity-50"
            >
              {reportDownloading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Download className="h-4 w-4" />
              )}
              {reportDownloading ? "Generating…" : "Export PDF"}
            </button>
          )}
          <StatusBadge status={verdict} />
        </div>
      </div>

      {reportError && (
        <p className="text-sm text-red-400">{reportError}</p>
      )}

      {artifactsPending && (
        <div className="flex items-center gap-3 rounded-xl border border-cyan-500/20 bg-cyan-500/5 px-4 py-3 text-sm text-cyan-200 backdrop-blur-sm">
          <Loader2 className="h-4 w-4 shrink-0 animate-spin" />
          <span>Generating forensic visualizations… Images load automatically when ready.</span>
        </div>
      )}

      <ForensicDashboard analysis={{ ...analysis, risk_fusion: analysis.risk_fusion || dashboard.risk_fusion, jury: juryData }} />

      {juryFusion?.verdict && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-2xl border border-violet-500/20 bg-violet-500/5 p-6"
        >
          <h4 className="text-sm font-semibold uppercase tracking-wide text-violet-400">AI Jury Verdict</h4>
          <p className="mt-2 text-xl font-bold text-white">{juryFusion.verdict || juryFusion.final_verdict}</p>
          {juryFusion.confidence != null && (
            <p className="mt-1 text-sm text-slate-400">Confidence: {Number(juryFusion.confidence).toFixed(1)}%</p>
          )}
          {juryFusion.majority_opinion && (
            <p className="mt-3 text-sm leading-relaxed text-slate-300">{juryFusion.majority_opinion}</p>
          )}
        </motion.div>
      )}

      {item.processingTime > 0 && (
        <p className="text-xs text-slate-500">
          Processing time: {(item.processingTime / 1000).toFixed(1)}s
          {reportsPending &&
            " · Generating professional forensic report… Estimated time: 3–5 seconds"}
        </p>
      )}

      {explanation && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-2xl border border-[#1F2937] bg-gradient-to-br from-[#111827]/90 to-[#0B1120]/90 p-6 backdrop-blur-md"
        >
          <h4 className="text-sm font-semibold uppercase tracking-wide text-cyan-400">
            AI Forensic Explanation
          </h4>
          <p className="mt-3 text-sm leading-relaxed text-slate-300">{explanation}</p>
        </motion.div>
      )}

      {evidenceId && artifactUrl("ela") && (
        <ForensicViewer
          title="Interactive Forensic Viewer"
          originalUrl={getUnifiedArtifactUrl(evidenceId, "ela")}
          overlayUrl={getUnifiedArtifactUrl(evidenceId, "ela")}
          overlayLabel="ELA Heatmap"
        />
      )}

      {/* Overall Risk Gauge */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.15 }}
        className="flex flex-col items-center rounded-2xl border border-[#1F2937] bg-gradient-to-br from-[#111827] to-[#0B1120] p-8 shadow-xl"
      >
        <RiskGauge score={riskScore} size={220} label="Overall Risk" />
      </motion.div>

      {/* Module Scores */}
      <div>
        <h4 className="mb-4 text-lg font-semibold text-white">Module Scores</h4>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {moduleScores.map((mod, i) => (
            <ProgressCard
              key={mod.title}
              icon={mod.icon}
              title={mod.title}
              score={mod.score}
              delay={i * 0.1}
            />
          ))}
        </div>
      </div>

      {(analysis.scan_mode === "deep" || spectralFusion.overall_score != null) && (
        <div>
          <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <h4 className="text-lg font-semibold text-white">Multi-Spectral Analysis</h4>
            {spectralFusion.overall_score_pct != null && (
              <p className="text-sm text-cyan-300">
                Fusion score: {spectralFusion.overall_score_pct}% · confidence{" "}
                {Math.round(Number(spectralFusion.confidence || 0) * 100)}%
              </p>
            )}
          </div>
          {spectralFusion.reasoning && (
            <p className="mb-4 text-sm leading-relaxed text-slate-400">
              {spectralFusion.reasoning}
            </p>
          )}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {spectralScores.map((mod, i) => (
              <ProgressCard
                key={mod.title}
                icon={mod.icon}
                title={mod.title}
                score={mod.score}
                delay={i * 0.08}
                subtitle={mod.explanation}
              />
            ))}
          </div>
        </div>
      )}

      {(analysis.scan_mode === "deep" || analysis.ai_generation) && Object.keys(ganDetection).length > 0 && (
        <GanDetectionPanel ganDetection={ganDetection} aiGeneration={analysis.ai_generation} />
      )}

      {analysis.scan_mode === "deep" && Object.keys(faceForensics).length > 0 && (
        <FaceForensicsPanel faceForensics={faceForensics} evidenceId={evidenceId} />
      )}

      {Object.keys(metadataForensics).length > 0 && (
        <MetadataForensicsPanel metadataForensics={metadataForensics} />
      )}

      {explainability.success !== false && Object.keys(explainability).length > 0 && (
        <ExplainabilityPanel explainability={explainability} />
      )}

      {/* Tampering Detection */}
      {Object.keys(tampering).length > 0 && (
        <TamperingCard tampering={tampering} />
      )}

      {/* Copy-Move Details */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="rounded-2xl border border-[#1F2937] bg-[#111827] p-6"
      >
        <h4 className="text-lg font-semibold text-white mb-4">
          Copy-Move Details
        </h4>
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-[#1F2937] bg-[#0B1120] p-4">
            <p className="text-xs text-slate-500">Detection Status</p>
            <p
              className={`mt-2 font-semibold ${
                signals.copy_move_detected
                  ? "text-red-400"
                  : "text-emerald-400"
              }`}
            >
              {signals.copy_move_detected
                ? "Duplicate Region Detected"
                : "No Duplicate Detected"}
            </p>
          </div>
          <div className="rounded-xl border border-[#1F2937] bg-[#0B1120] p-4">
            <p className="text-xs text-slate-500">Matched Points</p>
            <p className="mt-2 text-2xl font-bold text-white">
              {signals.matched_points || 0}
            </p>
          </div>
          <div className="rounded-xl border border-[#1F2937] bg-[#0B1120] p-4">
            <p className="text-xs text-slate-500">RANSAC Inliers</p>
            <p className="mt-2 text-2xl font-bold text-white">
              {signals.ransac_inliers || 0}
            </p>
          </div>
        </div>
      </motion.div>

      {/* Forensic Artifacts */}
      <div>
        <h4 className="mb-2 text-lg font-semibold text-white">
          Forensic Visualizations
        </h4>
        <p className="mb-6 text-sm text-slate-500">
          Visual artifacts generated during analysis. Hover to zoom, download, or view fullscreen.
        </p>
        <div className="grid gap-6 sm:grid-cols-2">
          {artifactItems.map((art) => (
            <ArtifactCard
              key={art.key}
              title={art.title}
              description={art.description}
              artifactUrl={art.url}
            />
          ))}
        </div>
      </div>
    </motion.div>
  );
}

/* ========================================= */
/* Main ImageForensics component             */
/* ========================================= */

function ImageForensics({ results = [] }) {
  if (!results || results.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="mt-10 rounded-2xl border border-[#1F2937] bg-[#111827]/60 p-12 text-center backdrop-blur-sm"
      >
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-800">
          <Scan className="h-6 w-6 text-slate-500" />
        </div>
        <h2 className="text-xl font-semibold text-slate-300">
          Forensic Analysis Report
        </h2>
        <p className="mt-2 text-sm text-slate-500">
          Upload and analyze an image to generate a forensic report.
        </p>
      </motion.div>
    );
  }

  return (
    <div className="mt-10 space-y-12">
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h2 className="text-3xl font-bold text-white">
          Forensic Analysis Report
        </h2>
        <p className="mt-2 text-slate-400">
          AI-powered multimodal forensic investigation results.
        </p>
      </motion.div>

      {results.map((item, index) => (
        <ForensicReport
          key={item.evidenceId || index}
          item={item}
          index={index}
        />
      ))}
    </div>
  );
}

export default ImageForensics;
