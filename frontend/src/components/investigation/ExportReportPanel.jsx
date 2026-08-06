import { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import {
  Download,
  FileText,
  FileJson,
  FileType,
  Scale,
  Briefcase,
  Wrench,
  Fingerprint,
  Loader2,
  CheckCircle,
} from "lucide-react";
import {
  downloadReport,
  getReportFormats,
  getReportPreviewUrl,
  getReportStatus,
  pollReportReady,
  generateReport,
  ApplicationError,
  ConnectivityError,
  formatApiError,
} from "../../services/api";
import { useBackend } from "../../context/BackendConnectivity";

const FORMAT_ICONS = {
  pdf: FileText,
  docx: FileType,
  json: FileJson,
  html: FileText,
};

const TEMPLATE_ICONS = {
  full: FileText,
  executive: Briefcase,
  technical: Wrench,
  court: Scale,
  evidence: Fingerprint,
};

const GENERATING_LABEL =
  "Generating professional forensic report… Estimated time: 3–5 seconds";

function ExportReportPanel({ evidenceId, juryData = null, reportsPending: initialReportsPending = true }) {
  const { backendOnline, setApiError } = useBackend();
  const [formats, setFormats] = useState(null);
  const [selectedFormat, setSelectedFormat] = useState("pdf");
  const [selectedTemplate, setSelectedTemplate] = useState("full");
  const [exporting, setExporting] = useState(false);
  const [progressMsg, setProgressMsg] = useState("");
  const [lastExport, setLastExport] = useState(null);
  const [error, setError] = useState("");
  const [reportsReady, setReportsReady] = useState(!initialReportsPending);
  const [reportStatus, setReportStatus] = useState(
    initialReportsPending ? "processing" : "completed"
  );
  const abortRef = useRef(false);

  useEffect(() => {
    abortRef.current = false;
    if (!evidenceId || !backendOnline) return undefined;

    let cancelled = false;
    let timer = null;
    let attempts = 0;
    const maxAttempts = 10;

    const check = async () => {
      if (cancelled || abortRef.current || attempts >= maxAttempts) return;
      attempts += 1;
      try {
        if (attempts === 1) {
          await generateReport(evidenceId);
        }
        const status = await getReportStatus(evidenceId);
        if (cancelled) return;
        const ready = Boolean(status.report_ready || status.ready || status.status === "completed");
        setReportsReady(ready);
        setReportStatus(status.status || (ready ? "completed" : "processing"));
        if (ready || status.status === "failed") {
          if (status.status === "failed" && !ready) {
            setError(status.reason || "Report generation failed.");
          }
          return;
        }
      } catch {
        // Transient — keep Online status unchanged
      }
      if (!cancelled && attempts < maxAttempts) {
        timer = setTimeout(check, 800);
      }
    };

    check();
    return () => {
      cancelled = true;
      abortRef.current = true;
      if (timer) clearTimeout(timer);
    };
  }, [evidenceId, backendOnline]);

  useEffect(() => {
    getReportFormats()
      .then(setFormats)
      .catch(() =>
        setFormats({
          formats: [
            { id: "pdf", label: "PDF Report" },
            { id: "docx", label: "DOCX Report" },
            { id: "html", label: "HTML Report" },
            { id: "json", label: "JSON Report" },
          ],
          templates: [
            { id: "full", label: "Full Report" },
            { id: "executive", label: "Executive Summary" },
            { id: "technical", label: "Technical Summary" },
            { id: "court", label: "Court Report" },
            { id: "evidence", label: "Evidence Summary" },
          ],
        })
      );
  }, []);

  const mapReportError = (err) => {
    if (err instanceof ApplicationError) {
      setApiError?.(err.message);
      return err.message;
    }
    if (err instanceof ConnectivityError) {
      setApiError?.("Connectivity Error — retry download");
      return "Connectivity Error — retry download. Backend status is unchanged.";
    }
    return formatApiError(err, "Failed to generate report.");
  };

  const handleExport = async () => {
    if (!evidenceId) return;
    if (!backendOnline) {
      setError("Backend Offline — reconnect via health check first.");
      return;
    }
    setExporting(true);
    setError("");
    try {
      if (!reportsReady) {
        setProgressMsg(GENERATING_LABEL);
        await pollReportReady(evidenceId, { onProgress: setProgressMsg });
        setReportsReady(true);
        setReportStatus("completed");
      }
      setProgressMsg("Downloading…");
      const result = await downloadReport(
        evidenceId,
        selectedFormat,
        selectedTemplate,
        setProgressMsg
      );
      setLastExport(result);
      setReportsReady(true);
      setProgressMsg("");
    } catch (err) {
      setError(mapReportError(err));
      setProgressMsg("");
    } finally {
      setExporting(false);
    }
  };

  const handleQuickExport = async (format, template) => {
    if (!evidenceId) return;
    if (!backendOnline) {
      setError("Backend Offline — reconnect via health check first.");
      return;
    }
    setSelectedFormat(format);
    setSelectedTemplate(template);
    setExporting(true);
    setError("");
    setProgressMsg(GENERATING_LABEL);
    try {
      if (!reportsReady) {
        await pollReportReady(evidenceId, { onProgress: setProgressMsg });
        setReportsReady(true);
        setReportStatus("completed");
      }
      const result = await downloadReport(evidenceId, format, template, setProgressMsg);
      setLastExport(result);
      setReportsReady(true);
      setReportStatus("completed");
      setProgressMsg("");
    } catch (err) {
      setError(mapReportError(err));
      setProgressMsg("");
    } finally {
      setExporting(false);
    }
  };

  const handlePreviewHtml = () => {
    if (!evidenceId || !backendOnline) return;
    window.open(getReportPreviewUrl(evidenceId, selectedTemplate), "_blank", "noopener");
  };

  if (!evidenceId) {
    return (
      <div className="rounded-2xl border border-[#1F2937] bg-[#111827]/60 p-5 text-center">
        <Download className="mx-auto h-7 w-7 text-slate-600" />
        <p className="mt-2 text-xs text-slate-500">Analyze evidence to enable export</p>
      </div>
    );
  }

  const formatList = formats?.formats || [];
  const templateList = formats?.templates || [];
  const disabled = exporting || !backendOnline;
  const generating = !reportsReady && (reportStatus === "processing" || reportStatus === "queued");

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-5 backdrop-blur-xl"
    >
      <div className="mb-4 flex items-center gap-2">
        <Download className="h-4 w-4 text-cyan-400" />
        <h3 className="text-sm font-semibold text-white">Export Report</h3>
      </div>

      <div className="mb-4 grid grid-cols-2 gap-2">
        {[
          { label: "Download PDF", format: "pdf", template: "full" },
          { label: "Download Court PDF", format: "pdf", template: "court" },
          { label: "Download Executive", format: "pdf", template: "executive" },
          { label: "Download JSON", format: "json", template: "full" },
          { label: "Download HTML", format: "html", template: "full" },
          { label: "Download DOCX", format: "docx", template: "full" },
        ].map((preset) => (
          <button
            key={preset.label}
            type="button"
            disabled={disabled || !reportsReady}
            onClick={() => handleQuickExport(preset.format, preset.template)}
            className="rounded-lg border border-[#1F2937] bg-[#0B1120]/80 px-3 py-2 text-xs font-medium text-slate-300 transition hover:border-cyan-500/40 hover:text-cyan-400 disabled:opacity-50"
          >
            {preset.label}
          </button>
        ))}
      </div>

      <p className="mb-2 text-xs font-medium text-slate-500">Format</p>
      <div className="mb-3 flex gap-2">
        {formatList.map((f) => {
          const Icon = FORMAT_ICONS[f.id] || FileText;
          return (
            <button
              key={f.id}
              type="button"
              onClick={() => setSelectedFormat(f.id)}
              className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg border px-2 py-2 text-xs transition ${
                selectedFormat === f.id
                  ? "border-cyan-500/50 bg-cyan-500/10 text-cyan-400"
                  : "border-[#1F2937] text-slate-400 hover:border-slate-600"
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              {f.id.toUpperCase()}
            </button>
          );
        })}
      </div>

      <p className="mb-2 text-xs font-medium text-slate-500">Report Type</p>
      <div className="mb-4 space-y-1">
        {templateList.map((t) => {
          const Icon = TEMPLATE_ICONS[t.id] || FileText;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => setSelectedTemplate(t.id)}
              className={`flex w-full items-center gap-2 rounded-lg border px-3 py-2 text-left text-xs transition ${
                selectedTemplate === t.id
                  ? "border-cyan-500/50 bg-cyan-500/10 text-cyan-300"
                  : "border-[#1F2937] text-slate-400 hover:border-slate-600"
              }`}
            >
              <Icon className="h-3.5 w-3.5 shrink-0" />
              <span className="font-medium">{t.label}</span>
            </button>
          );
        })}
      </div>

      {error && (
        <div className="mb-3 rounded-lg border border-red-500/20 bg-red-500/5 px-3 py-2">
          <p className="text-xs text-red-400">{error}</p>
          <button
            type="button"
            onClick={handleExport}
            className="mt-1 text-xs font-medium text-red-300 underline hover:text-red-200"
          >
            Retry
          </button>
        </div>
      )}

      {generating && (
        <div className="mb-3 flex items-start gap-2 rounded-lg border border-cyan-500/20 bg-cyan-500/5 px-3 py-2 text-xs text-cyan-300">
          <Loader2 className="mt-0.5 h-3.5 w-3.5 shrink-0 animate-spin" />
          <span>{progressMsg || GENERATING_LABEL}</span>
        </div>
      )}

      {reportsReady && (
        <div className="mb-3 flex items-center gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-3 py-2 text-xs text-emerald-400">
          <CheckCircle className="h-3.5 w-3.5" />
          Report ready — downloads enabled
        </div>
      )}

      {lastExport?.filename && (
        <div className="mb-3 flex items-center gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-3 py-2">
          <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />
          <span className="text-xs text-emerald-400">Exported: {lastExport.filename}</span>
        </div>
      )}

      {exporting && progressMsg && !generating && (
        <p className="mb-3 text-center text-xs text-cyan-300">{progressMsg}</p>
      )}

      <div className="flex gap-2">
        <button
          type="button"
          disabled={disabled}
          onClick={handleExport}
          className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 px-4 py-3 text-sm font-semibold text-white transition hover:from-cyan-500 hover:to-blue-500 disabled:opacity-50"
        >
          {exporting ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Download className="h-4 w-4" />
          )}
          {exporting ? "Generating…" : !backendOnline ? "Offline" : "Download Report"}
        </button>
        {selectedFormat === "html" && (
          <button
            type="button"
            disabled={disabled}
            onClick={handlePreviewHtml}
            className="rounded-xl border border-cyan-500/30 px-4 py-3 text-sm font-medium text-cyan-400 hover:bg-cyan-500/10 disabled:opacity-50"
          >
            Preview
          </button>
        )}
      </div>

      <p className="mt-3 text-center text-[10px] text-slate-600">
        Includes risk gauge, charts, timeline, heatmaps &amp; custody chain
      </p>
    </motion.div>
  );
}

export default ExportReportPanel;
