function ProgressBar({

  value = 0,

  max = 100,

  label,

  showPercent = true,

  color = "blue",

  className = "",

}) {

  const percent =
    Math.min(100, Math.max(0, (value / max) * 100));


  const colorMap = {

    blue: "bg-blue-500",

    green: "bg-emerald-500",

    red: "bg-red-500",

    amber: "bg-amber-500",

    purple: "bg-purple-500",

  };


  return (

    <div className={`w-full ${className}`}>

      {(label || showPercent) && (

        <div className="mb-2 flex items-center justify-between text-sm">

          {label && (
            <span className="text-slate-400">{label}</span>
          )}

          {showPercent && (
            <span className="font-medium text-slate-300">
              {percent.toFixed(0)}%
            </span>
          )}

        </div>

      )}


      <div className="h-2 overflow-hidden rounded-full bg-slate-800">

        <div
          className={`h-full rounded-full transition-all duration-700 ease-out ${colorMap[color] || colorMap.blue}`}
          style={{ width: `${percent}%` }}
          role="progressbar"
          aria-valuenow={percent}
          aria-valuemin={0}
          aria-valuemax={100}
        />

      </div>

    </div>

  );

}

export default ProgressBar;
