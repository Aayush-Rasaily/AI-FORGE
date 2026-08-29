import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { humanizeRegionLabel, translateDetectorName, getSeverityInfo } from "./forensicTranslator";
import { motion, AnimatePresence } from "framer-motion";
import {
  Eye,
  Flame,
  Scan,
  BoxSelect,
  Layers,
  Copy,
  Shield,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Minimize2,
  RotateCcw,
  Loader2,
  SplitSquareHorizontal,
  Search,
  Filter,
  AlertTriangle,
  Cpu,
  MapPin,
  CheckCircle2,
} from "lucide-react";

const DETECTOR_TYPES = [
  { id: "ELA", label: "Editing Artifacts", color: "bg-red-500/20 text-red-300 border-red-500/40" },
  { id: "Noise", label: "Inconsistencies", color: "bg-amber-500/20 text-amber-300 border-amber-500/40" },
  { id: "Copy Move", label: "Copied Content", color: "bg-cyan-500/20 text-cyan-300 border-cyan-500/40" },
  { id: "OCR", label: "Text Analysis", color: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40" },
  { id: "Metadata", label: "Document History", color: "bg-blue-500/20 text-blue-300 border-blue-500/40" },
  { id: "GAN", label: "AI Generation", color: "bg-purple-500/20 text-purple-300 border-purple-500/40" },
  { id: "Signature", label: "Signature Check", color: "bg-pink-500/20 text-pink-300 border-pink-500/40" },
  { id: "Logo", label: "Logo Analysis", color: "bg-orange-500/20 text-orange-300 border-orange-500/40" },
  { id: "Forgery", label: "Forgery Detection", color: "bg-rose-500/20 text-rose-300 border-rose-500/40" },
];

const MODES = [
  { id: "original", label: "Original Evidence", icon: Eye },
  { id: "heatmap", label: "Manipulation Heatmap", icon: Flame },
  { id: "ela", label: "Editing Detection Map", icon: Scan },
  { id: "noise", label: "Inconsistency Map", icon: Shield },
  { id: "copy_move", label: "Copied Content", icon: Copy },
  { id: "forgery_mask", label: "Manipulation Areas", icon: Scan },
  { id: "segmentation_overlay", label: "Evidence Overlay", icon: Layers },
  { id: "bounding_boxes", label: "Detected Regions", icon: BoxSelect },
  { id: "compare", label: "Before / After", icon: SplitSquareHorizontal },
];

const getRiskTone = (score) => {
  const s = Number(score) || 0;
  const pct = s <= 1 ? s * 100 : s;
  if (pct >= 75) return { border: "border-red-500", bg: "bg-red-500/25", text: "text-red-400", hex: "#ef4444", label: "Critical" };
  if (pct >= 55) return { border: "border-orange-400", bg: "bg-orange-400/20", text: "text-orange-300", hex: "#fb923c", label: "High Risk" };
  if (pct >= 35) return { border: "border-yellow-400", bg: "bg-yellow-400/20", text: "text-yellow-300", hex: "#facc15", label: "Medium Risk" };
  return { border: "border-emerald-400", bg: "bg-emerald-400/20", text: "text-emerald-300", hex: "#34d399", label: "Low Risk" };
};

function InteractiveForensicPane({
  originalUrl,
  overlayUrl,
  viewMode,
  onViewModeChange,
  opacity = 0.6,
  regions = [],
  selectedRegion,
  onSelectRegion,
  loading,
  focusRegion = null,
  hasRegions = false,
}) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [fullscreen, setFullscreen] = useState(false);
  const [compareMode, setCompareMode] = useState(false);
  const [splitPos, setSplitPos] = useState(50);
  const [natural, setNatural] = useState({ w: 1, h: 1 });
  const [hoveredRegion, setHoveredRegion] = useState(null);
  const [imgError, setImgError] = useState(false);

  // Magnifier Loupe lens state
  const [magnifierActive, setMagnifierActive] = useState(false);
  const [magnifierPos, setMagnifierPos] = useState({ x: 0, y: 0, relX: 0, relY: 0 });

  // Active Individual Detector Toggles
  const [activeDetectors, setActiveDetectors] = useState(() =>
    DETECTOR_TYPES.reduce((acc, d) => ({ ...acc, [d.id]: true }), {})
  );

  const dragging = useRef(false);
  const lastPos = useRef({ x: 0, y: 0 });
  const viewportRef = useRef(null);

  const toggleDetector = (detId) => {
    setActiveDetectors((prev) => ({ ...prev, [detId]: !prev[detId] }));
  };

  const reset = useCallback(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setSplitPos(50);
    setMagnifierActive(false);
  }, []);

  // Filter regions based on active detector toggles
  const filteredRegions = useMemo(() => {
    if (!regions) return [];
    return regions.filter((reg) => {
      const dets = reg.detectors || (reg.detector ? [reg.detector] : ["Ensemble"]);
      return dets.some((d) => {
        const dUpper = d.toUpperCase();
        return Object.entries(activeDetectors).some(([key, active]) => {
          if (!active) return false;
          const kUpper = key.toUpperCase();
          return dUpper.includes(kUpper) || kUpper.includes(dUpper);
        });
      });
    });
  }, [regions, activeDetectors]);

  // Sync mode tab with comparison slider
  useEffect(() => {
    if (viewMode === "compare") {
      setCompareMode(true);
    }
  }, [viewMode]);

  // Click / Copilot driven auto-zoom to region bbox
  useEffect(() => {
    if (!focusRegion) return;
    const nb = focusRegion.normalized_bbox;
    const bbox = focusRegion.bbox || focusRegion.bounding_box || {};
    let cx = 0.5;
    let cy = 0.5;
    if (nb) {
      cx = (nb.x || 0) + (nb.w || 0) / 2;
      cy = (nb.y || 0) + (nb.h || 0) / 2;
    } else if (Array.isArray(bbox) && bbox.length >= 4 && natural.w > 1) {
      cx = (bbox[0] + bbox[2] / 2) / natural.w;
      cy = (bbox[1] + bbox[3] / 2) / natural.h;
    } else if (bbox.x != null && natural.w > 1) {
      const w = bbox.w || bbox.width || 1;
      const h = bbox.h || bbox.height || 1;
      cx = (bbox.x + w / 2) / natural.w;
      cy = (bbox.y + h / 2) / natural.h;
    }
    const targetZoom = 2.4;
    setZoom(targetZoom);
    const vp = viewportRef.current;
    const vw = vp?.clientWidth || 400;
    const vh = vp?.clientHeight || 360;
    setPan({
      x: (0.5 - cx) * vw * targetZoom,
      y: (0.5 - cy) * vh * targetZoom,
    });
    onSelectRegion?.(focusRegion);
  }, [focusRegion, natural.w, natural.h, onSelectRegion]);

  useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;
    const onWheel = (e) => {
      if (e.cancelable) e.preventDefault();
      setZoom((z) => Math.min(6, Math.max(0.4, z + (e.deltaY > 0 ? -0.15 : 0.15))));
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  const activeOverlayUrl = overlayUrl || originalUrl;
  const showOverlay = viewMode !== "original" && Boolean(activeOverlayUrl) && !imgError;

  const shell = fullscreen
    ? "fixed inset-0 z-[60] flex flex-col bg-[#020617]/98 p-4"
    : "flex flex-col overflow-hidden rounded-2xl border border-[#1F2937] bg-[#0B1120] shadow-2xl";

  return (
    <div className={shell}>
      {/* Top Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#1F2937] px-3.5 py-2.5 bg-[#0F172A]/90">
        <p className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
          <Layers className="h-4 w-4 text-cyan-400" />
          Evidence Examination Viewer
        </p>

        <div className="flex items-center gap-1.5">
          {/* Magnifier Lens Toggle */}
          <button
            type="button"
            onClick={() => setMagnifierActive((m) => !m)}
            className={`flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium transition ${
              magnifierActive
                ? "bg-cyan-500/20 text-cyan-300 ring-1 ring-cyan-500/50"
                : "text-slate-400 hover:bg-slate-800 hover:text-white"
            }`}
            title="Magnifier Loupe Lens"
          >
            <Search className="h-3.5 w-3.5" />
            <span>Magnifier</span>
          </button>

          <button type="button" onClick={() => setZoom((z) => Math.min(6, z + 0.3))} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white" title="Zoom In">
            <ZoomIn className="h-4 w-4" />
          </button>
          <button type="button" onClick={() => setZoom((z) => Math.max(0.4, z - 0.3))} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white" title="Zoom Out">
            <ZoomOut className="h-4 w-4" />
          </button>

          <button
            type="button"
            onClick={() => {
              setCompareMode((c) => !c);
              if (!compareMode) onViewModeChange("compare");
            }}
            className={`rounded-lg p-1.5 transition ${compareMode ? "bg-cyan-500/20 text-cyan-300 ring-1 ring-cyan-500/40" : "text-slate-400 hover:bg-slate-800 hover:text-white"}`}
            title="Comparison Split Slider"
          >
            <SplitSquareHorizontal className="h-4 w-4" />
          </button>

          <button type="button" onClick={reset} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white" title="Reset View">
            <RotateCcw className="h-4 w-4" />
          </button>

          <button type="button" onClick={() => setFullscreen((f) => !f)} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white" title="Fullscreen Workstation">
            {fullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* Mode Tabs */}
      <div className="flex gap-1 overflow-x-auto border-b border-[#1F2937] px-2 py-2 scrollbar-thin bg-[#0B1120]">
        {MODES.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => {
              setImgError(false);
              onViewModeChange(id);
              if (id === "compare") setCompareMode(true);
            }}
            className={`inline-flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[11px] font-medium transition ${
              viewMode === id
                ? "bg-cyan-500/20 text-cyan-300 ring-1 ring-cyan-500/50 shadow-md"
                : "text-slate-400 hover:bg-slate-800/80 hover:text-slate-200"
            }`}
          >
            <Icon className="h-3 w-3" />
            {label}
          </button>
        ))}
      </div>

      {/* Individual Detector Toggle Bar */}
      <div className="flex flex-wrap items-center gap-1.5 border-b border-[#1F2937] bg-[#0B1120]/95 px-3 py-2">
        <span className="flex items-center gap-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider mr-1">
          <Filter className="h-3 w-3 text-cyan-400" />
          Filter by Detection Type:
        </span>
        {DETECTOR_TYPES.map(({ id, label, color }) => {
          const active = activeDetectors[id];
          return (
            <button
              key={id}
              type="button"
              onClick={() => toggleDetector(id)}
              className={`rounded-md px-2 py-0.5 text-[10px] font-semibold transition border ${
                active
                  ? `${color} shadow-sm ring-1 ring-white/10`
                  : "border-slate-800 bg-slate-900/60 text-slate-500 line-through opacity-50"
              }`}
            >
              {label}
            </button>
          );
        })}
      </div>

      {/* Comparison Split Slider Controls */}
      {compareMode && (
        <div className="flex items-center gap-3 border-b border-[#1F2937] px-4 py-2 text-xs text-slate-300 bg-[#0F172A]/90">
          <span className="shrink-0 text-[10px] font-bold text-slate-400 uppercase">Original</span>
          <input
            type="range"
            min="0"
            max="100"
            value={splitPos}
            onChange={(e) => setSplitPos(Number(e.target.value))}
            className="flex-1 cursor-pointer appearance-none rounded-full bg-slate-700 h-1.5 accent-cyan-400"
            title="Comparison Slider position"
          />
          <span className="shrink-0 text-[10px] font-bold text-cyan-400 uppercase">Localization</span>
          <span className="w-8 text-right text-[10px] tabular-nums font-mono text-slate-400">{splitPos}%</span>
        </div>
      )}

      {/* Viewport Canvas */}
      <div
        ref={viewportRef}
        className={`relative flex-1 cursor-grab overflow-hidden active:cursor-grabbing select-none ${
          fullscreen ? "min-h-0" : "min-h-[300px] md:min-h-[420px]"
        }`}
        onPointerDown={(e) => {
          dragging.current = true;
          lastPos.current = { x: e.clientX, y: e.clientY };
        }}
        onPointerMove={(e) => {
          if (magnifierActive && viewportRef.current) {
            const rect = viewportRef.current.getBoundingClientRect();
            const relX = ((e.clientX - rect.left) / rect.width) * 100;
            const relY = ((e.clientY - rect.top) / rect.height) * 100;
            setMagnifierPos({ x: e.clientX - rect.left, y: e.clientY - rect.top, relX, relY });
          }
          if (!dragging.current) return;
          setPan((p) => ({
            x: p.x + (e.clientX - lastPos.current.x),
            y: p.y + (e.clientY - lastPos.current.y),
          }));
          lastPos.current = { x: e.clientX, y: e.clientY };
        }}
        onPointerUp={() => {
          dragging.current = false;
        }}
        onPointerLeave={() => {
          dragging.current = false;
        }}
      >
        {loading && (
          <div className="absolute inset-0 z-20 flex items-center justify-center bg-[#0B1120]/70 backdrop-blur-sm">
            <Loader2 className="h-8 w-8 animate-spin text-cyan-400" />
          </div>
        )}

        <motion.div
          className="absolute inset-0 flex items-center justify-center p-2"
          animate={{ x: pan.x, y: pan.y, scale: zoom }}
          transition={{ type: "spring", stiffness: 280, damping: 28 }}
        >
          <div className="relative inline-block max-h-full max-w-full">
            {/* Base Original Image */}
            <img
              src={originalUrl}
              alt="Original evidence"
              className="max-h-[450px] max-w-full object-contain select-none shadow-xl rounded"
              draggable={false}
              onLoad={(e) =>
                setNatural({
                  w: e.target.naturalWidth || 1,
                  h: e.target.naturalHeight || 1,
                })
              }
            />

            {/* Comparison Slider Mode */}
            {compareMode && showOverlay ? (
              <div
                className="absolute inset-0 overflow-hidden rounded"
                style={{ clipPath: `inset(0 0 0 ${splitPos}%)` }}
              >
                <img
                  src={activeOverlayUrl}
                  alt="Localization overlay"
                  className="max-h-[450px] w-full h-full object-contain select-none"
                  draggable={false}
                />
                <div
                  className="absolute top-0 bottom-0 w-0.5 bg-cyan-400 shadow-lg shadow-cyan-500/60"
                  style={{ left: `${splitPos}%` }}
                />
              </div>
            ) : showOverlay ? (
              <motion.img
                key={viewMode}
                initial={{ opacity: 0 }}
                animate={{ opacity: opacity }}
                src={activeOverlayUrl}
                alt={viewMode}
                className="pointer-events-none absolute inset-0 h-full w-full object-contain select-none rounded"
                draggable={false}
                onError={() => setImgError(true)}
              />
            ) : null}

            {/* Vector Region Overlays with Tooltips and Severity Badges */}
            {filteredRegions.length > 0 && (
              <div className="absolute inset-0 pointer-events-auto">
                {filteredRegions.map((reg, idx) => {
                  if (!reg) return null;
                  const nb = reg.normalized_bbox;
                  const b = reg.bbox || reg.bounding_box || {};
                  
                  let style = {};
                  if (Array.isArray(b) && b.length >= 4) {
                    if (b.length === 4 && b[2] < natural.w && b[3] < natural.h) {
                      // format [x, y, w, h]
                      style = {
                        left: `${(b[0] / natural.w) * 100}%`,
                        top: `${(b[1] / natural.h) * 100}%`,
                        width: `${(b[2] / natural.w) * 100}%`,
                        height: `${(b[3] / natural.h) * 100}%`,
                      };
                    } else if (b.length === 4) {
                      // format [x1, y1, x2, y2]
                      style = {
                        left: `${(b[0] / natural.w) * 100}%`,
                        top: `${(b[1] / natural.h) * 100}%`,
                        width: `${((b[2] - b[0]) / natural.w) * 100}%`,
                        height: `${((b[3] - b[1]) / natural.h) * 100}%`,
                      };
                    }
                  } else if (nb) {
                    style = {
                      left: `${nb.x * 100}%`,
                      top: `${nb.y * 100}%`,
                      width: `${nb.w * 100}%`,
                      height: `${nb.h * 100}%`,
                    };
                  } else {
                    style = {
                      left: `${((b.x || 0) / natural.w) * 100}%`,
                      top: `${((b.y || 0) / natural.h) * 100}%`,
                      width: `${((b.w || 0) / natural.w) * 100}%`,
                      height: `${((b.h || 0) / natural.h) * 100}%`,
                    };
                  }

                  const tone = getRiskTone(reg.score || reg.confidence || reg.confidence_pct);
                  const isSelected = selectedRegion?.id === reg.id || selectedRegion?.region_id === reg.region_id;
                  const isHovered = hoveredRegion?.id === reg.id;

                  return (
                    <div
                      key={reg.id || `reg-${idx}`}
                      className={`absolute border-2 transition-all cursor-pointer rounded-sm ${tone.border} ${tone.bg} ${
                        isSelected ? "ring-2 ring-cyan-300 ring-offset-2 ring-offset-[#0B1120] z-20 scale-[1.02]" : "hover:scale-[1.01]"
                      }`}
                      style={style}
                      onMouseEnter={() => setHoveredRegion(reg)}
                      onMouseLeave={() => setHoveredRegion(null)}
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectRegion?.(reg);
                      }}
                    >
                      {/* Region Human Label Tag */}
                      <span
                        className="absolute -top-5 left-0 rounded px-1.5 py-0.5 text-[9px] font-extrabold uppercase tracking-wider text-white shadow-md whitespace-nowrap max-w-[180px] overflow-hidden text-ellipsis"
                        style={{ backgroundColor: tone.hex }}
                      >
                        {humanizeRegionLabel(reg, idx)} · {getSeverityInfo(reg.score || reg.confidence || reg.confidence_pct).short}
                      </span>

                      {/* Interactive Hover Tooltip — Plain Language First */}
                      {isHovered && (
                        <div className="absolute bottom-full left-1/2 mb-2 w-60 -translate-x-1/2 rounded-xl border border-[#1F2937] bg-[#0B1120]/97 p-3 text-xs text-white shadow-2xl backdrop-blur-md z-30 pointer-events-none">
                          {/* What was found */}
                          <div className="border-b border-[#1F2937] pb-2 mb-2">
                            <p className={`text-[9px] font-bold uppercase tracking-widest mb-0.5 ${tone.text}`}>
                              {getSeverityInfo(reg.score || reg.confidence || reg.confidence_pct).short}
                            </p>
                            <p className="font-semibold text-white text-[11px] leading-snug">
                              {humanizeRegionLabel(reg, idx)}
                            </p>
                            {(reg.plain_english_explanation || reg.reason) && (
                              <p className="text-[10px] text-slate-300 mt-1 leading-snug">
                                {reg.plain_english_explanation || reg.reason}
                              </p>
                            )}
                          </div>
                          <div className="flex items-center justify-between text-[10px]">
                            <span className="text-slate-400">AI Certainty</span>
                            <span className={`font-black tabular-nums ${tone.text}`}>
                              {Math.round(Number(reg.confidence_pct || (reg.confidence > 1 ? reg.confidence : reg.confidence * 100) || 50))}%
                            </span>
                          </div>
                          <p className="mt-1.5 text-[9px] text-slate-500">Click to inspect · Scroll to zoom</p>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </motion.div>

        {/* Magnifier Loupe Circular Lens */}
        {magnifierActive && (
          <div
            className="pointer-events-none absolute h-36 w-36 rounded-full border-2 border-cyan-400 shadow-2xl overflow-hidden z-40"
            style={{
              left: `${magnifierPos.x - 72}px`,
              top: `${magnifierPos.y - 72}px`,
              backgroundImage: `url(${originalUrl})`,
              backgroundPosition: `${magnifierPos.relX}% ${magnifierPos.relY}%`,
              backgroundSize: `${(natural.w / 1.5) * zoom}px`,
            }}
          >
            <div className="absolute inset-0 rounded-full border border-white/30 ring-1 ring-cyan-500/50" />
          </div>
        )}
      </div>
    </div>
  );
}

export default InteractiveForensicPane;
