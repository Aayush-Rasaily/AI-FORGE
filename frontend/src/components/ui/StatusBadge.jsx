/* ========================================= */
/* Status Badge Component                    */
/* Maps verdict/status to color variants     */
/* ========================================= */

const STATUS_VARIANTS = {

  success: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",

  warning: "bg-amber-500/15 text-amber-400 border-amber-500/30",

  danger: "bg-red-500/15 text-red-400 border-red-500/30",

  info: "bg-blue-500/15 text-blue-400 border-blue-500/30",

  neutral: "bg-slate-500/15 text-slate-400 border-slate-500/30",

};


function resolveVariant(status) {

  if (!status) {
    return "neutral";
  }


  const normalized = String(status).toLowerCase();


  if (
    normalized.includes("authentic") ||
    normalized.includes("genuine") ||
    normalized.includes("low") ||
    normalized.includes("clean") ||
    normalized.includes("match")
  ) {
    return "success";
  }


  if (
    normalized.includes("suspicious") ||
    normalized.includes("medium") ||
    normalized.includes("uncertain")
  ) {
    return "warning";
  }


  if (
    normalized.includes("forged") ||
    normalized.includes("fake") ||
    normalized.includes("high") ||
    normalized.includes("manipulated") ||
    normalized.includes("detected") ||
    normalized.includes("mismatch")
  ) {
    return "danger";
  }


  return "info";

}


function StatusBadge({ status, label, variant }) {

  const resolvedVariant =
    variant || resolveVariant(status);


  const displayLabel =
    label || status || "Unknown";


  return (

    <span
      className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide ${STATUS_VARIANTS[resolvedVariant]}`}
    >

      {displayLabel}

    </span>

  );

}

export default StatusBadge;
