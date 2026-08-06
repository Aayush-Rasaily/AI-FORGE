import { useState } from "react";
import { motion } from "framer-motion";
import {
  ScanFace,
  Loader2,
  AlertCircle,
  Upload,
  Video,
  Image as ImageIcon,
} from "lucide-react";

import {
  analyzeDeepfakeImage,
  analyzeDeepfakeVideo,
  analyzeDeepfakeImageUpload,
  getArtifactUrl,
  getApiBaseUrl,
} from "../../services/api";
import RiskGauge from "../ui/RiskGauge";
import FaceForensicsPanel from "../ui/FaceForensicsPanel";
import GanDetectionPanel from "../ui/GanDetectionPanel";

function SignalList({ findings = [] }) {
  if (!findings.length) {
    return (
      <p className="text-sm text-slate-500">
        No deepfake indicators detected.
      </p>
    );
  }
  return (
    <div className="space-y-3">
      {findings.map((f, i) => (
        <div
          key={i}
          className="rounded-lg border border-[#1F2937] bg-[#0B1220] p-4"
        >
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase tracking-wider text-red-400">
              {f.type || "signal"}
            </span>
            {f.score != null && (
              <span className="text-[10px] text-slate-500">
                {Math.round(f.score * 100)}%
              </span>
            )}
          </div>
          <p className="mt-1 text-sm font-medium text-white">{f.what}</p>
          <p className="mt-1 text-xs text-slate-500">{f.why}</p>
        </div>
      ))}
    </div>
  );
}

