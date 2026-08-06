import { motion } from "framer-motion";
import { Brain, Eye, FileText, PenTool, CheckCircle, Activity } from "lucide-react";

const MODELS = [
  { name: "Vision Forensics", icon: Eye, status: "online", accuracy: "97.2%", latency: "3.8s" },
  { name: "Document OCR", icon: FileText, status: "online", accuracy: "98.1%", latency: "5.2s" },
  { name: "Siamese Signature", icon: PenTool, status: "online", accuracy: "99.0%", latency: "1.4s" },
  { name: "AI Jury Ensemble", icon: Brain, status: "online", accuracy: "96.8%", latency: "8.1s" },
];

function ModelHealthPanel({ health }) {
  const device = health?.hardware?.device || health?.inference?.device || "cpu";
  const cuda = health?.hardware?.cuda_available;
  const statusLabel = health?.status === "healthy" ? "All Systems Operational" : "Checking…";

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.15 }}
      className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-6 backdrop-blur-xl"
    >
      <div className="flex items-center justify-between mb-5">
        <div>
          <h3 className="text-lg font-semibold text-white">AI Model Health</h3>
          <p className="text-xs text-slate-500">
            Device: {device}{cuda ? ` · ${health.hardware.cuda_device_name}` : ""}
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-full bg-emerald-500/10 px-3 py-1 text-xs text-emerald-400">
          <Activity className="h-3 w-3 animate-pulse" />
          {statusLabel}
        </div>
      </div>

      <div className="space-y-3">
        {MODELS.map((model, i) => {
          const Icon = model.icon;
          return (
            <motion.div
              key={model.name}
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 * i }}
              className="flex items-center justify-between rounded-xl border border-[#1F2937] bg-[#0B1120]/60 px-4 py-3"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-500/10">
                  <Icon className="h-4 w-4 text-blue-400" />
                </div>
                <div>
                  <p className="text-sm font-medium text-white">{model.name}</p>
                  <p className="text-xs text-slate-500">
                    {model.accuracy} accuracy · {model.latency} avg
                  </p>
                </div>
              </div>
              <CheckCircle className="h-4 w-4 text-emerald-400" />
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}

export default ModelHealthPanel;
