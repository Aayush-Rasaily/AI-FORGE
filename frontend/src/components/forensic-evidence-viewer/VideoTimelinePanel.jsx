import { Play, Clapperboard, Film, ShieldAlert, Cpu } from "lucide-react";

function VideoTimelinePanel({ intervals = [], activeTs, onSelect }) {
  if (!intervals.length) return null;

  const maxTs = Math.max(
    1,
    ...intervals.map((i) => Number(i.timestamp_sec || i.time_seconds || i.timestamp) || 0),
    ...intervals.map((i) => (Number(i.timestamp_sec || i.time_seconds || i.timestamp) || 0) + 1)
  );

  return (
    <div className="rounded-2xl border border-[#1F2937] bg-[#111827]/90 p-5 backdrop-blur-xl shadow-xl">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Clapperboard className="h-4 w-4 text-violet-400" />
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">Video Anomaly Keyframe Audit</h3>
        </div>
        <span className="rounded-md border border-[#1F2937] bg-[#0B1120] px-2.5 py-1 text-[11px] font-mono text-violet-400">
          {intervals.length} Anomalous Keyframes
        </span>
      </div>

      {/* Timeline Scrub Track */}
      <div className="relative mb-5 h-10 overflow-hidden rounded-xl bg-[#0B1120] border border-slate-800">
        <div className="absolute inset-x-3 top-1/2 h-1 -translate-y-1/2 rounded-full bg-slate-700" />
        {intervals.map((iv, idx) => {
          const ts = Number(iv.time_seconds || iv.timestamp_sec || iv.timestamp) || 0;
          const left = Math.min(96, Math.max(2, (ts / maxTs) * 100));
          const score = Number(iv.confidence || iv.deepfake_score || iv.score) || 0.5;
          const color = score >= 0.7 ? "bg-red-500" : score >= 0.4 ? "bg-orange-400" : "bg-emerald-400";
          const active = activeTs === iv.timestamp || activeTs === ts;

          return (
            <button
              key={`${ts}-${idx}`}
              type="button"
              title={`${iv.timestamp_str || iv.timestamp} — ${iv.finding || iv.reason || "Keyframe anomaly"}`}
              onClick={() => onSelect?.(iv)}
              className={`absolute top-1/2 h-5 w-5 -translate-x-1/2 -translate-y-1/2 rounded-sm ${color} ${
                active ? "ring-2 ring-white scale-125 z-10" : ""
              } transition hover:scale-125`}
              style={{ left: `${left}%` }}
            />
          );
        })}
        <span className="absolute bottom-1 left-3 text-[9px] font-mono text-slate-500">00:00.00</span>
        <span className="absolute bottom-1 right-3 text-[9px] font-mono text-slate-500">
          {maxTs.toFixed(2)}s
        </span>
      </div>

      {/* Keyframe Finding Cards Grid */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {intervals.slice(0, 15).map((iv, idx) => {
          const frameNum = iv.frame_number || (idx + 1) * 15;
          const tsStr = iv.timestamp_str || iv.timestamp || `${Number(iv.time_seconds || 0).toFixed(2)}s`;
          const findingName = iv.finding || iv.edit_type || "Face replacement";
          const evidenceList = iv.evidence || iv.detectors || ["Xception", "Optical Flow", "Frequency Domain"];
          const evidenceStr = Array.isArray(evidenceList) ? evidenceList.join(", ") : String(evidenceList);
          const active = activeTs === iv.timestamp || activeTs === iv.time_seconds;

          return (
            <button
              key={`kf-${idx}`}
              type="button"
              onClick={() => onSelect?.(iv)}
              className={`group flex flex-col justify-between rounded-xl border p-3.5 text-left transition-all ${
                active
                  ? "border-violet-500/60 bg-violet-500/15 ring-1 ring-violet-500/50 shadow-lg shadow-violet-500/10"
                  : "border-[#1F2937] bg-[#0B1120]/80 hover:border-slate-600 hover:bg-[#0B1120]"
              }`}
            >
              <div>
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className="font-mono font-bold text-white group-hover:text-violet-300">
                    Frame {frameNum}
                  </span>
                  <span className="rounded bg-slate-800 px-2 py-0.5 font-mono text-[10px] font-semibold text-violet-300">
                    {tsStr}
                  </span>
                </div>

                <div className="flex items-center gap-1.5 mb-1.5">
                  <Film className="h-3.5 w-3.5 text-rose-400 shrink-0" />
                  <span className="text-xs font-bold text-rose-300">{findingName}</span>
                </div>

                <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                  {iv.reason || iv.summary || "Deep neural frame signal anomaly localized."}
                </p>
              </div>

              <div className="mt-3 pt-2.5 border-t border-[#1F2937]/60 space-y-1 text-[10px]">
                <div className="flex items-center justify-between text-slate-400">
                  <span className="flex items-center gap-1">
                    <Cpu className="h-3 w-3 text-slate-500" />
                    Evidence:
                  </span>
                  <span className="font-semibold text-slate-200 truncate max-w-[160px]">{evidenceStr}</span>
                </div>
                <div className="text-slate-500 truncate">
                  <span className="font-semibold text-slate-400">Rec: </span>
                  {iv.recommendation || "Verify original footage"}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default VideoTimelinePanel;