function DeepFakeForensics({ imageResults = [] }) {
  const [mode, setMode] = useState("image"); // image | video
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [videoFile, setVideoFile] = useState(null);

  const primaryImage = imageResults[0];
  const evidenceId = primaryImage?.evidenceId;

  async function runImageAnalysis() {
    if (!evidenceId) return;
    setLoading(true);
    setError("");
    try {
      const data = await analyzeDeepfakeImage(evidenceId);
      setResult(data);
    } catch (err) {
      setError(err.message || "Deepfake analysis failed.");
    } finally {
      setLoading(false);
    }
  }

  async function runVideoAnalysis() {
    if (!videoFile) return;
    setLoading(true);
    setError("");
    try {
      const data = await analyzeDeepfakeVideo(videoFile);
      setResult(data);
    } catch (err) {
      setError(err.message || "Video deepfake analysis failed.");
    } finally {
      setLoading(false);
    }
  }

  async function runUploadAnalysis(file) {
    setLoading(true);
    setError("");
    try {
      const data = await analyzeDeepfakeImageUpload(file);
      setResult(data);
    } catch (err) {
      setError(err.message || "Deepfake analysis failed.");
    } finally {
      setLoading(false);
    }
  }

  const probability = Math.round((result?.deepfake_probability || 0) * 100);
  const confidence = Math.round((result?.confidence || 0) * 100);
  const heatmapUrl = result?.heatmap_url
    ? result.heatmap_url.startsWith("http")
      ? result.heatmap_url
      : `${getApiBaseUrl()}${result.heatmap_url}`
    : result?.heatmap
      ? getArtifactUrl(result.heatmap)
      : null;

  return (
    <div className="space-y-6">
      {/* Mode selector */}
      <div className="flex gap-2">
        {[
          { id: "image", label: "Image", icon: ImageIcon },
          { id: "video", label: "Video", icon: Video },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => { setMode(id); setResult(null); setError(""); }}
            className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition ${
              mode === id
                ? "bg-red-500/20 text-red-300"
                : "text-slate-400 hover:bg-slate-800"
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Input */}
      {mode === "image" ? (
        <div className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-6">
          {evidenceId ? (
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm text-slate-400">Evidence ready</p>
                <p className="font-medium text-white">
                  {primaryImage.filename || evidenceId}
                </p>
              </div>
              <button
                type="button"
                onClick={runImageAnalysis}
                disabled={loading}
                className="rounded-lg bg-red-500/20 px-5 py-2.5 text-sm font-medium text-red-300 hover:bg-red-500/30 disabled:opacity-50"
              >
                {loading ? "Analyzing..." : "Run DeepFake Detection"}
              </button>
            </div>
          ) : (
            <label className="flex cursor-pointer flex-col items-center gap-3 rounded-xl border border-dashed border-[#1F2937] p-8 hover:border-red-500/30">
              <Upload className="h-8 w-8 text-slate-500" />
              <span className="text-sm text-slate-400">
                Upload an image or analyze evidence in Image Forensics first
              </span>
              <input
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) runUploadAnalysis(f);
                }}
              />
            </label>
          )}
        </div>
      ) : (
        <div className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-6">
          <label className="flex cursor-pointer flex-col items-center gap-3 rounded-xl border border-dashed border-[#1F2937] p-8 hover:border-red-500/30">
            <Video className="h-8 w-8 text-slate-500" />
            <span className="text-sm text-slate-400">
              {videoFile ? videoFile.name : "Select a video file"}
            </span>
            <input
              type="file"
              accept="video/*"
              className="hidden"
              onChange={(e) => setVideoFile(e.target.files?.[0] || null)}
            />
          </label>
          {videoFile && (
            <button
              type="button"
              onClick={runVideoAnalysis}
              disabled={loading}
              className="mt-4 w-full rounded-lg bg-red-500/20 py-2.5 text-sm font-medium text-red-300 hover:bg-red-500/30 disabled:opacity-50"
            >
              {loading ? "Analyzing video frames..." : "Run Video DeepFake Detection"}
            </button>
          )}
        </div>
      )}

      {loading && (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-[#1F2937] p-12">
          <Loader2 className="h-10 w-10 animate-spin text-red-400" />
          <p className="mt-4 text-sm text-slate-400">
            Detecting face swapping, GAN artifacts, blink anomalies...
          </p>
        </div>
      )}

      {error && (
        <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-6 text-center">
          <AlertCircle className="mx-auto h-8 w-8 text-red-400" />
          <p className="mt-3 text-sm text-red-300">{error}</p>
        </div>
      )}

      {result && !loading && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          <FaceForensicsPanel faceForensics={result} />

          {result.gan_detection && (
            <GanDetectionPanel ganDetection={result.gan_detection} />
          )}

          {result.frames?.length > 0 && (
            <div className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-6">
              <p className="mb-4 text-sm font-semibold text-white">
                Per-Frame Analysis
              </p>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {result.frames.map((frame) => (
                  <div
                    key={frame.frame_number}
                    className="rounded-lg border border-[#1F2937] bg-[#0B1220] p-3"
                  >
                    <p className="text-xs text-slate-500">
                      Frame {frame.frame_number} · {frame.timestamp}s
                    </p>
                    <p className="mt-1 text-sm font-medium text-white">
                      {Math.round((frame.deepfake_probability || 0) * 100)}% probability
                    </p>
                    <p className="text-xs text-slate-400">{frame.verdict}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {result.blink_analysis && (
            <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
              <p className="text-xs font-semibold text-amber-300">Blink Analysis</p>
              <p className="mt-1 text-sm text-slate-300">
                {result.blink_analysis.message}
              </p>
            </div>
          )}

        </motion.div>
      )}

      {!result && !loading && !error && mode === "image" && !evidenceId && (
        <div className="rounded-2xl border border-[#1F2937] bg-[#111827]/60 p-12 text-center">
          <ScanFace className="mx-auto h-12 w-12 text-slate-600" />
          <h3 className="mt-4 text-xl font-bold text-white">DeepFake Detection</h3>
          <p className="mt-2 text-sm text-slate-500">
            Detects face swapping, GAN artifacts, compression inconsistencies,
            and blink anomalies in images and videos.
          </p>
        </div>
      )}
    </div>
  );
}

export default DeepFakeForensics;
