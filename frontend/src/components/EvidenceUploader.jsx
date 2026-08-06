import { useState } from "react";
import {
  uploadEvidence,
  analyzeImage,
  analyzeDocument,
  ApplicationError,
  ConnectivityError,
  formatApiError,
} from "../services/api";
import { useBackend } from "../context/BackendConnectivity";

import UploadZone from "./ui/UploadZone";
import AnalysisLoader from "./ui/AnalysisLoader";

async function processFile(file, analysisType, onProgress, forceDeep) {
  const uploadResult = await uploadEvidence(file);
  const evidenceId = uploadResult.evidence_id;

  if (!evidenceId) {
    throw new ApplicationError("Backend did not return an evidence ID.", { status: 500 });
  }

  const fileType = uploadResult.file_type;

  if (analysisType === "image") {
    if (fileType !== "image") {
      throw new ApplicationError("Please upload a valid image file for Image Forensics.", {
        status: 400,
      });
    }
    const response = await analyzeImage(evidenceId, { onProgress, forceDeep });
    return {
      filename: file.name,
      evidenceId,
      fileType: "image",
      status: "completed",
      analysis: response.analysis ?? {},
      tampering: response.tampering ?? {},
      dashboard: response.dashboard ?? {},
      jury: response.jury ?? {},
      report: response.report ?? {},
      artifacts: response.artifacts ?? {},
      risk: response.risk,
      confidence: response.confidence,
      processingTime: response.processing_time,
      reportsPending: response.reports_pending ?? true,
      reportStatus: response.report_status ?? "processing",
      timing: response.timing,
      cached: response.cached,
      artifactsPending: false,
      scanMode: response.scan_mode,
      warnings: response.warnings ?? [],
      hashes: uploadResult.hashes,
      intakeTimestamp: uploadResult.intake_timestamp,
    };
  }

  if (analysisType === "document") {
    if (fileType !== "document" && fileType !== "pdf") {
      throw new ApplicationError(
        "Please upload a PDF, DOC, or DOCX file for Document Forensics.",
        { status: 400 }
      );
    }
    const documentResult = await analyzeDocument(evidenceId, { onProgress });
    return {
      filename: file.name,
      evidenceId,
      fileType: "document",
      status: "completed",
      documentAnalysis: documentResult.analysis ?? documentResult,
      timing: documentResult.timing,
      cached: documentResult.cached,
      hashes: uploadResult.hashes,
      intakeTimestamp: uploadResult.intake_timestamp,
      reportsPending: true,
    };
  }

  throw new ApplicationError("Unknown analysis type.", { status: 400 });
}

function EvidenceUploader({
  analysisType,
  files,
  setFiles,
  processing,
  setProcessing,
  setResults,
  error,
  setError,
}) {
  const { backendOnline } = useBackend();
  const isDocument = analysisType === "document";
  const [progressEvents, setProgressEvents] = useState([]);
  const [forceDeep, setForceDeep] = useState(false);

  const acceptedTypes = isDocument
    ? ".pdf,.doc,.docx"
    : ".jpg,.jpeg,.png,.webp";

  const supportedText = isDocument
    ? "Supported: PDF, DOCX (DOC: convert to PDF first)"
    : "Supported: JPG, JPEG, PNG, WEBP";

  const handleFilesSelected = (selectedFiles) => {
    if (!backendOnline) {
      setError("Backend Offline — health check failed. Reconnect first.");
      return;
    }
    setFiles(selectedFiles);
    setResults([]);
    setError("");
  };

  const handleAnalyze = async () => {
    if (!backendOnline) {
      setError("Backend Offline — health check failed. Reconnect first.");
      return;
    }
    if (!files || files.length === 0) {
      setError(
        isDocument
          ? "Please select at least one document."
          : "Please select at least one image."
      );
      return;
    }

    setProcessing(true);
    setError("");
    setResults([]);
    setProgressEvents([]);

    try {
      const results = await Promise.allSettled(
        files.map((file) =>
          processFile(file, analysisType, (event) => {
            setProgressEvents((prev) => [...prev, event]);
          }, forceDeep)
        )
      );

      const analysisResults = results.map((result, i) => {
        if (result.status === "fulfilled") {
          return result.value;
        }
        const reason = result.reason;
        let message = "Analysis failed";
        if (reason instanceof ApplicationError) {
          message = reason.message;
        } else if (reason instanceof ConnectivityError) {
          message = "Connectivity Error — retry. Backend Online status is unchanged.";
        } else {
          message = formatApiError(reason, "Analysis failed");
        }
        return {
          filename: files[i].name,
          evidenceId: null,
          fileType: isDocument ? "document" : "image",
          status: "failed",
          error: message,
          analysis: {},
          tampering: {},
        };
      });

      setResults(analysisResults);

      if (analysisResults.every((r) => r.status === "failed")) {
        setError(analysisResults[0]?.error || "Analysis failed for all selected files.");
      }
    } catch (err) {
      console.error("Evidence analysis error:", err);
      setError(formatApiError(err, "Evidence analysis failed."));
    } finally {
      setProcessing(false);
    }
  };

  const disabled = processing || !backendOnline;

  return (
    <>
      {!backendOnline && (
        <div className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          Backend Offline — health check failed. Uploads are paused until reconnect.
        </div>
      )}

      <UploadZone
        accept={acceptedTypes}
        multiple
        supportedText={supportedText}
        title={
          isDocument ? "Upload Document Evidence" : "Upload Image Evidence"
        }
        files={files}
        onFilesSelected={handleFilesSelected}
        disabled={disabled}
        processing={processing}
      />

      {files.length > 0 && !isDocument && (
        <label className="mt-4 flex items-center gap-2 text-sm text-slate-400">
          <input
            type="checkbox"
            checked={forceDeep}
            onChange={(e) => setForceDeep(e.target.checked)}
            disabled={disabled}
            className="rounded border-slate-600 bg-slate-800"
          />
          Force deep scan (run all forensic modules even if quick scan passes)
        </label>
      )}

      {files.length > 0 && (
        <button
          onClick={handleAnalyze}
          disabled={disabled}
          className="mt-6 w-full rounded-xl bg-gradient-to-r from-emerald-600 to-cyan-600 px-8 py-3.5 font-semibold text-white shadow-lg shadow-emerald-500/20 transition hover:from-emerald-500 hover:to-cyan-500 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
        >
          {processing
            ? "Analyzing..."
            : !backendOnline
              ? "Backend Offline"
              : isDocument
                ? "Analyze Document"
                : "Analyze Images"}
        </button>
      )}

      <AnalysisLoader
        active={processing}
        analysisType={analysisType}
        fileCount={files.length}
        progressEvents={progressEvents}
      />

      {error && (
        <div className="mt-6 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-red-400 text-sm">
          {error}
        </div>
      )}
    </>
  );
}

export default EvidenceUploader;
