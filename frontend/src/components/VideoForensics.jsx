import { useState, useRef, useCallback } from "react";
import {
  analyzeVideo,
  getArtifactUrl,
  ApplicationError,
  ConnectivityError,
  formatApiError,
} from "../services/api";
import { useBackend } from "../context/BackendConnectivity";
import AnalysisLoader from "./ui/AnalysisLoader";

function VideoForensics({ onResult }) {
  const { backendOnline } = useBackend();
  const [selectedFile, setSelectedFile] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [progressEvents, setProgressEvents] = useState([]);
  const [focusedTimestamp, setFocusedTimestamp] = useState(null);
  const timelineRef = useRef(null);

  // Click-to-seek: scroll to matching timeline entry and highlight it
  const seekToTimestamp = useCallback((timestampSec) => {
    setFocusedTimestamp(timestampSec);
    // Scroll the matching entry into view
    const el = document.getElementById(`video-ts-${String(timestampSec).replace(".", "_")}`);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      el.focus({ preventScroll: true });
    }
  }, []);

  function handleFileChange(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setSelectedFile(file);
    setResult(null);
    setError("");
    setProgressEvents([]);
  }

  async function handleAnalyze() {
    if (!backendOnline) {
      setError("Backend Offline — health check failed. Use Reconnect.");
      return;
    }
    if (!selectedFile) {
      setError("Please select a video first.");
      return;
    }

    try {
      setLoading(true);
      setError("");
      setResult(null);
      setProgressEvents([]);

      const data = await analyzeVideo(selectedFile, {
        onProgress: (event) => {
          setProgressEvents((prev) => [...prev, event]);
        },
      });

      setResult(data.analysis);
      if (onResult) onResult(data.analysis);
    } catch (err) {
      console.error("[VIDEO] Analysis failed:", err);
      if (err instanceof ApplicationError) {
        setError(err.message || "Video analysis failed.");
      } else if (err instanceof ConnectivityError) {
        setError("Connectivity Error — retry analysis. Backend status is health-check only.");
      } else {
        setError(formatApiError(err, "Video analysis failed."));
      }
    } finally {
      setLoading(false);
    }
  }

  const video = result?.video || {};
  const summary = result?.summary || {};
  const frames = result?.frames || [];
  const timeline = result?.timeline || [];
  const deepfakeProb = result?.deepfake_probability ?? summary?.deepfake_probability ?? 0;

  return (
    <div className="mt-10 space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-white">Video Forensics & Temporal Deepfake Analysis</h2>
        <p className="mt-2 text-sm text-slate-400">
          Stream/batch keyframe analysis, temporal consistency checks, face swap, and deepfake timeline verification.
        </p>
      </div>

      <div className="rounded-xl border-2 border-dashed border-slate-700 bg-slate-900/80 p-8 text-center">
        <h3 className="text-xl font-semibold text-white">Upload Video Evidence</h3>
        <p className="mt-2 text-sm text-slate-400">
          Supported formats: MP4, AVI, MOV, MKV, WEBM
        </p>

        <label className="mt-6 inline-block cursor-pointer rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-3 font-semibold text-white transition hover:from-blue-500 hover:to-indigo-500">
          Select Video File
          <input
            type="file"
            accept="video/mp4,video/avi,video/quicktime,video/x-matroska,video/webm"
            onChange={handleFileChange}
            className="hidden"
          />
        </label>

        {selectedFile && (
          <div className="mt-5 max-w-md mx-auto rounded-lg bg-slate-950 p-4 border border-slate-800">
            <p className="font-medium text-slate-200">{selectedFile.name}</p>
            <p className="mt-1 text-sm text-slate-400">
              {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
            </p>
          </div>
        )}

        <button
          onClick={handleAnalyze}
          disabled={loading || !selectedFile || !backendOnline}
          className="mt-6 rounded-lg bg-emerald-600 px-8 py-3 font-semibold text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50 shadow-lg shadow-emerald-600/20"
        >
          {loading ? "Analyzing Video Frames..." : !backendOnline ? "Backend Offline" : "Analyze Video"}
        </button>
      </div>

      <AnalysisLoader
        active={loading}
        analysisType="video"
        fileCount={1}
        progressEvents={progressEvents}
      />

      {error && (
        <div className="rounded-lg border border-red-800 bg-red-950/80 p-5 text-red-300">
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-8">

          {/* Overview Metrics */}
          <div>
            <h3 className="text-xl font-bold text-white mb-4">Video Technical Metadata</h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
              <MetricCard title="Duration" value={`${video.duration ?? 0} sec`} />
              <MetricCard title="FPS" value={video.fps ?? "N/A"} />
              <MetricCard title="Total Frames" value={video.frame_count ?? "N/A"} />
              <MetricCard
                title="Resolution"
                value={`${video.width ?? 0} × ${video.height ?? 0}`}
              />
              <MetricCard
                title="Deepfake Confidence"
                value={`${(deepfakeProb * 100).toFixed(1)}%`}
                highlight={deepfakeProb > 0.5 ? "text-rose-400" : "text-emerald-400"}
              />
            </div>
          </div>

          {/* Courtroom Timeline of Anomalies */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/90 p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-xl font-bold text-white">Courtroom Forensic Timeline</h3>
                <p className="text-xs text-slate-400 mt-1">
                  Temporal anomaly sequence with exact timestamps, deepfake probabilities, and evidence rationale.
                </p>
              </div>
              <span className="text-xs font-semibold px-3 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                {timeline.length} Anomaly Events
              </span>
            </div>

            {timeline.length === 0 ? (
              <div className="p-6 text-center text-slate-400 bg-slate-950/50 rounded-lg border border-slate-800">
                No significant temporal or deepfake anomalies detected across keyframe timeline.
              </div>
            ) : (
              <div
                ref={timelineRef}
                className="space-y-3 mt-4 max-h-96 overflow-y-auto pr-2"
              >
                {timeline.map((evt, idx) => {
                  const parsedTimestamp = Number(String(evt.timestamp || "").replace("s", ""));
                  const ts = evt.time_seconds ?? (Number.isFinite(parsedTimestamp) ? parsedTimestamp : 0);
                  const tsId = `video-ts-${String(ts).replace(".", "_")}`;
                  const isFocused = focusedTimestamp != null && Math.abs(ts - focusedTimestamp) < 0.1;
                  return (
                    <div
                      id={tsId}
                      key={idx}
                      tabIndex={-1}
                      role="button"
                      aria-label={`Seek to ${evt.timestamp || `${ts.toFixed(3)}s`}`}
                      onClick={() => seekToTimestamp(ts)}
                      className={`flex items-start gap-4 p-4 rounded-lg border transition cursor-pointer outline-none ${
                        isFocused
                          ? "border-red-500/60 bg-red-950/30 ring-1 ring-red-500/40"
                          : "border-slate-800/80 bg-slate-950/80 hover:border-slate-700"
                      }`}
                    >
                      <div className={`px-3 py-1 rounded font-mono text-xs font-bold shrink-0 ${
                        isFocused ? "bg-red-900/80 text-red-300" : "bg-slate-800 text-cyan-400"
                      }`}>
                        {evt.timestamp || `${ts.toFixed(3)}s`}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-sm text-slate-200">
                            Frame #{evt.frame_number ?? evt.frame_index}
                          </span>
                          <span className={`text-xs font-bold ${
                            evt.deepfake_confidence > 60 ? "text-rose-400" : "text-amber-400"
                          }`}>
                            Deepfake Confidence: {evt.deepfake_confidence ?? (evt.deepfake_score * 100)?.toFixed(1)}%
                          </span>
                        </div>
                        <p className="text-xs text-slate-300 mt-1">
                          <strong>Reason:</strong>{" "}
                          {evt.reason_text || (evt.reasons && evt.reasons.join(", ")) || "Temporal anomaly"}
                        </p>
                        {evt.faces && evt.faces.length > 0 && (
                          <p className="text-xs text-slate-400 mt-1">
                            Detected faces: {evt.faces.length} in frame ROI
                          </p>
                        )}
                        {isFocused && (
                          <p className="mt-1.5 text-[10px] font-semibold uppercase tracking-wider text-red-400">
                            ▶ Investigating this frame
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Keyframe Gallery */}
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
            <h3 className="text-xl font-bold text-white mb-1">Key Frame Forensic Gallery</h3>
            <p className="text-sm text-slate-400 mb-6">
              Representative scene keyframes with edge density, texture blur, and face detection signals.
            </p>

            {frames.length === 0 ? (
              <p className="text-slate-500">No frames available.</p>
            ) : (
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
                {frames.map((frame, index) => (
                  <FrameCard
                    key={frame.frame_index ?? index}
                    frame={frame}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function MetricCard({ title, value, highlight }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <p className="text-xs text-slate-400 uppercase tracking-wider">{title}</p>
      <p className={`mt-2 text-2xl font-bold ${highlight || "text-white"}`}>{value}</p>
    </div>
  );
}

function FrameCard({ frame }) {
  const imageUrl = getArtifactUrl(frame.image);

  return (
    <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-950">
      <div className="aspect-video bg-black relative">
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={`Frame ${frame.frame_index}`}
            className="h-full w-full object-contain"
          />
        ) : (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-slate-500">Frame unavailable</p>
          </div>
        )}

        {frame.signals?.deepfake_score > 0.5 && (
          <div className="absolute top-2 right-2 px-2 py-1 bg-rose-600/90 text-white font-bold text-xs rounded shadow">
            Anomaly
          </div>
        )}
      </div>

      <div className="p-4">
        <div className="flex justify-between items-center mb-3">
          <p className="font-semibold text-sm text-slate-200">Frame #{frame.frame_number ?? frame.frame_index}</p>
          <p className="text-xs font-mono text-cyan-400">{frame.timestamp_formatted || `${frame.timestamp}s`}</p>
        </div>

        <div className="space-y-1.5 text-xs">
          <SignalRow label="Edge Density" value={frame.signals?.edge_density ?? "N/A"} />
          <SignalRow label="Blur Score" value={frame.signals?.blur_score ?? "N/A"} />
          <SignalRow label="GAN Artifacts" value={frame.signals?.gan_artifacts ?? "N/A"} />
          <SignalRow label="Detected Faces" value={frame.signals?.face_count ?? 0} />
        </div>
      </div>
    </div>
  );
}

function SignalRow({ label, value }) {
  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-slate-400">{label}</span>
      <span className="font-semibold text-slate-200">{value}</span>
    </div>
  );
}

export default VideoForensics;
