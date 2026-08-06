import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Brain,
  Scan,
  Waves,
  Database,
  Copy,
  FileText,
  Shield,
  Check,
  Loader2,
  SkipForward,
  Palette,
  Grid3x3,
  Radio,
  Sparkles,
  ScanFace,
  Eye,
  GitBranch,
} from "lucide-react";

const MODULE_META = {
  prepare_image: { icon: Scan, label: "Preparing image" },
  quick_scan: { icon: Scan, label: "Quick Scan" },
  deep_scan: { icon: Brain, label: "Deep Forensic Scan" },
  forensics: { icon: Scan, label: "ELA / Edge / Wavelet" },
  ela: { icon: Scan, label: "ELA" },
  wavelet: { icon: Waves, label: "Wavelet" },
  metadata: { icon: Database, label: "EXIF Metadata" },
  metadata_gps: { icon: Database, label: "GPS Validation" },
  metadata_timezone: { icon: Database, label: "Timezone Validation" },
  metadata_camera: { icon: Database, label: "Camera Fingerprint" },
  metadata_software: { icon: Database, label: "Editing Software" },
  metadata_thumbnail: { icon: Database, label: "Thumbnail Verification" },
  metadata_hash: { icon: Database, label: "Hash Consistency" },
  metadata_hidden: { icon: Database, label: "Hidden Metadata" },
  metadata_content: { icon: Database, label: "Content Comparison" },
  metadata_report: { icon: Database, label: "Forensic Report" },
  explainability: { icon: Brain, label: "Explainability Engine" },
  gradcam: { icon: Eye, label: "GradCAM" },
  shap: { icon: GitBranch, label: "SHAP Attribution" },
  lime: { icon: Brain, label: "LIME Explanation" },
  copy_move: { icon: Copy, label: "Copy Move" },
  noise: { icon: Shield, label: "Noise Analysis" },
  rgb: { icon: Palette, label: "RGB Analysis" },
  hsv: { icon: Palette, label: "HSV Analysis" },
  lab: { icon: Palette, label: "LAB Analysis" },
  ycbcr: { icon: Palette, label: "YCbCr Analysis" },
  frequency: { icon: Radio, label: "Frequency Domain" },
  jpeg_block: { icon: Grid3x3, label: "JPEG Block Analysis" },
  gan_detection: { icon: Sparkles, label: "GAN / AI Generator Detection" },
  gan_cnn: { icon: Sparkles, label: "GAN CNN" },
  gan_vit: { icon: Sparkles, label: "GAN ViT" },
  gan_clip: { icon: Sparkles, label: "GAN CLIP" },
  gan_frequency: { icon: Radio, label: "GAN Frequency" },
  face_forensics: { icon: ScanFace, label: "Face Forensics" },
  pdf_render: { icon: FileText, label: "PDF Render" },
  validate: { icon: Scan, label: "Validate" },
  convert: { icon: Scan, label: "Convert" },
  layout: { icon: FileText, label: "Layout" },
  heatmap: { icon: Waves, label: "Heatmap" },
  font: { icon: FileText, label: "Font Consistency" },
  spacing: { icon: FileText, label: "Spacing" },
  region: { icon: FileText, label: "OCR Layout" },
  ocr: { icon: FileText, label: "OCR Consensus" },
  ocr_consensus: { icon: FileText, label: "OCR Voting" },
  ocr_tesseract: { icon: FileText, label: "Tesseract" },
  ocr_easyocr: { icon: FileText, label: "EasyOCR" },
  ocr_paddleocr: { icon: FileText, label: "PaddleOCR" },
  ocr_trocr: { icon: FileText, label: "TrOCR" },
  tampering: { icon: Shield, label: "Tampering" },
  layoutlmv3: { icon: Brain, label: "LayoutLMv3" },
  donut: { icon: Brain, label: "Donut Transformer" },
  document_intelligence: { icon: Shield, label: "Document Intelligence" },
  fusion: { icon: Brain, label: "Risk Fusion" },
  artifacts: { icon: Scan, label: "Generating Heatmaps" },
  jury: { icon: Brain, label: "AI Jury Deliberation" },
  dashboard: { icon: Grid3x3, label: "Building Dashboard" },
  reports: { icon: FileText, label: "Preparing Reports" },
  analysis_sync: { icon: Check, label: "Finalizing Analysis" },
  keyframes: { icon: Scan, label: "Keyframes" },
  frame_signals: { icon: Waves, label: "Frame Signals" },
  keyframe_forensics: { icon: Brain, label: "Keyframe Forensics" },
};

const DEFAULT_MODULES = [
  "prepare_image", "quick_scan", "metadata", "metadata_gps", "metadata_timezone",
  "metadata_camera", "metadata_software", "metadata_thumbnail", "metadata_hash",
  "metadata_hidden", "metadata_content", "metadata_report",
  "explainability", "gradcam", "shap", "lime",
  "rgb", "jpeg_block", "frequency",
  "gan_detection", "face_forensics", "forensics", "copy_move", "noise",
  "lab", "ycbcr", "hsv", "tampering", "deep_scan", "fusion",
];

