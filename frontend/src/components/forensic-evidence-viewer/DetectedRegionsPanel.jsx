import { MapPin } from "lucide-react";
import PlainLanguageFindingCard from "./PlainLanguageFindingCard";

/**
 * DetectedRegionsPanel — Plain-language forensic findings list.
 *
 * Each card communicates WHAT/WHERE/WHY/HOW in plain English
 * so a non-technical investigator immediately understands the findings.
 */
function DetectedRegionsPanel({ regions = [], selectedId, onSelect }) {
  return (
    <div className="rounded-2xl border border-[#1F2937] bg-[#111827]/90 p-5 backdrop-blur-xl shadow-xl">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MapPin className="h-4 w-4 text-cyan-400" />
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">
            What Was Found
          </h3>
        </div>
        <span className="rounded-md border border-[#1F2937] bg-[#0B1120] px-2.5 py-1 text-[11px] font-mono text-cyan-400">
          {regions.length} {regions.length === 1 ? "Finding" : "Findings"}
        </span>
      </div>

      {/* Color legend */}
      <div className="mb-4 flex flex-wrap items-center gap-x-4 gap-y-1.5 rounded-xl border border-[#1F2937] bg-[#0B1120]/60 px-3 py-2">
        <p className="text-[9px] font-bold uppercase tracking-widest text-slate-500 shrink-0">Legend:</p>
        {[
          { hex: "#ef4444", label: "Confirmed" },
          { hex: "#fb923c", label: "Suspicious" },
          { hex: "#facc15", label: "Needs Verification" },
          { hex: "#34d399", label: "Appears Genuine" },
        ].map(({ hex, label }) => (
          <div key={label} className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: hex }} />
            <span className="text-[10px] text-slate-400">{label}</span>
          </div>
        ))}
      </div>

      {regions.length === 0 ? (
        <p className="text-sm text-slate-500 py-4 text-center">
          No manipulation findings detected.
        </p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {regions.slice(0, 30).map((reg, idx) => {
            const active = reg.id === selectedId || reg.region_id === selectedId;
            return (
              <PlainLanguageFindingCard
                key={reg.id || `reg-${idx}`}
                region={reg}
                index={idx}
                active={active}
                onSelect={onSelect}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

export default DetectedRegionsPanel;

