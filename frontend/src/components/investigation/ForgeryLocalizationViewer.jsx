import { useCallback, useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Layers,
  Loader2,
  AlertCircle,
  MapPin,
  Eye,
  Flame,
  Scan,
  Diff,
  FileJson,
  MessageSquareText,
  Play,
} from "lucide-react";
import {
  getLocalization,
  getArtifactUrl,
  ConnectivityError,
  formatApiError,
} from "../../services/api";
import { useBackend } from "../../context/BackendConnectivity";

const VIEWS = [
  { id: "original", label: "Original", icon: Eye },
  { id: "heatmap", label: "Heatmap", icon: Flame },
  { id: "forgery_mask", label: "Forgery Mask", icon: Scan },
  { id: "difference", label: "Difference", icon: Diff },
  { id: "highlighted", label: "Highlighted", icon: MapPin },
  { id: "metadata", label: "Metadata", icon: FileJson },
  { id: "explanation", label: "AI Explanation", icon: MessageSquareText },
];

function ForgeryLocalizationViewer({ evidenceId }) {
  const { online } = useBackend();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [data, setData] = useState(null);
  const [view, setView] = useState("heatmap");
  const [selectedRegion, setSelectedRegion] = useState(null);
  const [imgNatural, setImgNatural] = useState({ w: 1, h: 1 });

  const load = useCallback(async () => {
    if (!evidenceId || !online) return;
    setLoading(true);
    setError("");
    try {
      const result = await getLocalization(evidenceId);
      setData(result);
      if (result?.regions?.[0]) setSelectedRegion(result.regions[0]);
    } catch (err) {
      if (!(err instanceof ConnectivityError)) {
        setError(formatApiError(err, "Localization unavailable"));
      }
    } finally {
      setLoading(false);
    }
  }, [evidenceId, online]);

  useEffect(() => {
    load();
  }, [load]);

  const views = data?.views || {};
  const regions = data?.regions || [];
  const timeline = data?.video_timeline?.suspicious_intervals || [];

  const imageSrc = useMemo(() => {
    const key =
      view === "highlighted"
        ? "highlighted"
        : view === "forgery_mask"
          ? "forgery_mask"
          : view === "difference"
            ? "difference"
            : view === "original"
              ? "original"
              : "heatmap";
    const path = views[key] || views.heatmap || views.original;
    return path ? getArtifactUrl(path) : "";
  }, [view, views]);

  if (!evidenceId) return null;

  if (!online) {
    return (
      <div className="mt-6 rounded-2xl border border-red-500/20 bg-[#111827]/80 p-5 text-sm text-slate-400">
        Backend Offline — forgery localization paused until connectivity resumes.
      </div>
    );
  }

  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-6 overflow-hidden rounded-2xl border border-[#1F2937] bg-[#111827]/80 backdrop-blur-xl"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#1F2937] px-5 py-4">
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-cyan-400" />
          <div>
            <h3 className="text-sm font-semibold text-white">Forgery Localization</h3>
            <p className="text-[11px] text-slate-500">
              Pixel-level fusion of ELA, wavelet, copy-move, noise &amp; deep signals
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          className="rounded-lg border border-[#1F2937] px-3 py-1.5 text-xs text-slate-300 hover:border-cyan-500/40"
        >
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      <div className="flex flex-wrap gap-2 border-b border-[#1F2937] px-5 py-3">
        {VIEWS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setView(id)}
            className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs transition ${
              view === id
                ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/40"
                : "border border-transparent text-slate-400 hover:bg-[#0B1120]"
            }`}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        ))}
      </div>

      <div className="grid gap-4 p-5 lg:grid-cols-[1fr_280px]">
        <div className="relative min-h-[280px] overflow-hidden rounded-xl border border-[#1F2937] bg-[#0B1120]">
          {loading && (
            <div className="absolute inset-0 z-10 flex items-center justify-center bg-[#0B1120]/70">
              <Loader2 className="h-6 w-6 animate-spin text-cyan-400" />
            </div>
          )}
          {error && (
            <div className="flex items-center gap-2 p-6 text-sm text-amber-300">
              <AlertCircle className="h-4 w-4" />
              {error}
            </div>
          )}

          {view === "metadata" && (
            <pre className="max-h-[420px] overflow-auto p-4 text-[11px] leading-relaxed text-slate-300">
              {JSON.stringify(
                {
                  layers_used: data?.layers_used,
                  coverage: data?.coverage,
                  regions: regions.slice(0, 12),
                  video_timeline: data?.video_timeline,
                  weights: data?.weights,
                },
                null,
                2
              )}
            </pre>
          )}

          {view === "explanation" && (
            <div className="space-y-3 p-5">
              <p className="text-sm leading-relaxed text-slate-200">
                {data?.explanation || "No AI explanation available yet."}
              </p>
              {selectedRegion && (
                <div className="rounded-lg border border-cyan-500/30 bg-cyan-500/5 p-3 text-xs text-slate-300">
                  <p className="font-medium text-cyan-300">Selected region</p>
                  <p className="mt-1">{selectedRegion.reason || selectedRegion.label}</p>
                  <p className="mt-1 text-slate-500">
                    Score {(Number(selectedRegion.score) * 100).toFixed(0)}% · type{" "}
                    {selectedRegion.type || "image_region"}
                  </p>
                </div>
              )}
            </div>
          )}

          {view !== "metadata" && view !== "explanation" && imageSrc && (
            <div className="relative">
              <img
                src={imageSrc}
                alt={view}
                className="max-h-[480px] w-full object-contain"
                onLoad={(e) =>
                  setImgNatural({
                    w: e.target.naturalWidth || 1,
                    h: e.target.naturalHeight || 1,
                  })
                }
              />
              {/* Clickable region overlays (normalized when possible) */}
              <div className="pointer-events-none absolute inset-0">
                {regions.map((reg) => {
                  const nb = reg.normalized_bbox || null;
                  const b = reg.bbox || {};
                  const style = nb
                    ? {
                        left: `${nb.x * 100}%`,
                        top: `${nb.y * 100}%`,
                        width: `${nb.w * 100}%`,
                        height: `${nb.h * 100}%`,
                      }
                    : {
                        left: `${(b.x / imgNatural.w) * 100}%`,
                        top: `${(b.y / imgNatural.h) * 100}%`,
                        width: `${(b.w / imgNatural.w) * 100}%`,
                        height: `${(b.h / imgNatural.h) * 100}%`,
                      };
                  const active = selectedRegion?.id === reg.id;
                  return (
                    <button
                      key={reg.id}
                      type="button"
                      title={reg.reason || reg.label}
                      onClick={() => {
                        setSelectedRegion(reg);
                        setView("explanation");
                      }}
                      className={`pointer-events-auto absolute border-2 transition ${
                        active
                          ? "border-cyan-400 bg-cyan-400/10"
                          : "border-amber-400/70 bg-amber-400/5 hover:bg-amber-400/15"
                      }`}
                      style={style}
                    />
                  );
                })}
              </div>
            </div>
          )}

          {!loading && !error && !imageSrc && view !== "metadata" && view !== "explanation" && (
            <p className="p-6 text-sm text-slate-500">No localization imagery for this evidence yet.</p>
          )}
        </div>

        <div className="space-y-4">
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Suspicious regions
            </p>
            <div className="max-h-56 space-y-2 overflow-auto">
              {regions.length === 0 && (
                <p className="text-xs text-slate-500">No discrete regions detected.</p>
              )}
              {regions.slice(0, 20).map((reg) => (
                <button
                  key={reg.id}
                  type="button"
                  onClick={() => {
                    setSelectedRegion(reg);
                    setView("explanation");
                  }}
                  className={`w-full rounded-lg border px-3 py-2 text-left text-xs transition ${
                    selectedRegion?.id === reg.id
                      ? "border-cyan-500/40 bg-cyan-500/10 text-cyan-200"
                      : "border-[#1F2937] text-slate-300 hover:border-slate-600"
                  }`}
                >
                  <span className="font-medium">{reg.label || reg.id}</span>
                  <span className="mt-0.5 block text-[10px] text-slate-500 line-clamp-2">
                    {reg.reason}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {timeline.length > 0 && (
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Video anomaly timeline
              </p>
              <div className="max-h-40 space-y-1.5 overflow-auto">
                {timeline.map((iv, idx) => (
                  <button
                    key={`${iv.timestamp}-${idx}`}
                    type="button"
                    onClick={() =>
                      setSelectedRegion({
                        id: `video-${idx}`,
                        reason: iv.reason,
                        score: iv.score,
                        label: `t=${Number(iv.timestamp).toFixed(2)}s`,
                        type: "video_interval",
                      })
                    }
                    className="flex w-full items-center gap-2 rounded-lg border border-[#1F2937] px-3 py-2 text-left text-xs text-slate-300 hover:border-violet-500/40"
                  >
                    <Play className="h-3 w-3 text-violet-400" />
                    <span>
                      Jump {Number(iv.timestamp).toFixed(2)}s
                      {iv.frame_number != null ? ` · frame ${iv.frame_number}` : ""}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          <AnimatePresence>
            {selectedRegion && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="rounded-lg border border-[#1F2937] bg-[#0B1120] p-3 text-xs text-slate-400"
              >
                <p className="font-medium text-slate-200">Forensic reason</p>
                <p className="mt-1">{selectedRegion.reason || "—"}</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </motion.section>
  );
}

export default ForgeryLocalizationViewer;
