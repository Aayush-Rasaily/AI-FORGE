import { useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  AlertTriangle,
  FileWarning,
  Stamp,
  PenLine,
  Type,
  AlignJustify,
  ImageIcon,
  LayoutTemplate,
  FileX,
} from "lucide-react";

import { getArtifactUrl } from "../../services/api";
import RiskGauge from "./RiskGauge";

const ISSUE_META = {
  header_inconsistency: { icon: LayoutTemplate, label: "Header Inconsistency", color: "#f97316" },
  signature_mismatch: { icon: PenLine, label: "Signature Mismatch", color: "#ef4444" },
  fake_stamp: { icon: Stamp, label: "Fake Stamp", color: "#dc2626" },
  logo_manipulation: { icon: ImageIcon, label: "Logo Manipulation", color: "#eab308" },
  wrong_font: { icon: Type, label: "Wrong Font", color: "#a855f7" },
  spacing_anomaly: { icon: AlignJustify, label: "Spacing Anomaly", color: "#06b6d4" },
  tampered_paragraph: { icon: FileWarning, label: "Tampered Paragraph", color: "#f43f5e" },
  layout_anomaly: { icon: LayoutTemplate, label: "Layout Anomaly", color: "#fb923c" },
};

const SEVERITY_STYLES = {
  critical: "border-red-500/40 bg-red-500/10 text-red-300",
  high: "border-orange-500/40 bg-orange-500/10 text-orange-300",
  medium: "border-yellow-500/40 bg-yellow-500/10 text-yellow-300",
  low: "border-slate-600/40 bg-slate-700/30 text-slate-400",
};

function bboxToStyle(bbox, imgW, imgH) {
  if (!bbox || !Array.isArray(bbox) || bbox.length < 2 || !imgW || !imgH) return null;
  const xs = bbox.map((p) => (Array.isArray(p) ? p[0] : 0));
  const ys = bbox.map((p) => (Array.isArray(p) ? p[1] : 0));
  const x1 = Math.min(...xs);
  const y1 = Math.min(...ys);
  const x2 = Math.max(...xs);
  const y2 = Math.max(...ys);
  return {
    left: `${(x1 / imgW) * 100}%`,
    top: `${(y1 / imgH) * 100}%`,
    width: `${((x2 - x1) / imgW) * 100}%`,
    height: `${((y2 - y1) / imgH) * 100}%`,
  };
}

function IssueCard({ issue, selected, onClick }) {
  const meta = ISSUE_META[issue.type] || { icon: AlertTriangle, label: issue.type, color: "#94a3b8" };
  const Icon = meta.icon;
  const severity = issue.severity || "medium";

  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full rounded-xl border p-4 text-left transition ${
        selected
          ? "border-cyan-500/50 bg-cyan-500/10"
          : "border-slate-800 bg-slate-950 hover:border-slate-700"
      }`}
    >
      <div className="flex items-start gap-3">
        <div
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg"
          style={{ backgroundColor: `${meta.color}22`, color: meta.color }}
        >
          <Icon className="h-4 w-4" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold text-white">{meta.label}</span>
            <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase ${SEVERITY_STYLES[severity] || SEVERITY_STYLES.medium}`}>
              {severity}
            </span>
            <span className="text-xs text-slate-500">
              {Math.round((issue.score || 0) * 100)}% confidence
            </span>
          </div>
          <p className="mt-1 text-xs leading-relaxed text-slate-400">{issue.description}</p>
        </div>
      </div>
    </button>
  );
}

