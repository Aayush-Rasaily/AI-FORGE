import { memo } from "react";
import { motion } from "framer-motion";

function KPIWidget({
  label,
  value,
  sublabel,
  icon: Icon,
  accent = "cyan",
  delay = 0,
  trend,
  trendUp,
}) {
  const styles = {
    cyan: {
      card: "border-cyan-500/20",
      bg: "from-cyan-500/20 to-blue-500/5",
      icon: "text-cyan-400 border-cyan-500/20",
    },
    red: {
      card: "border-red-500/20",
      bg: "from-red-500/20 to-orange-500/5",
      icon: "text-red-400 border-red-500/20",
    },
    emerald: {
      card: "border-emerald-500/20",
      bg: "from-emerald-500/20 to-green-500/5",
      icon: "text-emerald-400 border-emerald-500/20",
    },
    purple: {
      card: "border-purple-500/20",
      bg: "from-purple-500/20 to-violet-500/5",
      icon: "text-purple-400 border-purple-500/20",
    },
    amber: {
      card: "border-amber-500/20",
      bg: "from-amber-500/20 to-yellow-500/5",
      icon: "text-amber-400 border-amber-500/20",
    },
    blue: {
      card: "border-blue-500/20",
      bg: "from-blue-500/20 to-indigo-500/5",
      icon: "text-blue-400 border-blue-500/20",
    },
  };

  const s = styles[accent] || styles.cyan;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay }}
      className={`command-widget relative overflow-hidden rounded-2xl border bg-gradient-to-br p-5 ${s.card}`}
      style={{ willChange: "transform, opacity" }}
    >
      <div className={`pointer-events-none absolute inset-0 bg-gradient-to-br opacity-60 ${s.bg}`} />
      <div className="relative flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            {label}
          </p>
          <p className="mt-1.5 font-display text-2xl font-bold tracking-tight text-white sm:text-3xl">
            {value}
          </p>
          {sublabel && (
            <p className="mt-1 text-xs text-slate-400">{sublabel}</p>
          )}
          {trend && (
            <p className={`mt-1.5 text-xs font-medium ${trendUp ? "text-emerald-400" : "text-slate-500"}`}>
              {trend}
            </p>
          )}
        </div>
        {Icon && (
          <div className={`shrink-0 rounded-xl border bg-black/20 p-2.5 ${s.icon}`}>
            <Icon className="h-5 w-5" />
          </div>
        )}
      </div>
    </motion.div>
  );
}

export default memo(KPIWidget);
