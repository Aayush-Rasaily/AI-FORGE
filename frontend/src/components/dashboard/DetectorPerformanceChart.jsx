import { memo, useMemo } from "react";
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

function DetectorPerformanceChart({ detectors = [], delay = 0.2 }) {
  const data = useMemo(() => {
    if (!detectors?.length) {
      return [
        { name: "ELA", f1: 0 },
        { name: "Noise", f1: 0 },
        { name: "Wavelet", f1: 0 },
      ];
    }
    return detectors.slice(0, 10).map((d) => ({
      name: String(d.detector || d.name || "—").replace(/_/g, " ").slice(0, 12),
      f1: Math.round((Number(d.f1 ?? d.weight ?? d.accuracy ?? 0)) * 100),
      precision: Math.round((Number(d.precision ?? 0)) * 100),
    }));
  }, [detectors]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="command-panel h-full rounded-2xl p-5 md:p-6"
    >
      <div className="mb-4">
        <h3 className="font-display text-base font-semibold text-white">Detector Performance</h3>
        <p className="text-xs text-slate-500">F1 score from benchmark evaluation</p>
      </div>
      <div className="h-56 w-full sm:h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} vertical={false} />
            <XAxis dataKey="name" tick={AXIS_TICK} axisLine={false} tickLine={false} interval={0} angle={-20} textAnchor="end" height={48} />
            <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={32} domain={[0, 100]} />
            <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v) => [`${v}%`, "F1"]} />
            <Bar dataKey="f1" name="F1 Score" fill={CHART_COLORS.cyan} radius={[4, 4, 0, 0]} maxBarSize={36} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}

export default memo(DetectorPerformanceChart);
