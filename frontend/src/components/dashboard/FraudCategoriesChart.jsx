import { memo, useMemo } from "react";
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
import { AXIS_TICK, CHART_COLORS, GRID_STROKE, TOOLTIP_STYLE } from "./chartTheme";

const CATEGORY_COLORS = [
  CHART_COLORS.red,
  CHART_COLORS.amber,
  CHART_COLORS.purple,
  CHART_COLORS.cyan,
  CHART_COLORS.emerald,
  CHART_COLORS.blue,
];

function FraudCategoriesChart({ categories = {}, delay = 0.25 }) {
  const data = useMemo(() => {
    const entries = Object.entries(categories || {});
    if (!entries.length) return [{ name: "No data", count: 0 }];
    return entries
      .map(([name, count]) => ({ name, count: Number(count) || 0 }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 8);
  }, [categories]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="command-panel h-full rounded-2xl p-5 md:p-6"
    >
      <div className="mb-4">
        <h3 className="font-display text-base font-semibold text-white">Fraud Categories</h3>
        <p className="text-xs text-slate-500">Verdict classification across analyses</p>
      </div>
      <div className="h-56 w-full sm:h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ left: 8, right: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} horizontal={false} />
            <XAxis type="number" tick={AXIS_TICK} axisLine={false} tickLine={false} />
            <YAxis
              type="category"
              dataKey="name"
              tick={AXIS_TICK}
              axisLine={false}
              tickLine={false}
              width={88}
            />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Bar dataKey="count" name="Analyses" radius={[0, 4, 4, 0]} maxBarSize={18}>
              {data.map((_, i) => (
                <Cell key={i} fill={CATEGORY_COLORS[i % CATEGORY_COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}

export default memo(FraudCategoriesChart);
