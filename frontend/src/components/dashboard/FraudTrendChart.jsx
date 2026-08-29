import { memo } from "react";
import { motion } from "framer-motion";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AXIS_TICK, GRID_STROKE, TOOLTIP_STYLE } from "./chartTheme";

const FALLBACK = [
  { day: "Mon", cases: 0, flagged: 0, evidence: 0 },
  { day: "Tue", cases: 0, flagged: 0, evidence: 0 },
  { day: "Wed", cases: 0, flagged: 0, evidence: 0 },
  { day: "Thu", cases: 0, flagged: 0, evidence: 0 },
  { day: "Fri", cases: 0, flagged: 0, evidence: 0 },
  { day: "Sat", cases: 0, flagged: 0, evidence: 0 },
  { day: "Sun", cases: 0, flagged: 0, evidence: 0 },
];

function FraudTrendChart({ data, delay = 0.15 }) {
  const chartData = data?.length ? data : FALLBACK;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="command-panel h-full rounded-2xl p-5 md:p-6"
    >
      <div className="mb-4">
        <h3 className="font-display text-base font-semibold text-white">Investigation Timeline</h3>
        <p className="text-xs text-slate-500">7-day case volume, flagged analyses & evidence intake</p>
      </div>
      <div className="h-56 w-full sm:h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="casesGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.35} />
                <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="flaggedGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#ef4444" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#ef4444" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} vertical={false} />
            <XAxis dataKey="day" tick={AXIS_TICK} axisLine={false} tickLine={false} />
            <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={28} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Area type="monotone" dataKey="cases" name="Cases" stroke="#3b82f6" fill="url(#casesGrad)" strokeWidth={2} />
            <Area type="monotone" dataKey="flagged" name="High Risk" stroke="#ef4444" fill="url(#flaggedGrad)" strokeWidth={2} />
            <Area type="monotone" dataKey="evidence" name="Evidence" stroke="#06b6d4" fill="transparent" strokeWidth={1.5} strokeDasharray="4 4" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}

export default memo(FraudTrendChart);
