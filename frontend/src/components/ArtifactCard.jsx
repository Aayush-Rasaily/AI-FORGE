import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ZoomIn,
  Download,
  Maximize2,
  X,
  ImageOff,
  Loader2,
} from "lucide-react";

function ArtifactCard({ title, description, artifactUrl }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [hovered, setHovered] = useState(false);

  const handleDownload = async () => {
    if (!artifactUrl) return;
    try {
      const res = await fetch(artifactUrl);
      if (!res.ok) return;
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

  return (
    <>
      <motion.div
        initial={{ opacity: 0, scale: 0.97 }}
        animate={{ opacity: 1, scale: 1 }}
        whileHover={{ y: -4 }}
        onHoverStart={() => setHovered(true)}
        onHoverEnd={() => setHovered(false)}
        className="group overflow-hidden rounded-2xl border border-[#1F2937] bg-[#111827] shadow-lg transition-shadow hover:shadow-blue-500/10 hover:border-blue-500/30"
      >
        <div className="p-4 border-b border-[#1F2937]">
          <h5 className="font-semibold text-white">{title}</h5>
          <p className="mt-0.5 text-xs text-slate-500">{description}</p>
        </div>

        <div className="relative overflow-hidden bg-[#0B1120]">
          {!artifactUrl ? (
            <div className="flex min-h-[220px] flex-col items-center justify-center gap-2 text-slate-600">
              <ImageOff className="h-8 w-8" />
              <p className="text-sm">Artifact not available</p>
            </div>
          ) : error ? (
            <div className="flex min-h-[220px] flex-col items-center justify-center gap-2 p-4 text-center">
              <ImageOff className="h-8 w-8 text-red-400" />
              <p className="text-sm text-red-400">Failed to load artifact</p>
              <p className="break-all text-[10px] text-slate-600">{artifactUrl}</p>
            </div>
          ) : (
            <>
              {loading && (
                <div className="absolute inset-0 z-10 flex items-center justify-center bg-[#0B1120]">
                  <Loader2 className="h-8 w-8 animate-spin text-cyan-500" />
                </div>
              )}

              <img
                src={artifactUrl}
                alt={title}
                className={`w-full object-contain transition-transform duration-300 ${
                  hovered ? "scale-105" : "scale-100"
                } max-h-[320px]`}
                onLoad={() => setLoading(false)}
                onError={() => {
                  setLoading(false);
                  setError(true);
                }}
              />

              {/* Hover actions */}
              <AnimatePresence>
                {hovered && !loading && !error && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="absolute inset-0 flex items-center justify-center gap-3 bg-black/50 backdrop-blur-sm"
                  >
                    <button
                      onClick={() => setFullscreen(true)}
                      className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/10 text-white transition hover:bg-white/20"
                      title="Fullscreen"
                    >
                      <Maximize2 className="h-4 w-4" />
                    </button>
                    <button
                      onClick={handleDownload}
                      className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/10 text-white transition hover:bg-white/20"
                      title="Download"
                    >
                      <Download className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => setFullscreen(true)}
                      className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/10 text-white transition hover:bg-white/20"
                      title="Zoom"
                    >
                      <ZoomIn className="h-4 w-4" />
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </>
          )}
        </div>
      </motion.div>

      {/* Fullscreen modal */}
      <AnimatePresence>
        {fullscreen && artifactUrl && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-4 backdrop-blur-md"
            onClick={() => setFullscreen(false)}
          >
            <button
              className="absolute right-4 top-4 flex h-10 w-10 items-center justify-center rounded-xl bg-white/10 text-white hover:bg-white/20"
              onClick={() => setFullscreen(false)}
            >
              <X className="h-5 w-5" />
            </button>
            <motion.img
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              src={artifactUrl}
              alt={title}
              className="max-h-[90vh] max-w-[90vw] object-contain rounded-xl"
              onClick={(e) => e.stopPropagation()}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

export default ArtifactCard;
