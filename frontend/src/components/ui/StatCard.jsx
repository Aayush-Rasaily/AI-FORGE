function StatCard({

  label,

  value,

  icon: Icon,

  gradient = "blue",

  trend,

}) {

  return (

    <div className={`glass-card rounded-xl p-6 gradient-card-${gradient}`}>

      <div className="flex items-start justify-between">

        <div>

          <p className="text-sm font-medium text-slate-400">
            {label}
          </p>

          <p className="mt-2 text-3xl font-bold text-white">
            {value}
          </p>

          {trend && (
            <p className="mt-1 text-xs text-slate-500">
              {trend}
            </p>
          )}

        </div>


        {Icon && (

          <div className="rounded-lg bg-white/5 p-2.5">

            <Icon className="h-5 w-5 text-slate-400" aria-hidden="true" />

          </div>

        )}

      </div>

    </div>

  );

}

export default StatCard;
