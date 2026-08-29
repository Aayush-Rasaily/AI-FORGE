import { memo } from "react";
import { motion } from "framer-motion";

const BLOCK_LABELS = ["0–4h", "4–8h", "8–12h", "12–16h", "16–20h", "20–24h"];

function dayLabelsForRows() {
  const labels = [];
  const today = new Date();
  for (let i = 6; i >= 0; i -= 1) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    labels.push(d.toLocaleDateString("en", { weekday: "short" }));
  }
  return labels;
}

function cellColor(value, max) {
  if (!value) return "rgba(30, 41, 59, 0.5)";
  const intensity = max > 0 ? value / max : 0;
  if (intensity > 0.75) return "rgba(6, 182, 212, 0.9)";
  if (intensity > 0.5) return "rgba(6, 182, 212, 0.65)";
  if (intensity > 0.25) return "rgba(59, 130, 246, 0.5)";
  return "rgba(59, 130, 246, 0.25)";
}

function ActivityHeatmap({ matrix = [], delay = 0.35 }) {
  const rows = matrix.length ? matrix : Array.from({ length: 7 }, () => Array(6).fill(0));
  const max = Math.max(1, ...rows.flat());
  const dayLabels = dayLabelsForRows();

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="command-panel h-full rounded-2xl p-5 md:p-6"
    >
      <div className="mb-4">
        <h3 className="font-display text-base font-semibold text-white">Activity Heatmap</h3>
        <p className="text-xs text-slate-500">Analysis volume by day and time block (7 days)</p>
      </div>

      <div className="overflow-x-auto">
        <div className="min-w-[280px]">
          <div className="mb-2 grid grid-cols-[2.5rem_repeat(6,1fr)] gap-1 text-[9px] text-slate-600">
            <div />
            {BLOCK_LABELS.map((b) => (
              <div key={b} className="text-center">{b}</div>
            ))}
          </div>
          {rows.map((row, ri) => (
            <div key={ri} className="mb-1 grid grid-cols-[2.5rem_repeat(6,1fr)] gap-1">
              <div className="flex items-center text-[10px] font-medium text-slate-500">
                {dayLabels[ri] || `D${ri + 1}`}
              </div>
              {row.map((val, ci) => (
                <div
                  key={ci}
                  title={`${val} analyses`}
                  className="aspect-[2/1] rounded-md transition-colors"
                  style={{ backgroundColor: cellColor(val, max) }}
                />
              ))}
            </div>
          ))}
        </div>
      </div>

      <div className="mt-3 flex items-center justify-end gap-2 text-[10px] text-slate-500">
        <span>Low</span>
        <div className="flex gap-0.5">
          {[0.15, 0.35, 0.55, 0.85].map((o) => (
            <div
              key={o}
              className="h-3 w-5 rounded-sm"
              style={{ backgroundColor: `rgba(6, 182, 212, ${o})` }}
            />
          ))}
        </div>
        <span>High</span>
      </div>
    </motion.div>
  );
}

export default memo(ActivityHeatmap);
