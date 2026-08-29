import { useState } from "react";
import {
  uploadEvidence,
  analyzeImage,
  analyzeDocument,
  investigateEvidence,
  ApplicationError,
  ConnectivityError,
  formatApiError,
} from "../services/api";
import { useBackend } from "../context/BackendConnectivity";

import UploadZone from "./ui/UploadZone";
import AnalysisLoader from "./ui/AnalysisLoader";

async function processFile(file, analysisType, onProgress, forceDeep, caseId) {
  const uploadResult = await uploadEvidence(file, caseId);
  const evidenceId = uploadResult.evidence_id;

  if (!evidenceId) {
    throw new ApplicationError("Backend did not return an evidence ID.", { status: 500 });
  }

  const fileType = uploadResult.file_type;

  if (analysisType === "investigate") {
    const response = await investigateEvidence(evidenceId, { onProgress, forceDeep });
    const inferredType =
      response.plan?.evidence_type ||
      (fileType === "pdf" ? "document" : fileType) ||
      "image";
    return {
      filename: file.name,
      evidenceId,
      fileType: inferredType === "document" ? "document" : inferredType,
      status: "completed",
      analysis: response.analysis ?? {},
      tampering: response.tampering ?? {},
      dashboard: response.dashboard ?? {},
      jury: response.jury ?? {},
      documentAnalysis: response.document_analysis ?? null,
      investigation: response,
      verdict: response.verdict,
      risk: response.risk || { score: response.risk_score, level: response.verdict },
      confidence: response.confidence,
      confidenceCalibration: response.confidence_calibration,
      explanation: response.explanation,
      correlation: response.correlation,
      agents: response.agents,
      timeline: response.timeline,
      artifacts: response.artifacts ?? {},
      reportsPending: response.reports_pending ?? true,
      reportStatus: "processing",
      hashes: uploadResult.hashes,
      intakeTimestamp: uploadResult.intake_timestamp,
      mode: "autonomous_investigation",
    };
  }

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
  caseId,
  ensureCaseId,
  showOfflineBanner = true,
}) {
  const { backendOnline } = useBackend();
  const isDocument = analysisType === "document";
  const isInvestigate = analysisType === "investigate";
  const [progressEvents, setProgressEvents] = useState([]);
  const [forceDeep, setForceDeep] = useState(false);

  const acceptedTypes = isDocument
    ? ".pdf,.doc,.docx"
    : isInvestigate
      ? ".jpg,.jpeg,.png,.webp,.pdf,.doc,.docx,.mp4,.mov,.avi,.mkv,.webm"
      : ".jpg,.jpeg,.png,.webp";

  const supportedText = isDocument
    ? "PDF · DOC · DOCX"
    : isInvestigate
      ? "PDF · JPG · PNG · MP4 · MOV"
      : "JPG · JPEG · PNG · WEBP";

  const handleFilesSelected = (selectedFiles) => {
    if (!backendOnline) {
      setError("The forensic service is offline. Reconnect before uploading evidence.");
      return;
    }
    setFiles(selectedFiles);
    setResults([]);
    setError("");
  };

  const handleAnalyze = async () => {
    if (!backendOnline) {
      setError("The forensic service is offline. Reconnect before starting analysis.");
      return;
    }
    if (!files || files.length === 0) {
      setError(
        isDocument
          ? "Please select at least one document."
          : "Please select at least one evidence file."
      );
      return;
    }

    setProcessing(true);
    setError("");
    setResults([]);
    setProgressEvents([]);

    try {
      const resolvedCaseId =
        caseId || (ensureCaseId ? await ensureCaseId(files[0]) : null);
      if (!resolvedCaseId) {
        throw new ApplicationError(
          "An investigation record could not be created for this evidence.",
          { status: 500 }
        );
      }

      const results = await Promise.allSettled(
        files.map((file) =>
          processFile(file, analysisType, (event) => {
            setProgressEvents((prev) => [...prev, event]);
          }, forceDeep, resolvedCaseId)
        )
      );

      const analysisResults = results.map((result, i) => {
        if (result.status === "fulfilled") {
          return { ...result.value, caseId: resolvedCaseId };
        }
        const reason = result.reason;
        const message =
          reason instanceof ApplicationError
            ? reason.message
            : reason instanceof ConnectivityError
              ? "The forensic service could not be reached. Please retry."
              : formatApiError(reason, "Analysis could not be completed");
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
        setError(analysisResults[0]?.error || "Analysis could not be completed for the selected files.");
      }
    } catch (err) {
      console.error("Evidence analysis error:", err);
      setError(formatApiError(err, "Analysis could not be completed."));
    } finally {
      setProcessing(false);
    }
  };

  const disabled = processing || !backendOnline;

  return (
    <>
      {!backendOnline && showOfflineBanner && (
        <div className="forge-inline-error">
          The forensic service is offline. Uploads are paused until the connection is restored.
        </div>
      )}

      <UploadZone
        accept={acceptedTypes}
        multiple
        supportedText={supportedText}
        title={
          isInvestigate
            ? "Drop files here"
            : isDocument
              ? "Drop a document here"
              : "Drop an image here"
        }
        files={files}
        onFilesSelected={handleFilesSelected}
        disabled={disabled}
        processing={processing}
      />

      {files.length > 0 && !isDocument && (
        <label className="forge-check">
          <input
            type="checkbox"
            checked={forceDeep}
            onChange={(e) => setForceDeep(e.target.checked)}
            disabled={disabled}
          />
          {isInvestigate
            ? "Include additional examination modules when available"
            : "Include additional image examination modules when available"}
        </label>
      )}

      {files.length > 0 && (
        <button
          onClick={handleAnalyze}
          disabled={disabled}
          className="forge-primary-action mt-4"
        >
          {processing
            ? "Analyzing"
            : !backendOnline
              ? "Service offline"
              : "Begin forensic examination"}
        </button>
      )}

      <AnalysisLoader
        active={processing}
        analysisType={isInvestigate ? "image" : analysisType}
        fileCount={files.length}
        progressEvents={progressEvents}
      />

      {error && (
        <div className="forge-inline-error mt-4" role="alert">
          {/please select|offline/i.test(error) ? (
            <span>{error}</span>
          ) : (
            <>
              <div>
                <strong>Analysis could not be completed</strong>
                <p>The evidence could not be processed at this time. Please try again.</p>
                <p>{error}</p>
              </div>
              {files.length > 0 && (
                <button type="button" onClick={handleAnalyze} disabled={disabled}>
                  Retry analysis
                </button>
              )}
            </>
          )}
        </div>
      )}
    </>
  );
}

export default EvidenceUploader;
