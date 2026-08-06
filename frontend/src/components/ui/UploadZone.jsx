import { useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, FileImage, CheckCircle } from "lucide-react";
import ProgressRing from "./ProgressRing";

function UploadZone({
  accept,
  multiple = true,
  supportedText,
  title,
  files = [],
  onFilesSelected,
  disabled = false,
  processing = false,
}) {
  const [dragging, setDragging] = useState(false);
  const [uploadState, setUploadState] = useState(null);
  const inputRef = useRef(null);

  const handleFiles = useCallback(
    (fileList) => {
      const selected = Array.from(fileList || []);
      if (selected.length === 0) return;

      setUploadState("success");
      onFilesSelected(selected);

      setTimeout(() => setUploadState(null), 2000);
    },
    [onFilesSelected]
  );

  const onDrop = useCallback(
    (e) => {
      e.preventDefault();
      setDragging(false);
      if (disabled) return;
      handleFiles(e.dataTransfer.files);
    },
    [disabled, handleFiles]
  );

  const onDragOver = (e) => {
    e.preventDefault();
    if (!disabled) setDragging(true);
  };

  const onDragLeave = () => setDragging(false);

  return (
    <div className="mt-8">
      <motion.div
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        animate={{
          borderColor: dragging
            ? "rgba(6,182,212,0.7)"
            : uploadState === "success"
              ? "rgba(34,197,94,0.5)"
              : "rgba(59,130,246,0.3)",
          scale: dragging ? 1.01 : 1,
        }}
        transition={{ duration: 0.2 }}
        className="relative overflow-hidden rounded-2xl border-2 border-dashed bg-[#111827]/60 p-10 text-center backdrop-blur-sm"
      >
        {/* Animated border glow */}
        {dragging && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="pointer-events-none absolute inset-0 bg-gradient-to-br from-cyan-500/5 to-blue-500/5"
          />
        )}

        <motion.div
          animate={dragging ? { y: -4 } : { y: 0 }}
          className="relative z-10"
        >
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-500/10 border border-blue-500/20">
            <Upload className="h-6 w-6 text-blue-400" />
          </div>

          <h3 className="text-xl font-semibold text-white">{title}</h3>
          <p className="mt-2 text-sm text-slate-400">{supportedText}</p>

          <p className="mt-3 text-xs text-slate-500">
            Drag & drop files here, or click to browse
          </p>

          <button
            type="button"
            disabled={disabled}
            onClick={() => inputRef.current?.click()}
            className="mt-6 inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-600 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-500/20 transition hover:from-blue-500 hover:to-cyan-500 disabled:opacity-50"
          >
            <FileImage className="h-4 w-4" />
            Select Files
          </button>

          <input
            ref={inputRef}
            type="file"
            multiple={multiple}
            accept={accept}
            className="hidden"
            disabled={disabled}
            onChange={(e) => handleFiles(e.target.files)}
          />
        </motion.div>

        {/* Success / error overlay */}
        <AnimatePresence>
          {uploadState === "success" && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 z-20 flex items-center justify-center bg-emerald-500/10 backdrop-blur-sm"
            >
              <CheckCircle className="h-10 w-10 text-emerald-400" />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Processing overlay */}
      {processing && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mt-6 flex flex-col items-center rounded-2xl border border-cyan-500/20 bg-cyan-500/5 p-8"
        >
          <ProgressRing progress={75} size={100} label="Analyzing evidence..." />
          <p className="mt-4 text-sm text-cyan-400">Estimated time: ~15 seconds</p>
        </motion.div>
      )}
      {files.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-6 space-y-3"
        >
          <h4 className="text-sm font-semibold text-slate-300">
            Selected Evidence ({files.length})
          </h4>

          {files.map((file, i) => (
            <motion.div
              key={`${file.name}-${i}`}
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className="flex items-center justify-between rounded-xl border border-[#1F2937] bg-[#111827] p-4"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10">
                  <FileImage className="h-5 w-5 text-blue-400" />
                </div>
                <div>
                  <p className="font-medium text-white text-sm">{file.name}</p>
                  <p className="text-xs text-slate-500">
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
              </div>
              <span className="flex items-center gap-1 text-xs text-emerald-400">
                <CheckCircle className="h-3.5 w-3.5" />
                Ready
              </span>
            </motion.div>
          ))}
        </motion.div>
      )}
    </div>
  );
}

export default UploadZone;
