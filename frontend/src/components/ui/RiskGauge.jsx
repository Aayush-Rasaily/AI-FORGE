import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";

/* ========================================= */
/* Risk Gauge — circular score indicator     */
/* ========================================= */

function getRiskColor(score) {

  if (score >= 70) {
    return "#ef4444";
  }

  if (score >= 40) {
    return "#f59e0b";
  }

  return "#22c55e";

}


function getRiskLabel(score) {

  if (score >= 70) {
    return "High Risk";
  }

  if (score >= 40) {
    return "Medium Risk";
  }

  return "Low Risk";

}


function RiskGauge({ score = 0, size = 180, label = "Risk Score" }) {

  const normalizedScore =
    Math.min(100, Math.max(0, Number(score) || 0));


  const data = [
    { value: normalizedScore },
    { value: 100 - normalizedScore },
  ];


  const color = getRiskColor(normalizedScore);


  return (

    <div className="flex flex-col items-center">

      <div style={{ width: size, height: size }}>

        <ResponsiveContainer width="100%" height="100%">

          <PieChart>

            <Pie
              data={data}
              cx="50%"
              cy="50%"
              startAngle={220}
              endAngle={-40}
              innerRadius="70%"
              outerRadius="90%"
              paddingAngle={0}
              dataKey="value"
              stroke="none"
            >

              <Cell fill={color} />

              <Cell fill="rgba(51, 65, 85, 0.4)" />

            </Pie>

          </PieChart>

        </ResponsiveContainer>


        {/* Center Score Overlay */}

        <div
          className="relative -mt-full flex flex-col items-center justify-center"
          style={{ height: size }}
        >

          <span
            className="text-3xl font-bold"
            style={{ color }}
          >

            {normalizedScore.toFixed(0)}

          </span>

          <span className="text-xs text-slate-400">
            / 100
          </span>

        </div>

      </div>


      <p className="mt-2 text-sm font-medium text-slate-300">
        {label}
      </p>


      <p
        className="mt-1 text-xs font-semibold uppercase tracking-wide"
        style={{ color }}
      >

        {getRiskLabel(normalizedScore)}

      </p>

    </div>

  );

}

export default RiskGauge;
