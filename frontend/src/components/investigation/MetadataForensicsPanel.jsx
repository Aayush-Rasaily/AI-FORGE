/**
 * MetadataForensicsPanel.jsx
 *
 * Dedicated metadata discrepancy display for AI-FORGE.
 *
 * Shows:
 *   - Creation timestamp vs. modification timestamp (with gap highlighted)
 *   - Visible document date vs. file modification timestamp discrepancy
 *   - Author, software, producer
 *   - Hash/integrity status
 *   - Plain-language discrepancy explanation
 *
 * FORENSIC PRINCIPLE: Metadata alone cannot conclusively establish
 * intentional manipulation. Always stated explicitly.
 */

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Database,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Calendar,
  User,
  Monitor,
  Clock,
  ShieldCheck,
  ShieldAlert,
  Info,
} from "lucide-react";

// ─── Individual metadata row ──────────────────────────────────────────────────

function MetaRow({ label, value, highlight = false }) {
  if (value == null || value === "" || value === false) return null;
  return (
    <div
      className={`flex items-start justify-between gap-4 py-2 text-xs border-b border-slate-800/60 last:border-0 ${
        highlight ? "metadata-discrepancy -mx-2 px-2 my-1" : ""
      }`}
    >
      <span className="shrink-0 text-slate-500">{label}</span>
      <span
        className={`text-right font-medium max-w-[60%] break-words ${
          highlight ? "text-orange-300" : "text-slate-200"
        }`}
      >
        {String(value)}
      </span>
    </div>
  );
}

// ─── Discrepancy callout ──────────────────────────────────────────────────────

function DiscrepancyCallout({ explanation }) {
  if (!explanation) return null;
  return (
    <div className="rounded-lg border border-orange-500/30 bg-orange-500/8 p-3.5">
      <div className="flex items-start gap-2">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-orange-400" />
        <div>
          <p className="text-xs font-semibold text-orange-300 mb-1">
            Metadata Discrepancy Detected
          </p>
          <p className="text-xs leading-relaxed text-slate-300">{explanation}</p>
        </div>
      </div>
    </div>
  );
}

// ─── Main MetadataForensicsPanel ─────────────────────────────────────────────

