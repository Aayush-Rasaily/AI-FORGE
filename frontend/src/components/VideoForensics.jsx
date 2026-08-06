import { useState } from "react";
import { motion } from "framer-motion";
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

  return (
    <div className="mt-10 space-y-8">
      <div>
        <h2 className="text-2xl font-bold">Video Forensics</h2>
        <p className="mt-2 text-sm text-slate-400">
          Analyze video metadata, scene keyframes, and frame-level forensic signals.
        </p>
      </div>

      <div className="rounded-xl border-2 border-dashed border-slate-700 bg-slate-900 p-10">
        <h3 className="text-xl font-semibold">Upload Video Evidence</h3>
        <p className="mt-2 text-sm text-slate-400">
          Supported formats: MP4, AVI, MOV, MKV, WEBM
        </p>

        <label className="mt-6 inline-block cursor-pointer rounded-lg bg-blue-600 px-6 py-3 font-semibold transition hover:bg-blue-500">
          Select Video
          <input
            type="file"
            accept="video/mp4,video/avi,video/quicktime,video/x-matroska,video/webm"
            onChange={handleFileChange}
            className="hidden"
          />
        </label>

        {selectedFile && (
          <div className="mt-5 rounded-lg bg-slate-950 p-4">
            <p className="font-medium">{selectedFile.name}</p>
            <p className="mt-1 text-sm text-slate-400">
              {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
            </p>
          </div>
        )}

        <button
          onClick={handleAnalyze}
          disabled={loading || !selectedFile || !backendOnline}
          className="mt-6 rounded-lg bg-green-600 px-8 py-3 font-semibold transition hover:bg-green-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Analyzing Video..." : !backendOnline ? "Backend Offline" : "Analyze Video"}
        </button>
      </div>

      <AnalysisLoader
        active={loading}
        analysisType="video"
        fileCount={1}
        progressEvents={progressEvents}
      />

      {error && (
        <div className="rounded-lg border border-red-800 bg-red-950 p-5 text-red-300">
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-8">
          <div>
            <h3 className="text-xl font-bold">Video Analysis Report</h3>
            <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <MetricCard title="Duration" value={`${video.duration ?? 0} sec`} />
              <MetricCard title="FPS" value={video.fps ?? "N/A"} />
              <MetricCard title="Frame Count" value={video.frame_count ?? "N/A"} />
              <MetricCard
                title="Resolution"
                value={`${video.width ?? 0} × ${video.height ?? 0}`}
              />
            </div>
          </div>

          <div>
            <h3 className="text-xl font-bold">Forensic Summary</h3>
            <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-3">
              <MetricCard
                title="Frames Analyzed"
                value={summary.frames_analyzed ?? 0}
              />
              <MetricCard
                title="Average Edge Density"
                value={summary.average_edge_density ?? "N/A"}
              />
              <MetricCard
                title="Average Blur Score"
                value={summary.average_blur_score ?? "N/A"}
              />
            </div>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
            <h3 className="text-xl font-bold">Key Frame Analysis</h3>
            <p className="mt-2 text-sm text-slate-400">
              Representative frames extracted via scene detection.
            </p>

            {frames.length === 0 ? (
              <p className="mt-6 text-slate-500">No frames available.</p>
            ) : (
              <div className="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
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

function MetricCard({ title, value }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <p className="text-sm text-slate-400">{title}</p>
      <p className="mt-2 text-2xl font-bold">{value}</p>
    </div>
  );
}

function FrameCard({ frame }) {
  const imageUrl = getArtifactUrl(frame.image);

  return (
    <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-950">
      <div className="aspect-video bg-black">
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
      </div>

      <div className="p-5">
        <div className="flex justify-between">
          <p className="font-semibold">Frame {frame.frame_index}</p>
          <p className="text-sm text-slate-400">{frame.timestamp}s</p>
        </div>

        <div className="mt-4 space-y-2">
          <SignalRow label="Edge Density" value={frame.signals?.edge_density ?? "N/A"} />
          <SignalRow label="Brightness" value={frame.signals?.brightness ?? "N/A"} />
          <SignalRow label="Blur Score" value={frame.signals?.blur_score ?? "N/A"} />
        </div>
      </div>
    </div>
  );
}

function SignalRow({ label, value }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-slate-400">{label}</span>
      <span className="font-semibold">{value}</span>
    </div>
  );
}

export default VideoForensics;