function AnalysisLoader({
  active = true,
  analysisType = "image",
  fileCount = 1,
  progressEvents = [],
}) {
  const [elapsed, setElapsed] = useState(0);
  const [moduleState, setModuleState] = useState({});

  useEffect(() => {
    if (!active) {
      setModuleState({});
      setElapsed(0);
      return;
    }
    const start = Date.now();
    const tick = setInterval(() => {
      setElapsed(Math.floor((Date.now() - start) / 1000));
    }, 1000);
    return () => clearInterval(tick);
  }, [active]);

  useEffect(() => {
    if (!progressEvents.length) return;
    const latest = progressEvents[progressEvents.length - 1];
    if (!latest?.module) return;
    setModuleState((prev) => ({
      ...prev,
      [latest.module]: {
        status: latest.status,
        elapsed: latest.elapsed,
      },
    }));
  }, [progressEvents]);

  if (!active) return null;

  const modules = analysisType === "document"
    ? [
        "pdf_render",
        "ocr_tesseract", "ocr_easyocr", "ocr_paddleocr", "ocr_trocr",
        "ocr_consensus", "ocr", "region",
        "layoutlmv3", "donut", "document_intelligence",
        "fusion",
      ]
    : analysisType === "video"
      ? ["metadata", "keyframes", "frame_signals", "keyframe_forensics"]
      : DEFAULT_MODULES;

  const completed = modules.filter(
    (m) => moduleState[m]?.status === "completed"
  ).length;
  const hasLiveProgress = progressEvents.length > 0;
  const progress = hasLiveProgress
    ? Math.round((completed / modules.length) * 100)
    : Math.min(90, Math.round((elapsed / 8) * 100));
  const remaining = Math.max(0, Math.ceil((modules.length - completed) * 0.8));

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-8 rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-8 backdrop-blur-xl"
    >
      <div className="flex flex-col items-center text-center">
        <motion.div
          animate={{ scale: [1, 1.06, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
          className="relative mb-6 flex h-16 w-16 items-center justify-center rounded-2xl border border-cyan-500/30 bg-gradient-to-br from-blue-600/20 to-cyan-600/20"
        >
          <Brain className="h-7 w-7 text-cyan-400" />
        </motion.div>

        <p className="text-lg font-semibold text-white">
          Analyzing {fileCount > 1 ? `${fileCount} files` : "evidence"}...
        </p>
        <p className="mt-1 text-xs text-slate-500">
          {elapsed}s elapsed
          {hasLiveProgress ? ` · ~${remaining}s remaining` : ""}
          {hasLiveProgress ? " · live progress" : ""}
        </p>

        <div className="mt-6 w-full max-w-md space-y-2">
          {modules.map((modId) => {
            const meta = MODULE_META[modId] || { icon: Scan, label: modId };
            const Icon = meta.icon;
            const state = moduleState[modId];
            const isDone = state?.status === "completed";
            const isSkipped = state?.status === "skipped";
            const isCurrent = state?.status === "running";
            const isFailed = state?.status === "failed";

            return (
              <div
                key={modId}
                className={`flex items-center gap-3 rounded-lg px-3 py-2 text-left transition ${
                  isCurrent ? "bg-cyan-500/10" : ""
                }`}
              >
                {isDone ? (
                  <motion.span
                    initial={{ scale: 0.8 }}
                    animate={{ scale: 1 }}
                    className="text-emerald-400"
                  >
                    ✓
                  </motion.span>
                ) : isSkipped ? (
                  <SkipForward className="h-4 w-4 shrink-0 text-slate-500" />
                ) : isCurrent ? (
                  <Loader2 className="h-4 w-4 shrink-0 animate-spin text-cyan-400" />
                ) : isFailed ? (
                  <Icon className="h-4 w-4 shrink-0 text-red-400" />
                ) : (
                  <Icon className="h-4 w-4 shrink-0 text-slate-600" />
                )}
                <span
                  className={`flex-1 text-sm ${
                    isDone
                      ? "text-emerald-400"
                      : isSkipped
                        ? "text-slate-500"
                        : isCurrent
                          ? "text-white"
                          : isFailed
                            ? "text-red-400"
                            : "text-slate-600"
                  }`}
                >
                  {isDone ? `✓ ${meta.label}` : isSkipped ? `${meta.label} (skipped)` : meta.label}
                </span>
                {state?.elapsed > 0 && (
                  <span className="text-[10px] text-slate-500">
                    {state.elapsed.toFixed(1)}s
                  </span>
                )}
              </div>
            );
          })}
        </div>

        <div className="mt-6 h-2 w-full max-w-md overflow-hidden rounded-full bg-slate-800">
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-blue-500 to-cyan-400"
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.4 }}
          />
        </div>
        <p className="mt-2 text-xs text-slate-500">{progress}% complete</p>
      </div>
    </motion.div>
  );
}

export default AnalysisLoader;
