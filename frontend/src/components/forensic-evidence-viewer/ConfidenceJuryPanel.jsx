import { Gauge, Scale } from "lucide-react";
import RiskGauge from "../ui/RiskGauge";
import { translateVerdict } from "./forensicTranslator";

function ConfidenceJuryPanel({
  confidence = 75,
  forgeryProbability,
  jury,
  riskScore,
}) {
  const conf = Number(confidence) > 1 ? Number(confidence) : Number(confidence) * 100;
  const risk =
    riskScore != null
      ? Number(riskScore) > 1
        ? Number(riskScore)
        : Number(riskScore) * 100
      : forgeryProbability != null
        ? Number(forgeryProbability)
        : null;

  const fusion = jury?.fusion || jury || {};
  const verdict =
    fusion.verdict ||
    fusion.final_verdict ||
    fusion.majority_vote?.majority_label ||
    fusion.risk_level ||
    null;

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-5">
        <div className="mb-3 flex items-center gap-2">
          <Gauge className="h-4 w-4 text-emerald-400" />
          <h3 className="text-sm font-semibold text-white">Confidence</h3>
        </div>
        <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-around">
          <RiskGauge score={Math.round(conf)} size={130} label="Detector Confidence" invert />
          {risk != null && (
            <RiskGauge score={Math.round(risk)} size={130} label="Forgery Probability" />
          )}
        </div>
      </div>

      <div className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-5">
        <div className="mb-3 flex items-center gap-2">
          <Scale className="h-4 w-4 text-violet-400" />
          <h3 className="text-sm font-semibold text-white">AI Jury</h3>
        </div>
        {verdict ? (
          <div className="space-y-2 text-sm">
            {/* Plain-language verdict — primary */}
            <div className="rounded-xl border border-[#1F2937] bg-[#0B1120]/80 px-3.5 py-3">
              <p className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">AI Assessment</p>
              <p className="font-semibold leading-snug text-white">
                {translateVerdict(verdict) || verdict}
              </p>
            </div>
            {fusion.risk_level && (
              <p className="text-xs text-slate-400">Severity level: {fusion.risk_level.replace(/_/g, " ")}</p>
            )}
            {fusion.majority_opinion && (
              <p className="text-xs leading-relaxed text-slate-300">{fusion.majority_opinion}</p>
            )}
            {fusion.confidence != null && (
              <p className="text-xs text-slate-500">
                The AI is{" "}
                {Number(fusion.confidence) > 1
                  ? Number(fusion.confidence).toFixed(1)
                  : (Number(fusion.confidence) * 100).toFixed(1)}
                % certain of this assessment.
              </p>
            )}
          </div>
        ) : (
          <p className="text-sm text-slate-500">AI Jury synthesis unavailable for this evidence.</p>
        )}
      </div>
    </div>
  );
}

export default ConfidenceJuryPanel;