function MetadataForensicsPanel({ metadata }) {
  const [expanded, setExpanded] = useState(true);

  if (!metadata) return null;

  const {
    creation,
    modified,
    author,
    software,
    producer,
    gpsPresent,
    thumbnailMismatch,
    dateGapDays,
    hasDateDiscrepancy,
    visibleDocumentDate,
    metadataModificationDate,
    discrepancyExplanation,
    riskScore,
    integrityPassed,
    integrityMessage,
  } = metadata;

  const hasAnyData =
    creation || modified || author || software || producer ||
    gpsPresent || thumbnailMismatch || discrepancyExplanation;

  if (!hasAnyData) return null;

  return (
    <motion.section
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-blue-500/20 bg-[#0a1628]/80 overflow-hidden"
    >
      {/* Header */}
      <button
        type="button"
        onClick={() => setExpanded((s) => !s)}
        className="flex w-full items-center justify-between px-5 py-3.5 text-left hover:bg-white/[0.02] transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-500/15 border border-blue-500/25">
            <Database className="h-3.5 w-3.5 text-blue-400" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-200">Document Metadata</p>
            <p className="text-[11px] text-slate-500">
              File history · Creation & modification records
            </p>
          </div>
          {hasDateDiscrepancy && (
            <span className="ml-1 inline-flex items-center gap-1 rounded-full border border-orange-500/40 bg-orange-500/10 px-2 py-0.5 text-[10px] font-bold text-orange-400">
              <AlertTriangle className="h-2.5 w-2.5" />
              Discrepancy
            </span>
          )}
        </div>
        {expanded ? (
          <ChevronUp className="h-4 w-4 text-slate-500" />
        ) : (
          <ChevronDown className="h-4 w-4 text-slate-500" />
        )}
      </button>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22 }}
            className="overflow-hidden"
          >
            <div className="border-t border-slate-800/60 px-5 pb-5 pt-4 space-y-4">

              {/* Discrepancy callout — shown first when present */}
              {discrepancyExplanation && (
                <DiscrepancyCallout explanation={discrepancyExplanation} />
              )}

              {/* Timeline comparison */}
              {(visibleDocumentDate || creation || modified) && (
                <div className="rounded-lg border border-slate-800 bg-slate-900/40">
                  <div className="px-3 py-2 border-b border-slate-800">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                      <Clock className="h-3 w-3" />
                      Document Timeline
                    </p>
                  </div>
                  <div className="px-3 py-2 divide-y divide-slate-800/40">
                    {visibleDocumentDate && (
                      <MetaRow
                        label="Visible Document Date"
                        value={visibleDocumentDate}
                      />
                    )}
                    {creation && (
                      <MetaRow label="File Creation Date" value={creation} />
                    )}
                    {modified && (
                      <MetaRow
                        label="Last Modified"
                        value={modified}
                        highlight={hasDateDiscrepancy}
                      />
                    )}
                    {dateGapDays != null && dateGapDays > 0 && (
                      <MetaRow
                        label="Modification Gap"
                        value={`${dateGapDays} day${dateGapDays !== 1 ? "s" : ""} after stated creation`}
                        highlight
                      />
                    )}
                  </div>
                </div>
              )}

              {/* Author / software */}
              {(author || software || producer) && (
                <div className="rounded-lg border border-slate-800 bg-slate-900/40">
                  <div className="px-3 py-2 border-b border-slate-800">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                      <Monitor className="h-3 w-3" />
                      Authoring Information
                    </p>
                  </div>
                  <div className="px-3 py-2 divide-y divide-slate-800/40">
                    {author && <MetaRow label="Author" value={author} />}
                    {software && <MetaRow label="Editing Software" value={software} />}
                    {producer && <MetaRow label="PDF Producer" value={producer} />}
                  </div>
                </div>
              )}

              {/* Additional flags */}
              {(gpsPresent || thumbnailMismatch) && (
                <div className="space-y-2">
                  {gpsPresent && (
                    <div className="flex items-center gap-2 rounded-lg border border-blue-500/20 bg-blue-500/5 px-3 py-2 text-xs text-slate-300">
                      <Info className="h-3.5 w-3.5 shrink-0 text-blue-400" />
                      GPS location data is embedded in this file's metadata.
                    </div>
                  )}
                  {thumbnailMismatch && (
                    <div className="flex items-center gap-2 rounded-lg border border-orange-500/25 bg-orange-500/5 px-3 py-2 text-xs text-slate-300">
                      <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-orange-400" />
                      Embedded thumbnail does not match the document content.
                    </div>
                  )}
                </div>
              )}

              {/* Integrity status */}
              {integrityPassed != null && (
                <div
                  className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-xs ${
                    integrityPassed
                      ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-300"
                      : "border-red-500/30 bg-red-500/5 text-red-300"
                  }`}
                >
                  {integrityPassed ? (
                    <ShieldCheck className="h-3.5 w-3.5 shrink-0" />
                  ) : (
                    <ShieldAlert className="h-3.5 w-3.5 shrink-0" />
                  )}
                  {integrityMessage ||
                    (integrityPassed
                      ? "Evidence remains unchanged since submission."
                      : "Evidence integrity check failed — file may have been modified.")}
                </div>
              )}

              {/* Forensic disclaimer */}
              <div className="rounded-lg border border-slate-800 bg-slate-900/30 px-3 py-2.5">
                <p className="text-[11px] leading-relaxed text-slate-500">
                  <span className="font-semibold text-slate-400">Note: </span>
                  Metadata findings indicate possible anomalies in document history.
                  Metadata alone cannot conclusively establish intentional manipulation.
                  Manual expert review is recommended.
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.section>
  );
}

export default MetadataForensicsPanel;