function DocumentPageViewer({ pages = [], missingPages = null }) {
  const [selectedPage, setSelectedPage] = useState(0);
  const [selectedIssue, setSelectedIssue] = useState(null);
  const [imgSize, setImgSize] = useState({ w: 0, h: 0 });
  const imgRef = useRef(null);

  const activePage = pages[selectedPage] || pages[0];
  const issues = activePage?.issues || activePage?.intelligence?.issues || [];
  const confidencePct = Math.round(
    Number(activePage?.page_confidence_pct ?? (activePage?.page_confidence || 0) * 100)
  );
  const heatmapPath =
    activePage?.heatmap?.heatmap ||
    activePage?.heatmap?.path ||
    activePage?.heatmap?.output_path;

  const highlightedIssue = useMemo(
    () => issues.find((_, i) => i === selectedIssue) || null,
    [issues, selectedIssue]
  );

  if (!pages.length) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-8 text-center text-slate-400">
        No pages available for interactive viewing.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page thumbnails */}
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
        <h3 className="text-sm font-semibold text-white">Pages — click to inspect</h3>
        <div className="mt-4 flex gap-3 overflow-x-auto pb-2">
          {pages.map((page, index) => {
            const pct = Math.round(
              Number(page.page_confidence_pct ?? (page.page_confidence || 0) * 100)
            );
            const issueCount = (page.issues || page.intelligence?.issues || []).length;
            const isActive = selectedPage === index;

            return (
              <button
                key={page.page_number ?? index}
                type="button"
                onClick={() => {
                  setSelectedPage(index);
                  setSelectedIssue(null);
                }}
                className={`group relative shrink-0 overflow-hidden rounded-lg border-2 transition ${
                  isActive
                    ? "border-cyan-500 shadow-lg shadow-cyan-500/20"
                    : "border-slate-700 hover:border-slate-500"
                }`}
              >
                {page.image ? (
                  <img
                    src={getArtifactUrl(page.image)}
                    alt={`Page ${page.page_number || index + 1}`}
                    className="h-28 w-20 object-cover"
                  />
                ) : (
                  <div className="flex h-28 w-20 items-center justify-center bg-slate-800 text-xs text-slate-500">
                    P{page.page_number || index + 1}
                  </div>
                )}
                <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/90 to-transparent px-1.5 py-1.5">
                  <p className="text-[10px] font-semibold text-white">
                    Page {page.page_number || index + 1}
                  </p>
                  <p className={`text-[9px] ${pct >= 70 ? "text-emerald-400" : pct >= 45 ? "text-yellow-400" : "text-red-400"}`}>
                    {pct}% authentic
                  </p>
                </div>
                {issueCount > 0 && (
                  <span className="absolute right-1 top-1 rounded-full bg-red-500 px-1.5 py-0.5 text-[9px] font-bold text-white">
                    {issueCount}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {missingPages?.missing_page_detected && (
        <div className="flex items-start gap-3 rounded-xl border border-red-500/30 bg-red-500/10 p-4">
          <FileX className="mt-0.5 h-5 w-5 shrink-0 text-red-400" />
          <div>
            <p className="font-semibold text-red-300">Missing Pages Detected</p>
            <p className="mt-1 text-sm text-red-200/80">
              Possible gaps in page sequence: {missingPages.missing_pages?.join(", ") || "unknown"}
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-5">
        {/* Page canvas */}
        <div className="xl:col-span-3">
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-lg font-bold text-white">
                  Page {activePage?.page_number || selectedPage + 1}
                </h3>
                <p className="text-xs text-slate-500">
                  LayoutLMv3 + Donut · click issues to highlight regions
                </p>
              </div>
              <div className="w-28">
                <RiskGauge
                  score={confidencePct}
                  label="Authenticity"
                  invert
                  size={100}
                />
              </div>
            </div>

            <div className="relative overflow-hidden rounded-lg bg-black">
              {activePage?.image && (
                <>
                  <img
                    ref={imgRef}
                    src={getArtifactUrl(activePage.image)}
                    alt={`Page ${activePage.page_number}`}
                    className="max-h-[600px] w-full object-contain"
                    onLoad={(e) =>
                      setImgSize({
                        w: e.target.naturalWidth,
                        h: e.target.naturalHeight,
                      })
                    }
                  />
                  {issues.map((issue, idx) => {
                    const style = bboxToStyle(issue.bbox, imgSize.w, imgSize.h);
                    if (!style) return null;
                    const meta = ISSUE_META[issue.type] || { color: "#ef4444" };
                    const isHighlighted = selectedIssue === idx || selectedIssue === null;
                    return (
                      <div
                        key={`${issue.type}-${idx}`}
                        className="pointer-events-none absolute border-2 transition-opacity"
                        style={{
                          ...style,
                          borderColor: meta.color,
                          backgroundColor: `${meta.color}${isHighlighted ? "33" : "11"}`,
                          opacity: selectedIssue === null || selectedIssue === idx ? 1 : 0.25,
                        }}
                      />
                    );
                  })}
                </>
              )}
            </div>

            {heatmapPath && (
              <div className="mt-4">
                <p className="mb-2 text-xs font-medium text-slate-400">Forensic Heatmap</p>
                <img
                  src={getArtifactUrl(heatmapPath)}
                  alt="Forensic heatmap"
                  className="max-h-48 w-full rounded-lg object-contain opacity-90"
                />
              </div>
            )}
          </div>
        </div>

        {/* Issues panel */}
        <div className="xl:col-span-2">
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-white">Detected Issues</h3>
              <span className="rounded-full bg-slate-800 px-2.5 py-1 text-xs text-slate-400">
                {issues.length} found
              </span>
            </div>

            <AnimatePresence mode="wait">
              {issues.length === 0 ? (
                <motion.p
                  key="no-issues"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="mt-6 text-sm text-emerald-400"
                >
                  No tampering signals detected on this page.
                </motion.p>
              ) : (
                <motion.div
                  key={`issues-${selectedPage}`}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-4 space-y-3"
                >
                  {issues.map((issue, idx) => (
                    <IssueCard
                      key={`${issue.type}-${idx}`}
                      issue={issue}
                      selected={selectedIssue === idx}
                      onClick={() =>
                        setSelectedIssue(selectedIssue === idx ? null : idx)
                      }
                    />
                  ))}
                </motion.div>
              )}
            </AnimatePresence>

            {activePage?.intelligence && (
              <div className="mt-6 space-y-2 border-t border-slate-800 pt-4">
                <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
                  Model Scores
                </p>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="rounded-lg bg-slate-950 p-3">
                    <p className="text-slate-500">LayoutLMv3</p>
                    <p className="mt-1 font-mono text-cyan-300">
                      {Math.round(
                        (activePage.intelligence.layoutlmv3?.layout_anomaly_score || 0) * 100
                      )}
                      % anomaly
                    </p>
                  </div>
                  <div className="rounded-lg bg-slate-950 p-3">
                    <p className="text-slate-500">Donut</p>
                    <p className="mt-1 font-mono text-purple-300">
                      {Math.round(
                        (activePage.intelligence.donut?.parse_anomaly_score || 0) * 100
                      )}
                      % parse gap
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default DocumentPageViewer;
