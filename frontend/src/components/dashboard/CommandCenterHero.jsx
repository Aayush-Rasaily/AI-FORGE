import { memo } from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  Radio,
  Shield,
  Zap,
} from "lucide-react";
import { useAnimatedCounter } from "../../hooks/useAnimatedCounter";

function CommandCenterHero({
  totalCases = 0,
  highRisk = 0,
  detectorAccuracy = null,
  backendOnline = false,
  device = "—",
}) {
  const cases = useAnimatedCounter(Number(totalCases) || 0);
  const risk = useAnimatedCounter(Number(highRisk) || 0);
  const accuracy = useAnimatedCounter(
    detectorAccuracy != null ? Math.round(detectorAccuracy * 100) : backendOnline ? 0 : 0
  );

  return (
    <motion.section
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45 }}
      className="command-hero relative mb-8 overflow-hidden rounded-2xl border border-white/5 p-6 md:p-8"
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(6,182,212,0.12),transparent_55%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,rgba(59,130,246,0.08),transparent_50%)]" />

      <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
        <div className="max-w-2xl">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-widest text-cyan-300">
              <Radio className="h-3 w-3" />
              Command Center
            </span>
            <span
              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[11px] font-medium ${
                backendOnline
                  ? "border border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                  : "border border-red-500/30 bg-red-500/10 text-red-400"
              }`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${backendOnline ? "bg-emerald-400 animate-pulse" : "bg-red-400"}`} />
              {backendOnline ? "Live" : "Offline"}
            </span>
          </div>

          <h1 className="font-display text-2xl font-bold tracking-tight text-white md:text-4xl">
            Enterprise Fraud Intelligence
            <span className="block bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
              Operations Dashboard
            </span>
          </h1>
          <p className="mt-3 max-w-xl text-sm leading-relaxed text-slate-400 md:text-base">
            Real-time case throughput, detector performance, and system health —
            unified for investigators and compliance teams.
          </p>

          <div className="mt-5 flex flex-wrap items-center gap-3">
            <Link
              to="/investigation"
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-cyan-500/20 transition hover:shadow-cyan-500/30"
            >
              Launch Investigation
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              to="/cases"
              className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-5 py-2.5 text-sm font-medium text-slate-300 transition hover:border-cyan-500/30 hover:text-white"
            >
              Case Management
            </Link>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3 sm:gap-4">
          {[
            { label: "Cases", value: cases, icon: Shield },
            { label: "High Risk", value: risk, icon: Zap },
            {
              label: "Detector Acc.",
              value: detectorAccuracy != null ? `${accuracy}%` : "—",
              icon: Radio,
            },
          ].map((item) => (
            <div
              key={item.label}
              className="rounded-xl border border-white/5 bg-black/25 px-4 py-3 backdrop-blur-sm"
            >
              <item.icon className="mb-2 h-4 w-4 text-cyan-400/80" />
              <p className="font-display text-xl font-bold text-white md:text-2xl">
                {item.value}
              </p>
              <p className="text-[10px] font-medium uppercase tracking-wider text-slate-500">
                {item.label}
              </p>
            </div>
          ))}
        </div>
      </div>

      <div className="relative mt-5 flex flex-wrap gap-4 border-t border-white/5 pt-4 text-xs text-slate-500">
        <span>Runtime: <span className="text-slate-300 capitalize">{device}</span></span>
        <span>Refresh: <span className="text-slate-300">10s health probe</span></span>
      </div>
    </motion.section>
  );
}

export default memo(CommandCenterHero);
