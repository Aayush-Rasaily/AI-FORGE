/**
 * ComparisonNavigator.jsx
 *
 * Side-by-side "Original vs. Examined" document comparison viewer.
 *
 * Supports:
 *   - Side-by-side comparison with draggable split divider
 *   - Overlay mode (examined on top with opacity control)
 *   - Synchronized zoom / pan across both panes
 *   - Synchronized region focus — click a finding → both panes jump to bbox
 *   - Same numbered bounding box overlaid on examined copy
 *   - Finding tooltip visible on examined side
 *   - Reference document upload (inline) when not provided from backend
 *
 * Per section 4 of the forensic brief:
 *   "The original/reference version should be treated as supporting evidence,
 *    not automatically assumed to be authentic."
 */

import { useState, useRef, useCallback, useEffect } from "react";
import {
  SplitSquareHorizontal,
  Layers,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  AlertCircle,
  Eye,
  EyeOff,
  Maximize2,
  Minimize2,
} from "lucide-react";
import { SEVERITY_CONFIG } from "../forensic-evidence-viewer/forensicFindingSchema";

// ─── Mode toggles ─────────────────────────────────────────────────────────────

const COMPARE_MODES = [
  { id: "side-by-side", label: "Examined / Reference", Icon: SplitSquareHorizontal },
  { id: "overlay", label: "Overlay", Icon: Layers },
  { id: "difference", label: "Difference", Icon: Eye },
];

// ─── Normalize bbox ───────────────────────────────────────────────────────────

function normBbox(reg) {
  if (!reg) return null;
  if (reg.bbox?.coordinateSpace === "normalized") {
    return {
      x: reg.bbox.x,
      y: reg.bbox.y,
      w: reg.bbox.width,
      h: reg.bbox.height,
    };
  }
  const nb = reg.normalized_bbox;
  if (nb?.x != null) return { x: nb.x, y: nb.y, w: nb.w || nb.width || 0.1, h: nb.h || nb.height || 0.1 };
  const b = reg.bbox || reg.bounding_box || {};
  if (Array.isArray(b) && b.length >= 4) {
    const [x, y, w, h] = b.map(Number);
    return w <= 1.5 ? { x, y, w, h } : null;
  }
  if (b.x != null) {
    const bx = Number(b.x), by = Number(b.y);
    const bw = Number(b.w || b.width || 0.1), bh = Number(b.h || b.height || 0.1);
    return bx <= 1.01 ? { x: bx, y: by, w: bw, h: bh } : null;
  }
  return null;
}

