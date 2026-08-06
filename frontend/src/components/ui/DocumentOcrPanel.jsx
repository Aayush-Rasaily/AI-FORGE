import { motion } from "framer-motion";
import { FileText, Languages, Scan, AlertTriangle, Layout } from "lucide-react";

import { getArtifactUrl } from "../../services/api";
import RiskGauge from "./RiskGauge";

function EngineScoreBar({ label, score, delay = 0 }) {
  const pct = Math.round(Number(score || 0) * 100);
  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay }}
      className="space-y-1"
    >
      <div className="flex justify-between text-xs">
        <span className="text-slate-400">{label}</span>
        <span className="font-mono text-cyan-300">{pct}%</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-slate-800">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ delay: delay + 0.1, duration: 0.7 }}
          className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-blue-400"
        />
      </div>
    </motion.div>
  );
}

function DocumentOcrPanel({ ocr = {}, pageImage = "" }) {
  if (!ocr || Object.keys(ocr).length === 0) return null;

  const text =
    ocr.full_text || ocr.text || ocr.extracted_text || "";
  const ocrConfidence = Math.round(Number(ocr.ocr_confidence ?? ocr.word_confidence ?? 0) * 100);
  const charConf = Math.round(Number(ocr.character_confidence || 0) * 100);
  const wordConf = Math.round(Number(ocr.word_confidence || 0) * 100);
  const layoutConf = Math.round(Number(ocr.layout_confidence || 0) * 100);
  const language = ocr.detected_language || "unknown";
  const consensus = ocr.consensus || {};
  const engineResults = ocr.engine_results || {};
  const mismatchHeatmap = ocr.mismatch_heatmap || ocr.visualizations?.mismatch_heatmap || ocr.artifacts?.mismatch_heatmap;
  const layoutOverlay = ocr.layout_overlay || ocr.visualizations?.layout_overlay || ocr.artifacts?.layout_overlay;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="overflow-hidden rounded-2xl border border-cyan-500/20 bg-gradient-to-br from-cyan-500/5 via-[#111827] to-blue-500/5"
    >
      <div className="border-b border-cyan-500/10 px-6 py-4">
        <div className="flex items-center gap-2">
          <Scan className="h-5 w-5 text-cyan-400" />
          <h4 className="text-lg font-semibold text-white">Multi-Engine OCR</h4>
        </div>
        <p className="mt-1 text-xs text-slate-500">
          Tesseract · EasyOCR · PaddleOCR · TrOCR · Consensus voting
        </p>
      </div>

      <div className="grid gap-6 p-6 lg:grid-cols-3">
        <div className="flex flex-col items-center rounded-xl border border-cyan-500/10 bg-[#0B1120]/60 p-6">
          <RiskGauge score={ocrConfidence} size={160} label="OCR Confidence" />
          <div className="mt-4 flex items-center gap-2 text-sm text-slate-400">
            <Languages className="h-4 w-4 text-cyan-400" />
            <span>
              Language: <span className="text-white capitalize">{language}</span>
            </span>
          </div>
          {consensus.primary_engine && (
            <p className="mt-2 text-xs text-slate-500">
              Primary engine: <span className="text-cyan-300">{consensus.primary_engine}</span>
              {consensus.fastest_engine && (
                <> · Fastest: <span className="text-emerald-300">{consensus.fastest_engine}</span></>
              )}
            </p>
          )}
        </div>

        <div className="space-y-4 lg:col-span-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Confidence Breakdown
          </p>
          <div className="grid gap-3 sm:grid-cols-3">
            <EngineScoreBar label="Character" score={charConf / 100} delay={0} />
            <EngineScoreBar label="Word" score={wordConf / 100} delay={0.06} />
            <EngineScoreBar label="Layout" score={layoutConf / 100} delay={0.12} />
          </div>

          {Object.keys(engineResults).length > 0 && (
            <div className="mt-4">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
                Engine Comparison
              </p>
              <div className="grid gap-2 sm:grid-cols-2">
                {Object.entries(engineResults).map(([name, res]) => (
                  <div
                    key={name}
                    className={`rounded-lg border p-3 ${
                      res.success ? "border-[#1F2937] bg-[#0B1120]" : "border-red-500/20 bg-red-500/5"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium uppercase text-slate-400">{name}</span>
                      <span className={`text-xs ${res.success ? "text-emerald-400" : "text-red-400"}`}>
                        {res.success ? "✓" : "✗"}
                      </span>
                    </div>
                    {res.success && (
                      <p className="mt-1 font-mono text-sm text-white">
                        {Math.round(Number(res.word_confidence || 0) * 100)}% · {Math.round(res.elapsed_ms || 0)}ms
                      </p>
                    )}
                    {res.error && (
                      <p className="mt-1 text-[10px] text-red-400 line-clamp-2">{res.error}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-cyan-500/10 px-6 py-4">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-cyan-400" />
          <p className="text-xs font-semibold uppercase tracking-wider text-cyan-400">
            Text Extraction
          </p>
        </div>
        <div className="mt-3 max-h-48 overflow-y-auto rounded-lg border border-[#1F2937] bg-[#0B1120] p-4">
          <pre className="whitespace-pre-wrap text-sm leading-relaxed text-slate-300">
            {text || "No text extracted."}
          </pre>
        </div>
        {consensus.reasoning && (
          <p className="mt-3 text-xs leading-relaxed text-slate-500">{consensus.reasoning}</p>
        )}
      </div>

      {(mismatchHeatmap || layoutOverlay) && (
        <div className="grid gap-4 border-t border-cyan-500/10 p-6 lg:grid-cols-2">
          {mismatchHeatmap && (
            <div className="rounded-xl border border-amber-500/20 bg-[#0B1120] p-3">
              <div className="mb-2 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-400" />
                <p className="text-xs font-semibold uppercase text-amber-300">Mismatch Heatmap</p>
              </div>
              <img
                src={getArtifactUrl(mismatchHeatmap)}
                alt="OCR mismatch heatmap"
                className="w-full rounded-lg object-contain"
              />
            </div>
          )}
          {layoutOverlay && (
            <div className="rounded-xl border border-cyan-500/20 bg-[#0B1120] p-3">
              <div className="mb-2 flex items-center gap-2">
                <Layout className="h-4 w-4 text-cyan-400" />
                <p className="text-xs font-semibold uppercase text-cyan-300">Layout Overlay</p>
              </div>
              <img
                src={getArtifactUrl(layoutOverlay)}
                alt="OCR layout overlay"
                className="w-full rounded-lg object-contain"
              />
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
}

export default DocumentOcrPanel;
