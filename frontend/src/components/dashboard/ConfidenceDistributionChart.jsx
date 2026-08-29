import { memo } from "react";
import { motion } from "framer-motion";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AXIS_TICK, GRID_STROKE, TOOLTIP_STYLE } from "./chartTheme";

const BUCKET_COLORS = ["#22c55e", "#84cc16", "#f59e0b", "#f97316", "#ef4444"];

function ConfidenceDistributionChart({ data = [], delay = 0.3 }) {
  const chartData = data.length
    ? data
    : [
        { label: "0–20%", count: 0 },
        { label: "21–40%", count: 0 },
        { label: "41–60%", count: 0 },
        { label: "61–80%", count: 0 },
        { label: "81–100%", count: 0 },
      ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="command-panel h-full rounded-2xl p-5 md:p-6"
    >
      <div className="mb-4">
        <h3 className="font-display text-base font-semibold text-white">AI Confidence Distribution</h3>
        <p className="text-xs text-slate-500">Model confidence buckets across completed analyses</p>
      </div>
      <div className="h-56 w-full sm:h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} vertical={false} />
            <XAxis dataKey="label" tick={AXIS_TICK} axisLine={false} tickLine={false} />
            <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={28} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Bar dataKey="count" name="Analyses" radius={[4, 4, 0, 0]} maxBarSize={40}>
              {chartData.map((_, i) => (
                <Cell key={i} fill={BUCKET_COLORS[i % BUCKET_COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}

export default memo(ConfidenceDistributionChart);
