import { memo } from "react";
import { motion } from "framer-motion";
import {
  Activity,
  CheckCircle,
  Cpu,
  Server,
  Shield,
  AlertTriangle,
} from "lucide-react";

const MODULES = [
  { name: "Vision Forensics", key: "vision" },
  { name: "Document OCR", key: "document" },
  { name: "Signature Net", key: "signature" },
  { name: "AI Jury", key: "jury" },
];

function SystemHealthWidget({ health, online, avgProcessingMs = 0, delay = 0.15 }) {
  const device = health?.hardware?.device || health?.inference?.device || "cpu";
  const cuda = health?.hardware?.cuda_available;
  const healthy = online && health?.status === "healthy";
  const sla = health?.sla_targets || {};

  const formatMs = (ms) => {
    const n = Number(ms) || 0;
    if (n >= 60000) return `${(n / 60000).toFixed(1)}m`;
    if (n >= 1000) return `${(n / 1000).toFixed(1)}s`;
    return `${n}ms`;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="command-panel rounded-2xl p-5 md:p-6"
    >
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-display text-base font-semibold text-white">System Health</h3>
          <p className="text-xs text-slate-500">
            Runtime · SLA · detector pipeline status
          </p>
        </div>
        <div
          className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold ${
            healthy
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
              : "border-amber-500/30 bg-amber-500/10 text-amber-400"
          }`}
        >
          <Activity className={`h-3 w-3 ${healthy ? "animate-pulse" : ""}`} />
          {healthy ? "Operational" : online ? "Degraded" : "Offline"}
        </div>
      </div>

      <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { icon: Server, label: "Backend", value: online ? "Online" : "Offline", ok: online },
          { icon: Cpu, label: "Device", value: device, ok: online },
          { icon: Shield, label: "Image SLA", value: `${sla.image_sec ?? "—"}s`, ok: true },
          { icon: AlertTriangle, label: "Avg Process", value: formatMs(avgProcessingMs), ok: avgProcessingMs > 0 },
        ].map((item) => (
          <div
            key={item.label}
            className="rounded-xl border border-white/5 bg-black/20 px-3 py-2.5"
          >
            <item.icon className={`mb-1 h-4 w-4 ${item.ok ? "text-cyan-400" : "text-slate-500"}`} />
            <p className="text-[10px] uppercase tracking-wider text-slate-500">{item.label}</p>
            <p className="truncate text-sm font-semibold capitalize text-white">{item.value}</p>
          </div>
        ))}
      </div>

      {cuda && (
        <p className="mb-3 text-xs text-slate-500">
          GPU: <span className="text-slate-300">{health.hardware.cuda_device_name}</span>
        </p>
      )}

      <div className="space-y-2">
        {MODULES.map((mod) => (
          <div
            key={mod.key}
            className="flex items-center justify-between rounded-lg border border-white/5 bg-white/[0.02] px-3 py-2"
          >
            <span className="text-sm text-slate-300">{mod.name}</span>
            <CheckCircle className={`h-4 w-4 ${online ? "text-emerald-400" : "text-slate-600"}`} />
          </div>
        ))}
      </div>
    </motion.div>
  );
}

export default memo(SystemHealthWidget);
