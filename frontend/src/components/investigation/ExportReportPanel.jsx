import { useEffect, useState } from "react";
import {
  CheckCircle2,
  ClipboardList,
  Download,
  FileCode2,
  FileText,
  Loader2,
} from "lucide-react";

import {
  downloadReport,
  formatApiError,
  generateReport,
  getReportStatus,
  pollReportReadyLight,
} from "../../services/api";
import { useBackend } from "../../context/BackendConnectivity";

const REPORT_OPTIONS = [
  {
    id: "executive",
    format: "pdf",
    template: "executive",
    title: "Executive report",
    description: "Concise finding and verdict summary",
    icon: FileText,
  },
  {
    id: "court",
    format: "pdf",
    template: "court",
    title: "Court report",
    description: "Four-page examiner-style evidence report",
    icon: ClipboardList,
  },
  {
    id: "technical",
    format: "pdf",
    template: "technical",
    title: "Technical report",
    description: "Methods, integrity records, and custody details",
    icon: FileCode2,
  },
  {
    id: "pdf",
    format: "pdf",
    template: "full",
    title: "Download PDF",
    description: "Complete forensic examination report",
    icon: Download,
  },
  {
    id: "docx",
    format: "docx",
    template: "full",
    title: "Download DOCX",
    description: "Editable examination report document",
    icon: FileText,
  },
];

function ExportReportPanel({
  evidenceId,
  reportsPending: initialReportsPending = false,
}) {
  const { backendOnline } = useBackend();
  const [ready, setReady] = useState(!initialReportsPending);
  const [preparing, setPreparing] = useState(initialReportsPending);
  const [downloading, setDownloading] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!evidenceId || !backendOnline) return undefined;
    let cancelled = false;

    async function prepare() {
      setPreparing(true);
      setError("");
      try {
        let status = await getReportStatus(evidenceId);
        if (cancelled) return;
        let isReady = Boolean(
          status?.report_ready ||
            status?.ready ||
            status?.status === "completed"
        );
        if (!isReady && status?.status !== "failed") {
          await generateReport(evidenceId);
          status = await getReportStatus(evidenceId);
          isReady = Boolean(
            status?.report_ready ||
              status?.ready ||
              status?.status === "completed"
          );
        }
        setReady(isReady);
        if (!isReady && status?.status !== "failed") {
          await pollReportReadyLight(evidenceId, {
            onProgress: (value) => !cancelled && setMessage(value),
          });
          if (!cancelled) setReady(true);
        }
      } catch (requestError) {
        if (!cancelled) {
          setError(formatApiError(requestError, "Report preparation is unavailable."));
        }
      } finally {
        if (!cancelled) {
          setPreparing(false);
          setMessage("");
        }
      }
    }

    prepare();
    return () => {
      cancelled = true;
    };
  }, [evidenceId, backendOnline]);

  async function handleDownload(option) {
    if (!evidenceId || !backendOnline) return;
    setDownloading(option.id);
    setError("");
    try {
      if (!ready) {
        setMessage("Preparing investigation report…");
        await pollReportReadyLight(evidenceId, { onProgress: setMessage });
        setReady(true);
      }
      await downloadReport(
        evidenceId,
        option.format,
        option.template,
        setMessage
      );
    } catch (requestError) {
      setError(formatApiError(requestError, "The report could not be downloaded."));
    } finally {
      setDownloading("");
      setMessage("");
    }
  }

  if (!evidenceId) {
    return (
      <div className="forge-empty-result">
        <Download className="h-5 w-5" />
        <div>
          <strong>Reports are not available</strong>
          <p>Complete an evidence examination to enable report downloads.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="forge-report-panel">
      <div className="forge-report-status">
        {preparing ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <CheckCircle2 className="h-4 w-4" />
        )}
        <div>
          <strong>{preparing ? "Preparing reports" : "Reports ready"}</strong>
          <span>
            {message ||
              (ready
                ? "Generated from the completed investigation record"
                : "Report generation is queued")}
          </span>
        </div>
      </div>

      {error && <div className="forge-inline-notice forge-inline-notice-warning">{error}</div>}

      <div className="forge-report-options">
        {REPORT_OPTIONS.map((option) => {
          const Icon = option.icon;
          const active = downloading === option.id;
          return (
            <button
              type="button"
              key={option.id}
              disabled={!backendOnline || preparing || Boolean(downloading)}
              onClick={() => handleDownload(option)}
            >
              <Icon className="h-5 w-5" />
              <span>
                <strong>{option.title}</strong>
                <small>{option.description}</small>
              </span>
              {active ? (
                <Loader2 className="ml-auto h-4 w-4 animate-spin" />
              ) : (
                <Download className="ml-auto h-4 w-4" />
              )}
            </button>
          );
        })}
      </div>

      {!backendOnline && (
        <p className="forge-report-offline">
          Reconnect to the forensic service to download reports.
        </p>
      )}
    </div>
  );
}

export default ExportReportPanel;
