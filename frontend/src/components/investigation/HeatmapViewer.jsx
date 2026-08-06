import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Layers,
  Loader2,
  AlertCircle,
  Columns2,
  Image as ImageIcon,
} from "lucide-react";

import {
  generateAttentionHeatmap,
  getHeatmapArtifactUrl,
  getApiBaseUrl,
} from "../../services/api";

function HeatmapViewer({ evidenceId, filename }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [opacity, setOpacity] = useState(0.55);
  const [viewMode, setViewMode] = useState("overlay"); // overlay | side-by-side | heatmap

  const runHeatmap = useCallback(async () => {
    if (!evidenceId) return;
    setLoading(true);
    setError("");
    try {
      const data = await generateAttentionHeatmap(evidenceId);
      setResult(data);
    } catch (err) {
      setError(err.message || "Heatmap generation failed.");
    } finally {
      setLoading(false);
    }
  }, [evidenceId]);

  useEffect(() => {
    runHeatmap();
  }, [runHeatmap]);

  if (!evidenceId) {
    return (
      <div className="rounded-2xl border border-[#1F2937] bg-[#111827]/60 p-12 text-center">
        <Layers className="mx-auto h-12 w-12 text-slate-600" />
        <h3 className="mt-4 text-xl font-bold text-white">Attention Heatmap</h3>
        <p className="mt-2 text-sm text-slate-500">
          Upload and analyze an image first to generate the unified forensic heatmap.
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center rounded-2xl border border-[#1F2937] bg-[#111827]/60 p-16">
        <Loader2 className="h-10 w-10 animate-spin text-orange-400" />
        <p className="mt-4 text-sm text-slate-400">
          Fusing ELA, wavelet, copy-move, edge & tampering signals...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-8 text-center">
        <AlertCircle className="mx-auto h-8 w-8 text-red-400" />
        <p className="mt-3 text-sm text-red-300">{error}</p>
        <button
          type="button"
          onClick={runHeatmap}
          className="mt-4 rounded-lg bg-red-500/20 px-4 py-2 text-sm text-red-300 hover:bg-red-500/30"
        >
          Retry
        </button>
      </div>
    );
  }

  const originalUrl = getHeatmapArtifactUrl(evidenceId, "original");
  const heatmapUrl = getHeatmapArtifactUrl(evidenceId, "heatmap");
  const overlayUrl = getHeatmapArtifactUrl(evidenceId, "overlay");
  const legendUrl = getHeatmapArtifactUrl(evidenceId, "legend");
  const zones = result?.risk_zones || {};
  const explanations = result?.explanations || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 rounded-2xl border border-orange-500/20 bg-gradient-to-br from-orange-500/5 to-[#111827] p-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-orange-400">
            Unified Attention Heatmap
          </p>
          <h3 className="mt-1 text-xl font-bold text-white">
            {filename || evidenceId}
          </h3>
          <p className="mt-1 text-sm text-slate-400">
            Overall risk: {Math.round((result?.overall_risk || 0) * 100)}% ·
            Red {zones.high_manipulation_pct ?? 0}% · Orange {zones.medium_risk_pct ?? 0}% ·
            Green {zones.safe_pct ?? 0}%
          </p>
        </div>
        <img
          src={`${getApiBaseUrl()}${legendUrl}`}
          alt="Legend"
          className="h-16 rounded-lg border border-[#1F2937]"
        />
      </div>

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-4 rounded-xl border border-[#1F2937] bg-[#111827]/80 p-4">
        <div className="flex gap-2">
          {[
            { id: "overlay", label: "Overlay" },
            { id: "side-by-side", label: "Side by Side", icon: Columns2 },
            { id: "heatmap", label: "Heatmap Only" },
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => setViewMode(id)}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                viewMode === id
                  ? "bg-orange-500/20 text-orange-300"
                  : "text-slate-400 hover:bg-slate-800"
              }`}
            >
              {Icon && <Icon className="h-3.5 w-3.5" />}
              {label}
            </button>
          ))}
        </div>

        {viewMode === "overlay" && (
          <div className="flex flex-1 items-center gap-3 min-w-[200px]">
            <span className="text-xs text-slate-500">Opacity</span>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={opacity}
              onChange={(e) => setOpacity(Number(e.target.value))}
              className="flex-1 accent-orange-500"
            />
            <span className="w-10 text-xs text-slate-400">
              {Math.round(opacity * 100)}%
            </span>
          </div>
        )}
      </div>

      {/* Viewer */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="overflow-hidden rounded-2xl border border-[#1F2937] bg-[#0B1220]"
      >
        {viewMode === "side-by-side" ? (
          <div className="grid gap-0 md:grid-cols-2">
            <div className="relative border-b border-[#1F2937] md:border-b-0 md:border-r">
              <span className="absolute left-3 top-3 z-10 rounded bg-black/60 px-2 py-1 text-[10px] text-slate-300">
                Original
              </span>
              <img
                src={`${getApiBaseUrl()}${originalUrl}`}
                alt="Original"
                className="w-full object-contain"
              />
            </div>
            <div className="relative">
              <span className="absolute left-3 top-3 z-10 rounded bg-black/60 px-2 py-1 text-[10px] text-orange-300">
                Attention Heatmap
              </span>
              <img
                src={`${getApiBaseUrl()}${heatmapUrl}`}
                alt="Heatmap"
                className="w-full object-contain"
              />
            </div>
          </div>
        ) : viewMode === "heatmap" ? (
          <img
            src={`${getApiBaseUrl()}${heatmapUrl}`}
            alt="Heatmap"
            className="w-full object-contain"
          />
        ) : (
          <div className="relative">
            <img
              src={`${getApiBaseUrl()}${originalUrl}`}
              alt="Original"
              className="w-full object-contain"
            />
            <img
              src={`${getApiBaseUrl()}${heatmapUrl}`}
              alt="Heatmap overlay"
              className="absolute inset-0 w-full object-contain"
              style={{ opacity }}
            />
          </div>
        )}
      </motion.div>

      {/* Module scores */}
      {result?.module_scores && (
        <div className="grid gap-3 sm:grid-cols-5">
          {Object.entries(result.module_scores).map(([mod, score]) => (
            <div
              key={mod}
              className="rounded-xl border border-[#1F2937] bg-[#111827]/80 p-3 text-center"
            >
              <p className="text-[10px] uppercase tracking-wider text-slate-500">
                {mod.replace("_", " ")}
              </p>
              <p className="mt-1 text-lg font-bold text-white">
                {Math.round(score * 100)}%
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Explainable findings */}
      <div className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-6">
        <h4 className="flex items-center gap-2 text-sm font-semibold text-white">
          <ImageIcon className="h-4 w-4 text-orange-400" />
          Explainable Findings
        </h4>
        <div className="mt-4 space-y-3">
          {explanations.map((exp, i) => (
            <div
              key={i}
              className="rounded-lg border border-[#1F2937] bg-[#0B1220] p-4"
            >
              <span className="text-[10px] uppercase tracking-wider text-orange-400">
                {exp.module}
              </span>
              <p className="mt-1 text-sm font-medium text-white">{exp.what}</p>
              <p className="mt-1 text-xs text-slate-500">{exp.why}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default HeatmapViewer;
