import { useState, useRef, useCallback, useEffect } from "react";
import { motion } from "framer-motion";
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  Minimize2,
  SplitSquareHorizontal,
  Layers,
  RotateCcw,
  Download,
  ImageOff,
} from "lucide-react";
import { getArtifactUrl } from "../services/api";

/**
 * Interactive forensic viewer — zoom, pan, compare, split slider, opacity overlay.
 */
function ForensicViewer({
  originalUrl,
  overlayUrl,
  overlayLabel = "Forensic Overlay",
  title = "Forensic Viewer",
}) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [fullscreen, setFullscreen] = useState(false);
  const [compareMode, setCompareMode] = useState(false);
  const [splitPos, setSplitPos] = useState(50);
  const [opacity, setOpacity] = useState(0.55);
  const [imgError, setImgError] = useState(false);
  const [resolution, setResolution] = useState(null);
  const dragging = useRef(false);
  const lastPos = useRef({ x: 0, y: 0 });
  const viewportRef = useRef(null);

  const resetView = useCallback(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setSplitPos(50);
  }, []);

  useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;

    const onWheel = (e) => {
      if (e.cancelable) e.preventDefault();
      setZoom((z) => Math.min(4, Math.max(0.5, z + (e.deltaY > 0 ? -0.1 : 0.1))));
    };

    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape" && fullscreen) setFullscreen(false);
      if (e.key === "+" || e.key === "=") setZoom((z) => Math.min(4, z + 0.2));
      if (e.key === "-") setZoom((z) => Math.max(0.5, z - 0.2));
      if (e.key === "0") resetView();
      if (e.key === "f") setFullscreen((f) => !f);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [fullscreen, resetView]);

  const onPointerDown = (e) => {
    dragging.current = true;
    lastPos.current = { x: e.clientX, y: e.clientY };
  };

  const onPointerMove = (e) => {
    if (!dragging.current) return;
    setPan((p) => ({
      x: p.x + (e.clientX - lastPos.current.x),
      y: p.y + (e.clientY - lastPos.current.y),
    }));
    lastPos.current = { x: e.clientX, y: e.clientY };
  };

  const onPointerUp = () => {
    dragging.current = false;
  };

  const orig = originalUrl ? getArtifactUrl(originalUrl) : "";
  const overlay = overlayUrl ? getArtifactUrl(overlayUrl) : "";

  const handleDownload = async () => {
    const src = orig || overlay;
    if (!src) return;
    try {
      const res = await fetch(src);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${title.replace(/\s+/g, "_").toLowerCase()}.jpg`;
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      /* ignore */
    }
  };

  if (!orig && !overlay) return null;

  const containerClass = fullscreen
    ? "fixed inset-0 z-50 bg-black/95 p-4"
    : "rounded-2xl border border-[#1F2937] bg-[#0B1120]/80 backdrop-blur-xl overflow-hidden";

  return (
    <div className={containerClass}>
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#1F2937] px-4 py-3">
        <div>
          <h4 className="font-semibold text-white">{title}</h4>
          {resolution && (
            <p className="text-[10px] text-slate-500">
              {resolution.w} × {resolution.h}px · {Math.round(zoom * 100)}%
            </p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setCompareMode(!compareMode)}
            className={`flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              compareMode
                ? "bg-cyan-500/20 text-cyan-300"
                : "bg-slate-800 text-slate-400 hover:text-white"
            }`}
          >
            <SplitSquareHorizontal className="h-3.5 w-3.5" />
            Compare
          </button>
          <button type="button" onClick={() => setZoom((z) => Math.min(4, z + 0.2))} className="rounded-lg bg-slate-800 p-2 text-slate-400 hover:text-white" title="Zoom in">
            <ZoomIn className="h-4 w-4" />
          </button>
          <button type="button" onClick={() => setZoom((z) => Math.max(0.5, z - 0.2))} className="rounded-lg bg-slate-800 p-2 text-slate-400 hover:text-white" title="Zoom out">
            <ZoomOut className="h-4 w-4" />
          </button>
          <button type="button" onClick={resetView} className="rounded-lg bg-slate-800 p-2 text-slate-400 hover:text-white" title="Reset zoom">
            <RotateCcw className="h-4 w-4" />
          </button>
          <button type="button" onClick={handleDownload} className="rounded-lg bg-slate-800 p-2 text-slate-400 hover:text-white" title="Download">
            <Download className="h-4 w-4" />
          </button>
          <button type="button" onClick={() => setFullscreen(!fullscreen)} className="rounded-lg bg-slate-800 p-2 text-slate-400 hover:text-white" title="Fullscreen">
            {fullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {compareMode && overlay && (
        <div className="flex items-center gap-3 px-4 py-2 text-xs text-slate-400">
          <Layers className="h-3.5 w-3.5" />
          <span>{overlayLabel} opacity</span>
          <input
            type="range"
            min="0"
            max="100"
            value={opacity * 100}
            onChange={(e) => setOpacity(Number(e.target.value) / 100)}
            className="flex-1 accent-cyan-500"
          />
          <input
            type="range"
            min="5"
            max="95"
            value={splitPos}
            onChange={(e) => setSplitPos(Number(e.target.value))}
            className="w-24 accent-emerald-500"
            title="Split position"
          />
        </div>
      )}

      <div
        ref={viewportRef}
        className="relative h-[min(70vh,480px)] cursor-grab overflow-hidden active:cursor-grabbing"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerLeave={onPointerUp}
      >
        {imgError ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-slate-500">
            <ImageOff className="h-10 w-10" />
            <p className="text-sm">Artifact not available</p>
          </div>
        ) : (
          <motion.div
            className="absolute inset-0 flex items-center justify-center"
            style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})` }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
          >
            {compareMode && overlay ? (
              <div className="relative max-h-full max-w-full">
                <img
                  src={orig}
                  alt="Original"
                  className="max-h-[460px] object-contain"
                  draggable={false}
                  onLoad={(e) => setResolution({ w: e.target.naturalWidth, h: e.target.naturalHeight })}
                  onError={() => setImgError(true)}
                />
                <div
                  className="absolute inset-0 overflow-hidden"
                  style={{ clipPath: `inset(0 ${100 - splitPos}% 0 0)` }}
                >
                  <img
                    src={overlay}
                    alt={overlayLabel}
                    className="max-h-[460px] object-contain"
                    style={{ opacity }}
                    draggable={false}
                    onError={() => setImgError(true)}
                  />
                </div>
                <div
                  className="absolute top-0 bottom-0 w-0.5 bg-cyan-400 shadow-lg"
                  style={{ left: `${splitPos}%` }}
                />
              </div>
            ) : (
              <img
                src={orig || overlay}
                alt={title}
                className="max-h-[460px] object-contain"
                draggable={false}
                onLoad={(e) => setResolution({ w: e.target.naturalWidth, h: e.target.naturalHeight })}
                onError={() => setImgError(true)}
              />
            )}
          </motion.div>
        )}
      </div>
    </div>
  );
}

export default ForensicViewer;
