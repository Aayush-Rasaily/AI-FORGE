import { motion } from "framer-motion";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

const DATA = [
  { day: "Mon", cases: 4, flagged: 1 },
  { day: "Tue", cases: 7, flagged: 2 },
  { day: "Wed", cases: 5, flagged: 3 },
  { day: "Thu", cases: 12, flagged: 4 },
  { day: "Fri", cases: 9, flagged: 2 },
  { day: "Sat", cases: 3, flagged: 1 },
  { day: "Sun", cases: 6, flagged: 2 },
];

function FraudTrendChart() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
      className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-6 backdrop-blur-xl"
    >
      <h3 className="text-lg font-semibold text-white">Fraud Detection Trends</h3>
      <p className="mt-1 text-xs text-slate-500">Weekly analysis volume & flagged cases</p>

      <div className="mt-6 h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={DATA}>
            <defs>
              <linearGradient id="casesGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="flaggedGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#ef4444" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#ef4444" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" />
            <XAxis dataKey="day" tick={{ fill: "#64748b", fontSize: 12 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: "#64748b", fontSize: 12 }} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={{
                background: "#111827",
                border: "1px solid #1F2937",
                borderRadius: "12px",
                color: "#f8fafc",
              }}
            />
            <Area type="monotone" dataKey="cases" stroke="#3b82f6" fill="url(#casesGrad)" strokeWidth={2} />
            <Area type="monotone" dataKey="flagged" stroke="#ef4444" fill="url(#flaggedGrad)" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}

export default FraudTrendChart;
