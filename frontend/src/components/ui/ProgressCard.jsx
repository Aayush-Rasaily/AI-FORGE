import { useEffect, useState } from "react";
import { motion } from "framer-motion";

/* ========================================= */
/* Animated counter hook                       */
/* ========================================= */

function useAnimatedNumber(target, duration = 1200) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    const start = performance.now();
    const from = 0;

    function tick(now) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(from + (target - from) * eased);

      if (progress < 1) {
        requestAnimationFrame(tick);
      }
    }

    requestAnimationFrame(tick);
  }, [target, duration]);

  return value;
}

/* ========================================= */
/* Progress Card — module score display        */
/* ========================================= */

function getStatus(score) {
  if (score >= 61) return { label: "High", color: "text-red-400", bar: "bg-red-500" };
  if (score >= 31) return { label: "Medium", color: "text-orange-400", bar: "bg-orange-500" };
  return { label: "Low", color: "text-emerald-400", bar: "bg-emerald-500" };
}

function ProgressCard({ icon: Icon, title, score = 0, delay = 0, subtitle = "" }) {
  const normalized = Math.min(100, Math.max(0, Number(score) || 0));
  const animated = useAnimatedNumber(normalized);
  const status = getStatus(normalized);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4 }}
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
      className="group rounded-2xl border border-[#1F2937] bg-[#111827] p-5 shadow-lg transition-shadow hover:shadow-blue-500/10 hover:border-blue-500/30"
    >
      <div className="flex items-start justify-between">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500/10 border border-blue-500/20 transition group-hover:bg-blue-500/20">
          {Icon && <Icon className="h-5 w-5 text-blue-400" />}
        </div>
        <span className={`text-xs font-semibold uppercase tracking-wide ${status.color}`}>
          {status.label}
        </span>
      </div>

      <h4 className="mt-4 text-sm font-medium text-slate-400">{title}</h4>

      <p className="mt-1 text-2xl font-bold text-white">
        {animated.toFixed(1)}%
      </p>

      <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-800">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${normalized}%` }}
          transition={{ delay: delay + 0.2, duration: 1, ease: "easeOut" }}
          className={`h-full rounded-full ${status.bar}`}
        />
      </div>
      {subtitle ? (
        <p className="mt-3 text-xs leading-relaxed text-slate-500 line-clamp-3">{subtitle}</p>
      ) : null}
    </motion.div>
  );
}

export default ProgressCard;