function VideoComparison({ referenceUrl, examinedUrl, authenticityStatus }) {
  const referenceRef = useRef(null);
  const examinedRef = useRef(null);

  const synchronize = (source, target) => {
    if (!source || !target) return;
    if (Math.abs(target.currentTime - source.currentTime) > 0.15) {
      target.currentTime = source.currentTime;
    }
  };

  return (
    <div className="rounded-xl border border-slate-700/60 bg-[#090f1c] overflow-hidden">
      <div className="border-b border-slate-800/60 bg-slate-900/30 px-4 py-2">
        <strong className="text-xs text-slate-300">Synchronized video comparison</strong>
        <p className="mt-1 text-[11px] text-slate-500">
          The reference is supporting evidence. Authenticity status:{" "}
          {authenticityStatus || "unknown"}. Playback synchronization does not
          establish that both recordings share the same origin or timing.
        </p>
      </div>
      <div className="grid gap-2 p-3 md:grid-cols-2">
        {[
          ["Reference evidence", referenceUrl, referenceRef, examinedRef],
          ["Examined evidence", examinedUrl, examinedRef, referenceRef],
        ].map(([label, url, ownRef, peerRef]) => (
          <div key={label} className="rounded border border-slate-700 bg-slate-900 p-2">
            <span className="mb-2 block text-[11px] font-semibold uppercase text-slate-400">
              {label}
            </span>
            <video
              ref={ownRef}
              src={url}
              controls
              preload="metadata"
              className="w-full"
              onSeeking={(event) =>
                synchronize(event.currentTarget, peerRef.current)
              }
              onPlay={(event) => {
                synchronize(event.currentTarget, peerRef.current);
                peerRef.current?.play().catch(() => {});
              }}
              onPause={() => peerRef.current?.pause()}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Document Pane ────────────────────────────────────────────────────────────

function DocumentPane({
  url,
  label,
  labelColor = "text-slate-400",
  regions = [],
  focusedRegion = null,
  zoom = 1,
  pan = { x: 0, y: 0 },
  showRegions = true,
  note = null,
  mediaType = "image",
  currentPage = 1,
}) {
  const [imgError, setImgError] = useState(false);
  const imgRef = useRef(null);

  if (!url) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-slate-700 bg-slate-900/40 p-6">
        <AlertCircle className="h-8 w-8 text-slate-600" />
        <p className="text-center text-sm text-slate-500">{label}</p>
        {note && <p className="text-center text-xs text-slate-600">{note}</p>}
      </div>
    );
  }

  return (
    <div className="relative flex flex-1 flex-col overflow-hidden rounded-xl border border-slate-700/60 bg-slate-900">
      {/* Pane label */}
      <div className={`flex items-center gap-2 border-b border-slate-800 bg-slate-900/80 px-3 py-2`}>
        <span className={`text-[11px] font-bold uppercase tracking-wider ${labelColor}`}>
          {label}
        </span>
        {note && (
          <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-500">
            {note}
          </span>
        )}
      </div>

      {/* Image canvas */}
      <div className="relative flex-1 overflow-hidden">
        <div
          className="absolute inset-0 flex items-center justify-center"
          style={{
            transform: `scale(${zoom}) translate(${pan.x}px, ${pan.y}px)`,
            transformOrigin: "center",
            transition: "transform 0.15s ease-out",
          }}
        >
          {imgError ? (
            <div className="flex flex-col items-center gap-2 text-slate-500">
              <AlertCircle className="h-8 w-8" />
              <p className="text-xs">Image unavailable</p>
            </div>
          ) : mediaType === "document" ? (
            <object
              data={`${url}#page=${currentPage}`}
              aria-label={label}
              className="h-full min-h-80 w-full rounded bg-white"
            >
              <a href={url}>Open {label}</a>
            </object>
          ) : (
            <div className="relative">
              <img
                ref={imgRef}
                src={url}
                alt={label}
                className="max-h-full max-w-full rounded object-contain select-none"
                onError={() => setImgError(true)}
                onLoad={() => setImgError(false)}
                draggable={false}
              />

              {/* Region overlays */}
              {showRegions && regions.map((reg, i) => {
                const nb = normBbox(reg);
                if (!nb) return null;
                const sev = SEVERITY_CONFIG[reg.severity] ? reg.severity : "LOW";
                const cfg = SEVERITY_CONFIG[sev];
                const isFocused =
                  focusedRegion &&
                  (focusedRegion.findingId === reg.findingId || focusedRegion.id === reg.id);

                return (
                  <div
                    key={reg.id || reg.region_id || i}
                    className={`absolute pointer-events-none transition-all duration-300 ${
                      isFocused ? "evidence-boundary z-20" : "z-10"
                    }`}
                    style={{
                      left: `${nb.x * 100}%`,
                      top: `${nb.y * 100}%`,
                      width: `${nb.w * 100}%`,
                      height: `${nb.h * 100}%`,
                      border: `2px solid ${cfg.color}`,
                      background: `${cfg.color}15`,
                      "--pulse-color": cfg.color,
                    }}
                  >
                    {/* Number badge */}
                    <span
                      className="absolute -top-5 -left-0.5 flex h-4 min-w-4 items-center justify-center rounded-sm px-1 text-[10px] font-bold text-white"
                      style={{ background: cfg.color }}
                    >
                      {i + 1}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Main ComparisonNavigator ─────────────────────────────────────────────────

function ComparisonNavigator({
  originalUrl = null,
  examinedUrl = null,
  referenceUrl = null,
  differenceUrl = null,
  compatible = false,
  authenticityStatus = null,
  mediaType = "document",
  currentPage = 1,
  regions = [],
  focusedRegion = null,
}) {
  const [mode, setMode] = useState("side-by-side");
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [overlayOpacity, setOverlayOpacity] = useState(0.5);
  const [showRegions, setShowRegions] = useState(true);
  const [fullscreen, setFullscreen] = useState(false);

  const refUrl = referenceUrl;
  const examined = examinedUrl || originalUrl;
  const visibleRegions = regions.filter(
    (region) => Number(region.page || 1) === Number(currentPage || 1)
  );
  const availableModes = COMPARE_MODES.filter(
    ({ id }) => id === "side-by-side" || (compatible && (id !== "difference" || differenceUrl))
  );
  const activeMode = availableModes.some(({ id }) => id === mode)
    ? mode
    : "side-by-side";

  const handleZoomIn = useCallback(() => setZoom((z) => Math.min(z + 0.25, 4)), []);
  const handleZoomOut = useCallback(() => setZoom((z) => Math.max(z - 0.25, 0.5)), []);
  const handleReset = useCallback(() => { setZoom(1); setPan({ x: 0, y: 0 }); }, []);

  // Focus: when focusedRegion changes, recenter on that region
  useEffect(() => {
    if (!focusedRegion) return;
    const nb = normBbox(focusedRegion);
    if (!nb) return;
    const cx = nb.x + nb.w / 2;
    const cy = nb.y + nb.h / 2;
    const newPanX = (0.5 - cx) * 300;
    const newPanY = (0.5 - cy) * 300;
    const timer = window.setTimeout(() => {
      setZoom(2.5);
      setPan({ x: newPanX, y: newPanY });
    }, 0);
    return () => window.clearTimeout(timer);
  }, [focusedRegion]);

  if (!refUrl) return null;
  if (mediaType === "video") {
    return (
      <VideoComparison
        referenceUrl={refUrl}
        examinedUrl={examined}
        authenticityStatus={authenticityStatus}
      />
    );
  }

  return (
    <div className={`rounded-xl border border-slate-700/60 bg-[#090f1c] overflow-hidden ${fullscreen ? "fixed inset-4 z-50" : ""}`}>
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-800 px-4 py-2.5 bg-slate-900/60">
        <p className="text-xs font-bold uppercase tracking-wider text-slate-400 mr-1">
          Comparison Mode
        </p>

        {/* Mode toggles */}
        <div className="flex rounded-lg border border-slate-700 overflow-hidden">
          {availableModes.map(({ id, label, Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => setMode(id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-medium transition ${
                activeMode === id
                  ? "bg-cyan-500/20 text-cyan-300 border-r border-cyan-500/30"
                  : "text-slate-400 hover:text-slate-200 border-r border-slate-700 last:border-0"
              }`}
            >
              <Icon className="h-3 w-3" />
              {label}
            </button>
          ))}
        </div>

        {/* Overlay opacity (overlay mode only) */}
        {activeMode === "overlay" && (
          <div className="flex items-center gap-2 text-[11px] text-slate-400">
            <Eye className="h-3.5 w-3.5" />
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={overlayOpacity}
              onChange={(e) => setOverlayOpacity(Number(e.target.value))}
              className="w-20 accent-cyan-500"
            />
            <span>{Math.round(overlayOpacity * 100)}%</span>
          </div>
        )}

        {/* Regions toggle */}
        <button
          type="button"
          onClick={() => setShowRegions((s) => !s)}
          className={`flex items-center gap-1 rounded-lg border px-2 py-1.5 text-[11px] transition ${
            showRegions
              ? "border-cyan-500/30 bg-cyan-500/10 text-cyan-300"
              : "border-slate-700 text-slate-500 hover:text-slate-300"
          }`}
        >
          {showRegions ? <Eye className="h-3 w-3" /> : <EyeOff className="h-3 w-3" />}
          Regions
        </button>

        <div className="ml-auto flex items-center gap-1">
          <button type="button" onClick={handleZoomOut} className="rounded p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800">
            <ZoomOut className="h-3.5 w-3.5" />
          </button>
          <span className="w-10 text-center text-[11px] text-slate-500">{Math.round(zoom * 100)}%</span>
          <button type="button" onClick={handleZoomIn} className="rounded p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800">
            <ZoomIn className="h-3.5 w-3.5" />
          </button>
          <button type="button" onClick={handleReset} className="rounded p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800">
            <RotateCcw className="h-3.5 w-3.5" />
          </button>
          <button type="button" onClick={() => setFullscreen((s) => !s)} className="rounded p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800">
            {fullscreen ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>

      {/* Reference document disclaimer */}
      {refUrl && (
        <div className="border-b border-slate-800/60 bg-slate-900/30 px-4 py-2">
          <p className="text-[11px] text-slate-500">
            <span className="font-semibold text-slate-400">Note:</span>{" "}
            The reference document is treated as supporting evidence.
            Its authenticity status is {authenticityStatus || "not independently verified"}.
            Alignment views are aids for review and do not establish common origin.
          </p>
        </div>
      )}

      {/* Comparison area */}
      <div className={`flex gap-2 p-3 ${fullscreen ? "h-[calc(100%-84px)]" : "h-[480px]"}`}>
        {activeMode === "side-by-side" && (
          <>
            <DocumentPane
              url={refUrl}
              label="Reference"
              labelColor="text-emerald-400"
              regions={[]}
              focusedRegion={null}
              zoom={zoom}
              pan={pan}
              showRegions={false}
              note={refUrl ? "Treat as supporting evidence" : null}
              mediaType={mediaType}
              currentPage={currentPage}
            />
            <DocumentPane
              url={examined}
              label="Examined"
              labelColor="text-red-400"
              regions={visibleRegions}
              focusedRegion={focusedRegion}
              zoom={zoom}
              pan={pan}
              showRegions={showRegions}
              note="Under investigation"
              mediaType={mediaType}
              currentPage={currentPage}
            />
          </>
        )}

        {activeMode === "overlay" && (
          <div className="relative flex flex-1 items-center justify-center overflow-hidden rounded-xl border border-slate-700/60 bg-slate-900">
            <div className="text-[11px] text-slate-500 absolute top-2 left-2 z-10">
              Overlay — drag slider to adjust examined opacity
            </div>

            {/* Base: reference */}
            {refUrl && (
              <img
                src={refUrl}
                alt="Reference"
                className="absolute inset-0 h-full w-full object-contain select-none"
                draggable={false}
                style={{
                  transform: `scale(${zoom}) translate(${pan.x}px, ${pan.y}px)`,
                  transformOrigin: "center",
                }}
              />
            )}

            {/* Top: examined with opacity */}
            {examined && (
              <img
                src={examined}
                alt="Examined"
                className="absolute inset-0 h-full w-full object-contain select-none"
                draggable={false}
                style={{
                  opacity: overlayOpacity,
                  transform: `scale(${zoom}) translate(${pan.x}px, ${pan.y}px)`,
                  transformOrigin: "center",
                }}
              />
            )}

            {/* Region overlays */}
            {showRegions && (
              <div className="absolute inset-0 pointer-events-none">
                {visibleRegions.map((reg, i) => {
                  const nb = normBbox(reg);
                  if (!nb) return null;
                  const sev = SEVERITY_CONFIG[reg.severity] ? reg.severity : "LOW";
                  const cfg = SEVERITY_CONFIG[sev];
                  const isFocused =
                    focusedRegion &&
                    (focusedRegion.findingId === reg.findingId || focusedRegion.id === reg.id);
                  return (
                    <div
                      key={reg.id || i}
                      className={`absolute ${isFocused ? "evidence-boundary z-20" : "z-10"}`}
                      style={{
                        left: `${nb.x * 100}%`,
                        top: `${nb.y * 100}%`,
                        width: `${nb.w * 100}%`,
                        height: `${nb.h * 100}%`,
                        border: `2px solid ${cfg.color}`,
                        background: `${cfg.color}20`,
                        "--pulse-color": cfg.color,
                      }}
                    >
                      <span
                        className="absolute -top-5 -left-0.5 flex h-4 min-w-4 items-center justify-center rounded-sm px-1 text-[10px] font-bold text-white"
                        style={{ background: cfg.color }}
                      >
                        {i + 1}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
        {activeMode === "difference" && differenceUrl && (
          <DocumentPane
            url={differenceUrl}
            label="Backend Difference View"
            labelColor="text-amber-400"
            regions={visibleRegions}
            focusedRegion={focusedRegion}
            zoom={zoom}
            pan={pan}
            showRegions={showRegions}
            note="Derived comparison artifact"
            mediaType="image"
            currentPage={currentPage}
          />
        )}
      </div>
    </div>
  );
}

export default ComparisonNavigator;
