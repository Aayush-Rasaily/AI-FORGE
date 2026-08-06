import { motion } from "framer-motion";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";

const DATA = [
  { name: "Image", value: 42, color: "#3b82f6" },
  { name: "Document", value: 28, color: "#22c55e" },
  { name: "Signature", value: 18, color: "#a855f7" },
  { name: "Video", value: 12, color: "#ef4444" },
];

function AnalysisPieChart() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
      className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-6 backdrop-blur-xl"
    >
      <h3 className="text-lg font-semibold text-white">Analysis Distribution</h3>
      <p className="mt-1 text-xs text-slate-500">Evidence types processed this week</p>

      <div className="mt-4 h-64">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={DATA}
              cx="50%"
              cy="50%"
              innerRadius={55}
              outerRadius={85}
              paddingAngle={4}
              dataKey="value"
            >
              {DATA.map((entry) => (
                <Cell key={entry.name} fill={entry.color} stroke="transparent" />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                background: "#111827",
                border: "1px solid #1F2937",
                borderRadius: "12px",
                color: "#f8fafc",
              }}
            />
            <Legend
              wrapperStyle={{ fontSize: "12px", color: "#94a3b8" }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}

export default AnalysisPieChart;
