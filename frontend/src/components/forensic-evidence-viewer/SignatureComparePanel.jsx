import { PenTool } from "lucide-react";
import { getArtifactUrl } from "../../services/api";

/**
 * Signature investigation pane — reference vs query with similarity explanation.
 */
function SignatureComparePanel({ signatureResult }) {
  if (!signatureResult) return null;

  const similarity =
    signatureResult.similarity ??
    signatureResult.score ??
    signatureResult.match_score ??
    null;
  const simPct =
    similarity == null
      ? null
      : Number(similarity) > 1
        ? Number(similarity)
        : Number(similarity) * 100;

  const matched = signatureResult.is_match ?? signatureResult.match ?? simPct >= 70;
  const reason =
    signatureResult.explanation ||
    signatureResult.reason ||
    (matched
      ? "Stroke geometry and keypoints are consistent with the reference signature."
      : "Stroke paths, pressure approximation, and keypoint alignment diverge from the reference.");

  const refUrl = signatureResult.reference_url
    ? getArtifactUrl(signatureResult.reference_url)
    : null;
  const queryUrl = signatureResult.query_url
    ? getArtifactUrl(signatureResult.query_url)
    : null;
  const heatUrl =
    signatureResult.heatmap_url || signatureResult.similarity_heatmap
      ? getArtifactUrl(
          signatureResult.heatmap_url || signatureResult.similarity_heatmap
        )
      : null;

  return (
    <div className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-5">
      <div className="mb-4 flex items-center gap-2">
        <PenTool className="h-4 w-4 text-fuchsia-400" />
        <h3 className="text-sm font-semibold text-white">Signature Viewer</h3>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {[
          { label: "Reference signature", src: refUrl },
          { label: "Query signature", src: queryUrl },
          { label: "Similarity heatmap", src: heatUrl },
        ].map(({ label, src }) => (
          <div key={label} className="overflow-hidden rounded-xl border border-[#1F2937] bg-[#0B1120]">
            <p className="border-b border-[#1F2937] px-3 py-1.5 text-[10px] uppercase tracking-wider text-slate-500">
              {label}
            </p>
            <div className="flex min-h-[120px] items-center justify-center p-2">
              {src ? (
                <img src={src} alt={label} className="max-h-[160px] object-contain" />
              ) : (
                <p className="text-xs text-slate-600">Not available</p>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl bg-[#0B1120] p-3">
          <p className="text-[10px] uppercase text-slate-500">Similarity</p>
          <p
            className={`text-xl font-bold ${
              matched ? "text-emerald-400" : "text-red-400"
            }`}
          >
            {simPct != null ? `${simPct.toFixed(1)}%` : "—"}
          </p>
        </div>
        <div className="rounded-xl bg-[#0B1120] p-3">
          <p className="text-[10px] uppercase text-slate-500">Verdict</p>
          <p className="text-sm font-semibold text-white">
            {matched ? "Likely match" : "Signature failed verification"}
          </p>
        </div>
        <div className="rounded-xl bg-[#0B1120] p-3 sm:col-span-1">
          <p className="text-[10px] uppercase text-slate-500">Pressure (approx.)</p>
          <p className="text-sm text-slate-300">
            {signatureResult.pressure_estimate ||
              signatureResult.stroke_pressure ||
              "Estimated from stroke width variance"}
          </p>
        </div>
      </div>

      <p className="mt-3 text-sm leading-relaxed text-slate-300">{reason}</p>
      {signatureResult.keypoints_matched != null && (
        <p className="mt-1 text-xs text-slate-500">
          Matching keypoints: {signatureResult.keypoints_matched}
          {signatureResult.keypoints_total != null
            ? ` / ${signatureResult.keypoints_total}`
            : ""}
        </p>
      )}
    </div>
  );
}

export default SignatureComparePanel;
