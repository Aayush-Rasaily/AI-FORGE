import { memo } from "react";
import { motion } from "framer-motion";
import { User } from "lucide-react";

function InvestigatorActivityPanel({ activity = [], delay = 0.3 }) {
  const items = activity.length ? activity : [{ name: "No activity yet", cases: 0 }];
  const max = Math.max(1, ...items.map((a) => a.cases || 0));

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="command-panel h-full rounded-2xl p-5 md:p-6"
    >
      <div className="mb-4">
        <h3 className="font-display text-base font-semibold text-white">Investigator Activity</h3>
        <p className="text-xs text-slate-500">Recent case ownership and completed assignments</p>
      </div>

      <div className="space-y-3">
        {items.map((inv, i) => (
          <motion.div
            key={inv.name}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: delay + i * 0.04 }}
            className="flex items-center gap-3"
          >
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-white/5 bg-white/5">
              <User className="h-4 w-4 text-cyan-400/80" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-2">
                <p className="truncate text-sm font-medium text-slate-200">{inv.name}</p>
                <span className="shrink-0 text-xs font-semibold text-cyan-400">{inv.cases}</span>
              </div>
              <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-slate-800">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-500"
                  style={{ width: `${((inv.cases || 0) / max) * 100}%` }}
                />
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}

export default memo(InvestigatorActivityPanel);
