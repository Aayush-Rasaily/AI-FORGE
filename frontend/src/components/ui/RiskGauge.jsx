import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";

/* ========================================= */
/* Color rules: 0-30 green, 31-60 orange,    */
/*              61-100 red                     */
/* ========================================= */

function getRiskColor(score, invert = false) {
  const effective = invert ? 100 - score : score;
  if (effective >= 61) return "#ef4444";
  if (effective >= 31) return "#f97316";
  return "#22c55e";
}

function getRiskLabel(score, invert = false) {
  const effective = invert ? 100 - score : score;
  if (effective >= 61) return "High Risk";
  if (effective >= 31) return "Medium Risk";
  return "Low Risk";
}

function useAnimatedScore(target, duration = 1400) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    const start = performance.now();

    function tick(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(target * eased);
      if (progress < 1) requestAnimationFrame(tick);
    }

    requestAnimationFrame(tick);
  }, [target, duration]);

  return value;
}

function RiskGauge({ score = 0, size = 200, label = "Overall Risk", invert = false }) {
  const normalized = Math.min(100, Math.max(0, Number(score) || 0));
  const animated = useAnimatedScore(normalized);
  const color = getRiskColor(animated, invert);

  const data = [
    { value: animated },
    { value: 100 - animated },
  ];

  return (
    <div className="flex flex-col items-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        style={{ width: size, height: size }}
        className="relative"
      >
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              startAngle={220}
              endAngle={-40}
              innerRadius="72%"
              outerRadius="90%"
              paddingAngle={0}
              dataKey="value"
              stroke="none"
            >
              <Cell fill={color} />
              <Cell fill="rgba(31,41,55,0.6)" />
            </Pie>
          </PieChart>
        </ResponsiveContainer>

        <div
          className="absolute inset-0 flex flex-col items-center justify-center"
        >
          <motion.span
            className="text-4xl font-bold"
            style={{ color }}
            key={Math.round(animated)}
          >
            {Math.round(animated)}
          </motion.span>
          <span className="text-xs text-slate-500">/ 100</span>
        </div>
      </motion.div>

      {label && (
        <p className="mt-3 text-sm font-semibold text-slate-300">{label}</p>
      )}

      <p
        className="mt-1 text-xs font-bold uppercase tracking-widest"
        style={{ color }}
      >
        {getRiskLabel(normalized, invert)}
      </p>
    </div>
  );
}

export default RiskGauge;
