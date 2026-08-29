import { memo } from "react";
import { motion } from "framer-motion";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AXIS_TICK, CHART_COLORS, GRID_STROKE, TOOLTIP_STYLE } from "./chartTheme";

function MonthlyCasesChart({ data = [], delay = 0.1 }) {
  const chartData = data.length
    ? data
    : [{ label: "—", cases: 0, high_risk: 0 }];

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="command-panel h-full rounded-2xl p-5 md:p-6"
    >
      <div className="mb-4">
        <h3 className="font-display text-base font-semibold text-white">Monthly Cases</h3>
        <p className="text-xs text-slate-500">Case intake vs high-risk analyses (6 months)</p>
      </div>
      <div className="h-56 w-full sm:h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} barGap={4}>
            <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} vertical={false} />
            <XAxis dataKey="label" tick={AXIS_TICK} axisLine={false} tickLine={false} />
            <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={28} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Bar dataKey="cases" name="Cases" fill={CHART_COLORS.blue} radius={[4, 4, 0, 0]} maxBarSize={32} />
            <Bar dataKey="high_risk" name="High Risk" fill={CHART_COLORS.red} radius={[4, 4, 0, 0]} maxBarSize={32} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}

export default memo(MonthlyCasesChart);
