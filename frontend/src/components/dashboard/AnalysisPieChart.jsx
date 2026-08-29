import { memo, useMemo } from "react";
import { motion } from "framer-motion";
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { EVIDENCE_COLORS, TOOLTIP_STYLE } from "./chartTheme";

const TYPE_LABELS = {
  image: "Image",
  document: "Document",
  signature: "Signature",
  video: "Video",
  pdf: "PDF",
  unknown: "Other",
};

function AnalysisPieChart({ evidenceByType = {}, delay = 0.2 }) {
  const data = useMemo(() => {
    const entries = Object.entries(evidenceByType || {});
    if (!entries.length) {
      return [
        { name: "Image", value: 0, color: EVIDENCE_COLORS.image },
        { name: "Document", value: 0, color: EVIDENCE_COLORS.document },
      ];
    }
    return entries.map(([key, value]) => ({
      name: TYPE_LABELS[key] || key.charAt(0).toUpperCase() + key.slice(1),
      value: Number(value) || 0,
      color: EVIDENCE_COLORS[key] || EVIDENCE_COLORS.unknown,
    }));
  }, [evidenceByType]);

  const total = data.reduce((s, d) => s + d.value, 0);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="command-panel h-full rounded-2xl p-5 md:p-6"
    >
      <div className="mb-2 flex items-start justify-between">
        <div>
          <h3 className="font-display text-base font-semibold text-white">Evidence Types</h3>
          <p className="text-xs text-slate-500">Distribution across intake pipeline</p>
        </div>
        <span className="rounded-lg bg-cyan-500/10 px-2 py-1 text-xs font-semibold text-cyan-400">
          {total} total
        </span>
      </div>
      <div className="h-56 sm:h-64">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={52}
              outerRadius={78}
              paddingAngle={3}
              dataKey="value"
            >
              {data.map((entry) => (
                <Cell key={entry.name} fill={entry.color} stroke="transparent" />
              ))}
            </Pie>
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Legend wrapperStyle={{ fontSize: "11px", color: "#94a3b8" }} />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}

export default memo(AnalysisPieChart);
