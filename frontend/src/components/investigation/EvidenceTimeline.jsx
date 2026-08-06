import { motion } from "framer-motion";
import { FileImage, FileText, Clock, CheckCircle, AlertCircle, Video } from "lucide-react";
import { useBackend } from "../../context/BackendConnectivity";

function EvidenceTimeline({ results = [], selectedEvidenceId, onSelect }) {
  const { evidence: sharedEvidence } = useBackend();

  // Merge session results with shared DB inventory (session takes precedence)
  const sessionIds = new Set(results.map((r) => r.evidenceId).filter(Boolean));
  const merged = [
    ...results.map((r) => ({
      evidenceId: r.evidenceId,
      filename: r.filename || r.original_filename,
      fileType: r.fileType || r.media_type || "image",
      status: r.status || "completed",
      hashes: r.hashes,
      analysis: r.analysis,
      intakeTimestamp: r.intakeTimestamp,
      source: "session",
    })),
    ...sharedEvidence
      .filter((e) => e.evidence_id && !sessionIds.has(e.evidence_id))
      .map((e) => ({
        evidenceId: e.evidence_id,
        filename: e.original_filename || e.evidence_id,
        fileType: e.media_type || "evidence",
        status: e.status || "registered",
        hashes: { sha256: e.sha256, sha512: e.sha512 },
        analysis: null,
        intakeTimestamp: e.intake_timestamp,
        source: "shared",
      })),
  ];

  if (!merged.length) {
    return (
      <div className="rounded-2xl border border-[#1F2937] bg-[#111827]/60 p-6 text-center">
        <Clock className="mx-auto h-8 w-8 text-slate-600" />
        <p className="mt-3 text-sm text-slate-500">No evidence analyzed yet</p>
        <p className="text-xs text-slate-600">Upload files to begin investigation</p>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-5 backdrop-blur-xl">
      <h3 className="mb-4 text-sm font-semibold text-white">Evidence Timeline</h3>
      <div className="relative space-y-0">
        <div className="absolute left-[15px] top-2 bottom-2 w-px bg-gradient-to-b from-blue-500/50 via-cyan-500/30 to-transparent" />

        {merged.map((item, i) => {
          const isFailed = item.status === "failed";
          const isSelected = item.evidenceId === selectedEvidenceId;
          const Icon =
            item.fileType === "document" || item.fileType === "pdf"
              ? FileText
              : item.fileType === "video"
                ? Video
                : FileImage;

          return (
            <motion.div
              key={`${item.evidenceId || item.filename}-${i}`}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: Math.min(i * 0.05, 0.4) }}
              className="relative flex cursor-pointer gap-4 pb-5 last:pb-0"
              onClick={() => item.evidenceId && onSelect?.(item.evidenceId)}
            >
              <div
                className={`relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border ${
                  isFailed
                    ? "border-red-500/50 bg-red-500/10"
                    : "border-emerald-500/50 bg-emerald-500/10"
                }`}
              >
                {isFailed ? (
                  <AlertCircle className="h-3.5 w-3.5 text-red-400" />
                ) : (
                  <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />
                )}
              </div>

              <div
                className={`min-w-0 flex-1 rounded-xl border p-3 transition-colors ${
                  isSelected
                    ? "border-cyan-500/50 bg-cyan-500/5"
                    : "border-[#1F2937] bg-[#0B1120]/60"
                }`}
              >
                <div className="flex items-start gap-2">
                  <Icon className="mt-0.5 h-4 w-4 shrink-0 text-slate-500" />
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-white">
                      {item.filename}
                    </p>
                    <p className="mt-0.5 text-xs capitalize text-slate-500">
                      {item.fileType} · {item.status}
                    </p>
                    {item.hashes?.sha256 && (
                      <p className="mt-1 truncate font-mono text-[9px] text-slate-600">
                        SHA-256: {item.hashes.sha256.slice(0, 16)}…
                      </p>
                    )}
                    {item.analysis?.verdict && (
                      <p className="mt-1 text-xs font-semibold text-cyan-400">
                        {item.analysis.verdict}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

export default EvidenceTimeline;
