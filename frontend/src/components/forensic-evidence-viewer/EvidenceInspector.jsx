import { motion, AnimatePresence } from "framer-motion";
import {
  Crosshair,
  Check,
  X,
  ZoomIn,
  Crop,
  Columns2,
  X as CloseIcon,
  ChevronDown,
  ChevronUp,
  MapPin,
  AlertTriangle,
} from "lucide-react";
import { useState } from "react";
import {
  getLocationDescription,
  translateDetectorName,
  generatePlainFinding,
} from "./forensicTranslator";

function VoteRow({ label, ok }) {
  return (
    <div className="flex items-center justify-between border-b border-[#1F2937]/80 py-1.5 text-xs last:border-0">
      <span className="text-slate-300">{label}</span>
      {ok ? (
        <span className="inline-flex items-center gap-1 text-emerald-400">
          <Check className="h-3.5 w-3.5" /> Yes
        </span>
      ) : (
        <span className="inline-flex items-center gap-1 text-slate-500">
          <X className="h-3.5 w-3.5" /> No
        </span>
      )}
    </div>
  );
}

function EvidenceInspector({ region, open, onClose, originalUrl, evidenceId }) {
  const [showTech, setShowTech] = useState(false);

  if (!open) {
    return (
      <div className="rounded-2xl border border-dashed border-[#1F2937] bg-[#111827]/40 p-5 text-center text-xs text-slate-500">
        Click a suspicious region to open the Evidence Inspector.
      </div>
    );
  }

  if (!region) {
    return (
      <div className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-5 text-sm text-slate-400">
        No region selected.
      </div>
    );
  }

  // Build a coords object that works with both canonical {width,height} and legacy {w,h} bbox
  const _bbox = region.bbox || region.bounding_box || {};
  const coords = region.coordinates || {
    x: _bbox?.x,
    y: _bbox?.y,
    // Accept both canonical 'width' and legacy shorthand 'w'
    width: _bbox?.width ?? _bbox?.w,
    // Accept both canonical 'height' and legacy shorthand 'h'
    height: _bbox?.height ?? _bbox?.h,
  };
  const votes = region.detector_votes || {};
  const rawScore = Number(region.confidence ?? region.score ?? 0) || 0;
  const conf = rawScore > 1 ? rawScore : rawScore * 100;
  const confColor =
    conf >= 85 ? "text-red-400" : conf >= 65 ? "text-orange-400" : "text-emerald-400";

  // Plain-language finding
  const finding = generatePlainFinding(region);
  const locationText = getLocationDescription(
    region.normalized_bbox || _bbox,
    region.page
  );

  const saveCrop = () => {
    // Open original in new tab focused — crop export relies on viewer coordinates
    if (originalUrl) window.open(originalUrl, "_blank", "noopener,noreferrer");
  };

  return (
    <AnimatePresence>
      <motion.aside
        initial={{ opacity: 0, x: 12 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: 12 }}
        className="overflow-hidden rounded-2xl border border-cyan-500/25 bg-[#111827]/95 shadow-xl shadow-cyan-950/20"
      >
        <div className="flex items-center justify-between border-b border-[#1F2937] px-4 py-3">
          <div className="flex items-center gap-2">
            <Crosshair className="h-4 w-4 text-cyan-400" />
            <h3 className="text-sm font-semibold text-white">
              Evidence Inspector
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-slate-500 hover:bg-slate-800 hover:text-white"
          >
            <CloseIcon className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-4 p-4">
          {/* PLAIN ENGLISH — Primary content (shown first) */}
          {(finding?.plainEnglish || region.plain_english_explanation || region.investigation) && (
            <div className={`rounded-xl border-l-4 px-3.5 py-3 ${finding?.severity.borderClass || "border-amber-400"} bg-[#0B1120]/80`}>
              <p className={`text-[10px] font-bold uppercase tracking-wider mb-1 ${finding?.severity.textClass || "text-amber-300"}`}>
                {finding?.severity.short || "FINDING"}
              </p>
              <p className="text-sm font-semibold text-white leading-snug">
                {finding?.whatHappened || region.manipulation || region.type || "Manipulation detected"}
              </p>
              <p className="mt-1.5 text-[11px] text-slate-300 leading-relaxed">
                {finding?.plainEnglish || region.plain_english_explanation ||
                  region.investigation?.split("\n")[0] ||
                  "Select a region to view the investigator summary."}
              </p>
            </div>
          )}

          {/* Location — plain + coordinates */}
          <div>
            <p className="text-[10px] uppercase tracking-wider text-slate-500 flex items-center gap-1 mb-1.5">
              <MapPin className="h-3 w-3" /> Location
            </p>
            {locationText && (
              <p className="text-sm font-semibold text-white mb-2">{locationText}</p>
            )}
            <div className="grid grid-cols-2 gap-2 rounded-xl bg-[#0B1120] p-3 text-xs">
              {[
                ["x", coords.x],
                ["y", coords.y],
                ["width", coords.width],
                ["height", coords.height],
              ].map(([k, v]) => (
                <div key={k}>
                  <span className="text-slate-500">{k}</span>
                  <p className="font-mono text-slate-200">{v ?? "—"}</p>
                </div>
              ))}
            </div>
          </div>

          {(region.mask_pixel_count != null || region.mask_coverage != null) && (
            <div className="grid grid-cols-2 gap-2 rounded-xl border border-[#1F2937] bg-[#0B1120] p-3 text-xs">
              <div>
                <span className="text-slate-500">mask pixels</span>
                <p className="font-mono text-slate-200">
                  {region.mask_pixel_count?.toLocaleString?.() ?? region.mask_pixel_count ?? "—"}
                </p>
              </div>
              <div>
                <span className="text-slate-500">coverage</span>
                <p className="font-mono text-slate-200">
                  {region.mask_coverage != null
                    ? `${(Number(region.mask_coverage) * 100).toFixed(3)}%`
                    : "—"}
                </p>
              </div>
            </div>
          )}

          {region.mask && region.mask_format === "png_base64_crop" && (
            <div>
              <p className="mb-1 text-[10px] uppercase tracking-wider text-slate-500">Region Mask</p>
              <img
                src={`data:image/png;base64,${region.mask}`}
                alt="Region mask"
                className="max-h-28 rounded-lg border border-[#1F2937] bg-black/40 object-contain"
              />
            </div>
          )}

          {region.explainability?.detector_contributions?.length > 0 && (
            <div>
              <p className="mb-1 text-[10px] uppercase tracking-wider text-slate-500">
                Detector Contributions
              </p>
              <div className="rounded-xl border border-[#1F2937] px-3 py-1">
                {region.explainability.detector_contributions.map((row) => (
                  <div key={row.detector} className="flex items-center justify-between border-b border-[#1F2937]/80 py-1.5 text-xs last:border-0">
                    <span className="text-slate-300">{row.detector}</span>
                    <span className={row.active ? "text-emerald-400" : "text-slate-500"}>
                      {(row.contribution * 100).toFixed(1)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {region.explainability?.verdict && (
            <div className="rounded-xl border border-[#1F2937] bg-[#0B1120] p-3">
              <p className="text-[10px] uppercase tracking-wider text-slate-500">Region Verdict</p>
              <p className="mt-1 text-sm font-semibold text-white">{region.explainability.verdict}</p>
            </div>
          )}

          {/* Confidence meter */}
          <div className="rounded-xl border border-[#1F2937] bg-[#0B1120] p-3">
            <p className="text-[10px] uppercase tracking-wider text-slate-500">
              AI Certainty
            </p>
            <p className={`mt-1 text-2xl font-bold tabular-nums ${confColor}`}>
              {conf.toFixed(1)}%
            </p>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-800">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  conf >= 85 ? "bg-red-500" : conf >= 65 ? "bg-orange-400" : "bg-emerald-400"
                }`}
                style={{ width: `${Math.min(100, conf)}%` }}
              />
            </div>
          </div>

          {/* What AI systems detected — plain label */}
          <div>
            <p className="mb-1 text-[10px] uppercase tracking-wider text-slate-500">
              What AI Systems Detected
            </p>
            <div className="rounded-xl border border-[#1F2937] px-3 py-1">
              {Object.keys(votes).length === 0 && (
                <p className="py-2 text-xs text-slate-500">No detector votes recorded.</p>
              )}
              {Object.entries(votes).map(([label, ok]) => (
                <div key={label} className="flex items-center justify-between border-b border-[#1F2937]/80 py-1.5 text-xs last:border-0">
                  <span className="text-slate-300">{translateDetectorName(label)}</span>
                  {ok ? (
                    <span className="inline-flex items-center gap-1 text-emerald-400"><Check className="h-3.5 w-3.5" /> Detected</span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-slate-500"><X className="h-3.5 w-3.5" /> Not detected</span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Technical details — collapsible */}
          <div>
            <button
              type="button"
              id="inspector-toggle-tech"
              onClick={() => setShowTech(s => !s)}
              className="flex w-full items-center justify-between text-[10px] uppercase tracking-wider text-slate-500 hover:text-slate-300 mb-1"
            >
              <span>AI Evidence Details (Technical)</span>
              {showTech ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </button>
            {showTech && (
              <p className="text-xs leading-relaxed text-slate-300">
                {region.technical_explanation || region.reason || "No technical explanation available."}
              </p>
            )}
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => originalUrl && window.open(originalUrl, "_blank")}
              className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-[#1F2937] px-3 py-2 text-xs text-slate-300 hover:border-cyan-500/40"
            >
              <ZoomIn className="h-3.5 w-3.5" />
              Zoom
            </button>
            <button
              type="button"
              onClick={saveCrop}
              className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-[#1F2937] px-3 py-2 text-xs text-slate-300 hover:border-cyan-500/40"
            >
              <Crop className="h-3.5 w-3.5" />
              Save Crop
            </button>
            <button
              type="button"
              onClick={() => originalUrl && window.open(originalUrl, "_blank")}
              className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-[#1F2937] px-3 py-2 text-xs text-slate-300 hover:border-cyan-500/40"
            >
              <Columns2 className="h-3.5 w-3.5" />
              Compare
            </button>
          </div>
          {evidenceId && (
            <p className="text-[10px] text-slate-600">Evidence ID: {evidenceId}</p>
          )}
        </div>
      </motion.aside>
    </AnimatePresence>
  );
}

export default EvidenceInspector;
