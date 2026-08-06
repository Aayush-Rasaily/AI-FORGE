import { FileText, ListOrdered } from "lucide-react";

function InvestigationReport({ fusion }) {
  const report = fusion?.report || {};
  const ranking = fusion?.evidence_ranking || [];

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-6">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-purple-400" />
          <h3 className="text-lg font-bold text-white">
            {report.title || "Final Investigation Report"}
          </h3>
        </div>

        <p className="mt-4 text-sm leading-relaxed text-slate-300">
          {report.summary}
        </p>

        <p className="mt-3 text-xs text-slate-500">{report.methodology}</p>

        {report.recommendations?.length > 0 && (
          <div className="mt-5">
            <p className="text-xs font-semibold uppercase tracking-wider text-purple-400">
              Recommendations
            </p>
            <ul className="mt-2 space-y-1.5">
              {report.recommendations.map((rec, i) => (
                <li key={i} className="text-xs text-slate-400">
                  • {rec}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {ranking.length > 0 && (
        <div className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-6">
          <div className="flex items-center gap-2">
            <ListOrdered className="h-5 w-5 text-purple-400" />
            <h3 className="text-lg font-bold text-white">Evidence Ranking</h3>
          </div>
          <div className="mt-4 space-y-2">
            {ranking.map((item) => (
              <div
                key={item.rank}
                className="flex items-start gap-3 rounded-lg border border-[#1F2937] bg-[#0B1220] p-3"
              >
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-purple-500/20 text-xs font-bold text-purple-300">
                  {item.rank}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium text-white">{item.finding}</p>
                  <p className="mt-0.5 text-[10px] text-slate-500">
                    {item.source} · {item.module} ·{" "}
                    {Math.round((item.confidence || 0) * 100)}% confidence
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default InvestigationReport;
