import { motion, AnimatePresence } from "framer-motion";
import { RefreshCw } from "lucide-react";
import { useBackend } from "../../context/BackendConnectivity";

/**
 * BackendStatus — Online when /api/health is healthy.
 * Offline only when health AND report AND analysis probes all fail.
 */
function BackendStatus({ className = "" }) {
  const { status, refreshHealth, backendOnline } = useBackend();

  const config = {
    connecting: {
      dot: "bg-amber-400",
      ring: "shadow-amber-400/30",
      label: "Connecting...",
      tooltip: "Connecting to AI backend (health check)…",
      text: "text-amber-400",
      bg: "bg-amber-500/10",
    },
    online: {
      dot: "bg-emerald-400",
      ring: "shadow-emerald-400/50",
      label: "Online",
      tooltip: "AI Backend Connected (GET /api/health)",
      text: "text-emerald-400",
      bg: "bg-emerald-500/10",
    },
    offline: {
      dot: "bg-red-400",
      ring: "shadow-red-400/50",
      label: "Offline",
      tooltip: "Health check failed — click to reconnect",
      text: "text-red-400",
      bg: "bg-red-500/10",
    },
  };

  const current = config[status] || config.connecting;

  return (
    <button
      type="button"
      onClick={refreshHealth}
      className={`group relative flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium transition hover:brightness-110 ${current.bg} ${current.text} ${className}`}
      title={current.tooltip}
      aria-label={current.tooltip}
      data-backend-online={backendOnline ? "true" : "false"}
    >
      <span className="relative flex h-2.5 w-2.5">
        <AnimatePresence mode="wait">
          {status !== "connecting" && (
            <motion.span
              key={status}
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: [1, 1.6, 1], opacity: [0.7, 0, 0.7] }}
              transition={{ duration: 2, repeat: Infinity }}
              className={`absolute inline-flex h-full w-full rounded-full ${current.dot} opacity-60`}
            />
          )}
        </AnimatePresence>
        {status === "connecting" ? (
          <RefreshCw className="relative h-2.5 w-2.5 animate-spin text-amber-400" />
        ) : (
          <span
            className={`relative inline-flex h-2.5 w-2.5 rounded-full ${current.dot} shadow-lg ${current.ring}`}
          />
        )}
      </span>

      <span className="hidden sm:inline">{current.label}</span>

      <div className="pointer-events-none absolute -bottom-9 right-0 z-50 whitespace-nowrap rounded-md border border-[#1F2937] bg-[#111827] px-2.5 py-1 text-[10px] text-slate-300 opacity-0 shadow-lg transition-opacity group-hover:opacity-100">
        {current.tooltip}
      </div>
    </button>
  );
}

export default BackendStatus;
