/**
 * AI-FORGE API client — single source of truth for backend HTTP.
 * Base: http://127.0.0.1:8000/api
 *
 * Error model (never mix):
 *   ConnectivityError  — network unreachable / timeout (health only drives Online/Offline)
 *   ApplicationError   — HTTP 4xx/5xx from a reachable backend
 */
import { API_BASE_URL, API_ORIGIN, apiUrl, originUrl } from "../config/api";

export { API_BASE_URL, API_ORIGIN, apiUrl, originUrl };

/** True network/connectivity failure — does NOT control BackendStatus. */
export class ConnectivityError extends Error {
  constructor(message = "Connectivity Error") {
    super(message);
    this.name = "ConnectivityError";
    this.code = "CONNECTIVITY_ERROR";
    this.kind = "connectivity";
  }
}

/** Backend responded with an application-level failure (404, 500, etc.). */
export class ApplicationError extends Error {
  constructor(message, { status = 0, endpoint = "" } = {}) {
    super(message);
    this.name = "ApplicationError";
    this.code = "APPLICATION_ERROR";
    this.kind = "application";
    this.status = status;
    this.endpoint = endpoint;
  }
}

/** @deprecated Use ConnectivityError — kept so older imports keep working */
export class BackendOfflineError extends ConnectivityError {
  constructor(message = "Connectivity Error") {
    super(message);
    this.name = "BackendOfflineError";
    this.code = "BACKEND_OFFLINE";
  }
}

async function getApiError(response, defaultMessage) {
  try {
    const errorData = await response.json();
    if (errorData.reason) return String(errorData.reason);
    if (errorData.error) {
      const parts = [errorData.error];
      if (errorData.details && errorData.details !== errorData.error) {
        parts.push(errorData.details);
      }
      if (errorData.module) {
        parts.push(`(module: ${errorData.module})`);
      }
      return parts.join(" — ");
    }
    return errorData.detail || errorData.message || defaultMessage;
  } catch {
    return defaultMessage;
  }
}

function isConnectivityFailure(error) {
  if (error instanceof ConnectivityError) return true;
  if (error?.name === "AbortError") return true;
  const msg = String(error?.message || error || "");
  return (
    error?.name === "TypeError" ||
    msg.includes("Failed to fetch") ||
    msg.includes("NetworkError") ||
    msg.includes("ERR_CONNECTION_REFUSED") ||
    msg.includes("Load failed") ||
    msg.includes("Network request failed")
  );
}

function toConnectivityError(error) {
  if (error instanceof ConnectivityError) return error;
  return new ConnectivityError(
    error?.name === "AbortError" ? "Request timed out" : "Connectivity Error"
  );
}

function toApplicationError(response, defaultMessage, endpoint = "") {
  return getApiError(response, defaultMessage).then(
    (msg) =>
      new ApplicationError(msg, {
        status: response.status,
        endpoint,
      })
  );
}

/**
 * Central fetch — returns Response when reachable.
 * Throws ConnectivityError only when the browser cannot reach the host.
 * HTTP 404/500 are NOT connectivity errors — callers must handle them.
 */
export async function apiFetch(path, options = {}) {
  const url = path.startsWith("http") ? path : apiUrl(path);
  try {
    return await fetch(url, {
      ...options,
      headers: {
        Accept: "application/json",
        ...(options.headers || {}),
      },
    });
  } catch (error) {
    throw toConnectivityError(error);
  }
}

export function isBackendHealthy(health) {
  if (!health || typeof health !== "object") return false;
  const status = String(health.status || "").toLowerCase();
  return status === "healthy" || status === "ok";
}

const HEALTH_TIMEOUT_MS = 8000;

/**
 * Health check ONLY — sole authority for Online / Offline.
 * Never used for report/upload/analysis error classification.
 */
export async function checkBackendHealth() {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), HEALTH_TIMEOUT_MS);
  try {
    const response = await fetch(apiUrl("health"), {
      method: "GET",
      headers: { Accept: "application/json" },
      signal: controller.signal,
      cache: "no-store",
    });

    if (!response.ok) {
      console.log("[Health Check]", "OFFLINE", `(HTTP ${response.status})`);
      throw new ConnectivityError(`Health check HTTP ${response.status}`);
    }

    const data = await response.json();
    if (!isBackendHealthy(data)) {
      console.log("[Health Check]", "OFFLINE", "(unhealthy payload)");
      throw new ConnectivityError("Health check returned unhealthy status");
    }

    console.log("[Health Check]", "ONLINE");
    return data;
  } catch (error) {
    if (!(error instanceof ConnectivityError)) {
      console.log("[Health Check]", "OFFLINE", error?.message || error);
    }
    throw toConnectivityError(error);
  } finally {
    clearTimeout(timer);
  }
}

export function getApiBaseUrl() {
  return API_ORIGIN;
}

export function formatApiError(error, fallback = "Request failed") {
  if (error instanceof ApplicationError) return error.message;
  if (error instanceof ConnectivityError) return error.message;
  return error?.message || fallback;
}

/* ========================================= */
/* Evidence                                    */
/* ========================================= */

export async function uploadEvidence(file) {
  const formData = new FormData();
  formData.append("file", file);
  let response;
  try {
    response = await apiFetch("evidence/upload", {
      method: "POST",
      body: formData,
      headers: {},
    });
  } catch (error) {
    throw toConnectivityError(error);
  }
  if (!response.ok) {
    throw await toApplicationError(response, "Evidence upload failed", "evidence/upload");
  }
  const data = await response.json();
  notifyEvidenceChanged(data.evidence_id);
  return data;
}

export async function listRecentEvidence(limit = 50) {
  const response = await apiFetch(`evidence/recent?limit=${limit}`);
  if (!response.ok) {
    if (response.status === 404) return { success: true, evidence: [] };
    throw new Error(await getApiError(response, "Failed to list evidence"));
  }
  return response.json();
}

export function notifyEvidenceChanged(evidenceId) {
  try {
    const payload = JSON.stringify({
      evidenceId: evidenceId || null,
      at: Date.now(),
    });
    localStorage.setItem("ai-forge-evidence-sync", payload);
    if (typeof BroadcastChannel !== "undefined") {
      const channel = new BroadcastChannel("ai-forge-evidence");
      channel.postMessage({ type: "evidence-changed", evidenceId });
      channel.close();
    }
    window.dispatchEvent(
      new CustomEvent("ai-forge-evidence-changed", { detail: { evidenceId } })
    );
  } catch {
    /* ignore storage errors */
  }
}

export function subscribeAnalysisProgress(jobId, onEvent, onError) {
  const url = apiUrl(`progress/stream/${jobId}`);
  const source = new EventSource(url);

  source.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onEvent(data);
      if (
        data.module === "pipeline" &&
        (data.status === "completed" || data.status === "failed")
      ) {
        source.close();
      }
    } catch (err) {
      console.warn("Progress parse error:", err);
    }
  };

  source.onerror = (err) => {
    source.close();
    if (onError) onError(err);
  };

  return () => source.close();
}

export async function analyzeImage(evidenceId, { onProgress, forceDeep = false } = {}) {
  let unsubscribe = null;
  if (onProgress) {
    unsubscribe = subscribeAnalysisProgress(evidenceId, onProgress);
  }
  try {
    const path = `evidence/analyze/${evidenceId}${forceDeep ? "?force_deep=true" : ""}`;
    const response = await apiFetch(path, { method: "POST" });
    if (!response.ok) {
      throw new Error(await getApiError(response, "Image analysis failed"));
    }
    const data = await response.json();
    notifyEvidenceChanged(evidenceId);
    // Auto-start report if backend did not already
    if (data.reports_pending !== false) {
      generateReport(evidenceId).catch(() => {});
    }
    return data;
  } finally {
    if (unsubscribe) unsubscribe();
  }
}

export async function analyzeEvidence(evidenceId) {
  if (!evidenceId) throw new Error("Evidence ID is required");
  const response = await apiFetch(`evidence/analyze/${evidenceId}`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(await getApiError(response, "Evidence analysis failed"));
  }
  const data = await response.json();
  notifyEvidenceChanged(evidenceId);
  generateReport(evidenceId).catch(() => {});
  return data;
}

export function getArtifactUrl(artifactPath) {
  if (!artifactPath) return "";
  if (artifactPath.startsWith("http://") || artifactPath.startsWith("https://")) {
    return artifactPath;
  }
  if (artifactPath.startsWith("/api/")) {
    return `${API_ORIGIN}${artifactPath}`;
  }
  return originUrl(artifactPath.replaceAll("\\", "/"));
}

export async function verifySignature(referenceFile, queryFile) {
  const formData = new FormData();
  formData.append("reference", referenceFile);
  formData.append("query", queryFile);
  const response = await apiFetch("evidence/verify-signature", {
    method: "POST",
    body: formData,
    headers: {},
  });
  if (!response.ok) {
    throw new Error(await getApiError(response, "Signature verification failed"));
  }
  const data = await response.json();
  if (data.evidence_id) {
    notifyEvidenceChanged(data.evidence_id);
    generateReport(data.evidence_id).catch(() => {});
  }
  return data;
}

export async function analyzeCopyMove(evidenceId) {
  if (!evidenceId) throw new Error("Evidence ID is required");
  const response = await apiFetch(`evidence/analyze-copy-move/${evidenceId}`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(await getApiError(response, "Copy-Move analysis failed"));
  }
  const data = await response.json();
  notifyEvidenceChanged(evidenceId);
  generateReport(evidenceId).catch(() => {});
  return data;
}

export function getCopyMoveArtifactUrl(evidenceId) {
  if (!evidenceId) return "";
  return apiUrl(`evidence/artifacts/${evidenceId}/copy_move`);
}

export function getUnifiedArtifactUrl(evidenceId, artifactType) {
  if (!evidenceId || !artifactType) return "";
  return apiUrl(`evidence/artifacts/${evidenceId}/${artifactType}`);
}

export async function analyzeDocument(evidenceId, { onProgress } = {}) {
  let unsubscribe = null;
  if (onProgress) {
    unsubscribe = subscribeAnalysisProgress(evidenceId, onProgress);
  }
  try {
    const response = await apiFetch(`evidence/analyze-document/${evidenceId}`, {
      method: "POST",
    });
    if (!response.ok) {
      throw new Error(await getApiError(response, "Document analysis failed"));
    }
    const data = await response.json();
    notifyEvidenceChanged(evidenceId);
    generateReport(evidenceId).catch(() => {});
    return data;
  } finally {
    if (unsubscribe) unsubscribe();
  }
}

export async function analyzeVideo(videoFile, { onProgress } = {}) {
  if (!videoFile) throw new Error("Video file is required.");

  const jobId =
    typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : `vid-${Date.now()}`;

  let unsubscribe = null;
  if (onProgress) {
    unsubscribe = subscribeAnalysisProgress(jobId, onProgress);
  }

  try {
    const formData = new FormData();
    formData.append("file", videoFile);
    const response = await apiFetch(
      `video/analyze?job_id=${encodeURIComponent(jobId)}`,
      { method: "POST", body: formData, headers: {} }
    );
    if (!response.ok) {
      throw new Error(await getApiError(response, "Video analysis failed."));
    }
    const data = await response.json();
    const evidenceId = data.video_id || data.evidence_id || jobId;
    notifyEvidenceChanged(evidenceId);
    generateReport(evidenceId).catch(() => {});
    return data;
  } finally {
    if (unsubscribe) unsubscribe();
  }
}

export async function runJuryAnalysis({
  evidenceId,
  filename,
  analysis,
  tampering,
  documentAnalysis,
  videoAnalysis,
  signatureResult,
}) {
  if (!analysis && !tampering && !documentAnalysis && !videoAnalysis && !signatureResult) {
    throw new Error("Forensic analysis data is required for jury synthesis.");
  }

  const response = await apiFetch("jury/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      evidence_id: evidenceId || null,
      filename: filename || null,
      analysis: analysis || {},
      tampering: tampering || {},
      document_analysis: documentAnalysis || null,
      video_analysis: videoAnalysis || null,
      signature_result: signatureResult || null,
    }),
  });

  if (!response.ok) {
    throw new Error(await getApiError(response, "AI Jury analysis failed"));
  }
  const data = await response.json();
  if (evidenceId) {
    notifyEvidenceChanged(evidenceId);
    generateReport(evidenceId).catch(() => {});
  }
  return data;
}

export async function analyzeTampering(evidenceId) {
  if (!evidenceId) throw new Error("Evidence ID is required");
  const response = await apiFetch(`evidence/analyze/${evidenceId}`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(await getApiError(response, "Tampering analysis failed"));
  }
  const data = await response.json();
  return data.tampering ?? data;
}

export async function generateAttentionHeatmap(evidenceId) {
  if (!evidenceId) throw new Error("Evidence ID is required");
  const response = await apiFetch(`forensics/heatmap/${evidenceId}`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(await getApiError(response, "Heatmap generation failed"));
  }
  const data = await response.json();
  if (evidenceId) generateReport(evidenceId).catch(() => {});
  return data;
}

export function getHeatmapArtifactUrl(evidenceId, artifactType) {
  if (!evidenceId || !artifactType) return "";
  return apiUrl(`forensics/heatmap/${evidenceId}/artifact/${artifactType}`);
}

export async function analyzeDeepfakeImage(evidenceId) {
  if (!evidenceId) throw new Error("Evidence ID is required");
  const response = await apiFetch(`forensics/deepfake/image/${evidenceId}`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(await getApiError(response, "Deepfake analysis failed"));
  }
  const data = await response.json();
  notifyEvidenceChanged(evidenceId);
  generateReport(evidenceId).catch(() => {});
  return data;
}

export async function analyzeDeepfakeImageUpload(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await apiFetch("forensics/deepfake/image", {
    method: "POST",
    body: formData,
    headers: {},
  });
  if (!response.ok) {
    throw new Error(await getApiError(response, "Deepfake analysis failed"));
  }
  const data = await response.json();
  if (data.evidence_id || data.image_id) {
    const id = data.evidence_id || data.image_id;
    notifyEvidenceChanged(id);
    generateReport(id).catch(() => {});
  }
  return data;
}

export async function getArtifactsStatus(evidenceId) {
  try {
    const response = await apiFetch(`evidence/artifacts-status/${evidenceId}`);
    if (!response.ok) return { status: "unknown" };
    return response.json();
  } catch {
    return { status: "unknown" };
  }
}

export async function getStoredReport(evidenceId) {
  const response = await apiFetch(`evidence/report/${evidenceId}`);
  if (!response.ok) throw new Error("Report not found");
  return response.json();
}

export async function analyzeDeepfakeVideo(videoFile) {
  const formData = new FormData();
  formData.append("file", videoFile);
  const response = await apiFetch("forensics/deepfake/video", {
    method: "POST",
    body: formData,
    headers: {},
  });
  if (!response.ok) {
    throw new Error(await getApiError(response, "Video deepfake analysis failed"));
  }
  const data = await response.json();
  const id = data.evidence_id || data.video_id;
  if (id) {
    notifyEvidenceChanged(id);
    generateReport(id).catch(() => {});
  }
  return data;
}

/* ========================================= */
/* Forensic Integrity                          */
/* ========================================= */

export async function getEvidenceHashes(evidenceId) {
  const response = await apiFetch(`forensics/evidence/${evidenceId}/hashes`);
  if (!response.ok) throw new Error(await getApiError(response, "Hashes not found"));
  return response.json();
}

export async function getChainOfCustody(evidenceId) {
  const response = await apiFetch(`forensics/evidence/${evidenceId}/custody`);
  if (!response.ok) {
    throw new Error(await getApiError(response, "Custody record not found"));
  }
  return response.json();
}

export async function verifyChainOfCustody(evidenceId) {
  const response = await apiFetch(`forensics/evidence/${evidenceId}/custody/verify`);
  if (!response.ok) throw new Error(await getApiError(response, "Verification failed"));
  return response.json();
}

export async function getEvidenceAuditLog(evidenceId, limit = 100) {
  const response = await apiFetch(
    `forensics/evidence/${evidenceId}/audit?limit=${limit}`
  );
  if (!response.ok) throw new Error(await getApiError(response, "Audit log not found"));
  return response.json();
}

export async function getSealedReports(evidenceId) {
  const response = await apiFetch(`forensics/evidence/${evidenceId}/reports`);
  if (!response.ok) throw new Error(await getApiError(response, "Reports not found"));
  return response.json();
}

export async function verifySealedReport(snapshotId) {
  const response = await apiFetch(`forensics/reports/${snapshotId}/verify`);
  if (!response.ok) {
    throw new Error(await getApiError(response, "Report verification failed"));
  }
  return response.json();
}

export async function getReproducibilityManifest(evidenceId) {
  const response = await apiFetch(`forensics/evidence/${evidenceId}/reproducibility`);
  if (!response.ok) throw new Error(await getApiError(response, "Manifest not found"));
  return response.json();
}

export async function createInvestigation(title, description = "") {
  const params = new URLSearchParams({ title });
  if (description) params.set("description", description);
  const response = await apiFetch(`forensics/investigations?${params}`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(await getApiError(response, "Failed to create investigation"));
  }
  return response.json();
}

export async function listInvestigations(limit = 50) {
  const response = await apiFetch(`forensics/investigations?limit=${limit}`);
  if (!response.ok) {
    throw new Error(await getApiError(response, "Failed to list investigations"));
  }
  return response.json();
}

/* ========================================= */
/* Pipeline — Dashboard & Report Status        */
/* ========================================= */

const TERMINAL_REPORT_STATUSES = new Set(["completed", "failed", "ready"]);
const GENERATING_MSG =
  "Generating professional forensic report… Estimated time: 3–5 seconds";

function normalizeReportStatus(data = {}) {
  let status = String(data.status || "queued").toLowerCase();
  if (status === "generating") status = "processing";
  if (status === "ready") status = "completed";
  if (status === "pending") status = "queued";
  const ready =
    status === "completed" ||
    Boolean(data.report_ready) ||
    Boolean(data.ready);
  return {
    ...data,
    status: ready && status !== "failed" ? "completed" : status,
    ready,
    report_ready: ready,
    message: data.message || (ready ? "Report ready." : GENERATING_MSG),
  };
}

export async function getDashboard(evidenceId) {
  const response = await apiFetch(`dashboard/${evidenceId}`);
  if (!response.ok) throw new Error(await getApiError(response, "Dashboard not found"));
  return response.json();
}

/** GET /api/report/{id} — may sync-generate from cached analysis. */
export async function getReport(evidenceId) {
  try {
    const response = await apiFetch(`report/${evidenceId}`);
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      return normalizeReportStatus({
        status: body.status || "failed",
        reason: body.reason || body.detail,
        report_ready: false,
        ready: false,
      });
    }
    return normalizeReportStatus(await response.json());
  } catch (error) {
    if (error instanceof ConnectivityError) {
      return {
        ready: false,
        report_ready: false,
        status: "queued",
        message: GENERATING_MSG,
      };
    }
    return {
      ready: false,
      report_ready: false,
      status: "failed",
      reason: error?.message || "Report request failed",
    };
  }
}

export async function getReportStatus(evidenceId) {
  try {
    const response = await apiFetch(`report/${evidenceId}/status`);
    if (!response.ok) {
      console.log("[Report Status]", response.status);
      return {
        ready: false,
        report_ready: false,
        status: "queued",
        message: GENERATING_MSG,
      };
    }
    return normalizeReportStatus(await response.json());
  } catch (error) {
    if (error instanceof ConnectivityError) {
      console.log("[Report Status]", "Connectivity Error (ignored for Online status)");
      return {
        ready: false,
        report_ready: false,
        status: "queued",
        message: GENERATING_MSG,
      };
    }
    return {
      ready: false,
      report_ready: false,
      status: "queued",
      message: GENERATING_MSG,
    };
  }
}

export async function generateReport(evidenceId) {
  if (!evidenceId) return { success: false };
  try {
    const response = await apiFetch(`report/${evidenceId}/generate`, {
      method: "POST",
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      return normalizeReportStatus({
        success: false,
        status: body.status || "failed",
        reason: body.reason,
      });
    }
    return normalizeReportStatus(await response.json());
  } catch {
    return { success: false, status: "queued", message: GENERATING_MSG };
  }
}

/**
 * Bounded wait for report readiness — never endless.
 * Prefers GET /api/report/{id} once (sync generate) after short status polls.
 */
export async function pollReportReady(
  evidenceId,
  { intervalMs = 750, maxAttempts = 8, onProgress, signal } = {}
) {
  onProgress?.(GENERATING_MSG);
  await generateReport(evidenceId);

  let attempts = 0;
  while (attempts < maxAttempts) {
    if (signal?.aborted) {
      throw new Error("Polling cancelled");
    }
    attempts += 1;
    onProgress?.(GENERATING_MSG);

    const status = await getReportStatus(evidenceId);
    if (status.ready || status.status === "completed") {
      return status;
    }
    if (status.status === "failed") {
      // One sync attempt via GET /api/report/{id}
      const synced = await getReport(evidenceId);
      if (synced.ready || synced.status === "completed") return synced;
      throw new ApplicationError(
        synced.reason || status.reason || "Report generation failed.",
        { status: 500, endpoint: `report/${evidenceId}` }
      );
    }

    await new Promise((r) => setTimeout(r, intervalMs));
  }

  // Final sync generate — uses cached analysis only
  onProgress?.(GENERATING_MSG);
  const final = await getReport(evidenceId);
  if (final.ready || final.status === "completed") return final;
  if (final.status === "failed") {
    throw new ApplicationError(final.reason || "Report generation failed.", {
      status: 500,
      endpoint: `report/${evidenceId}`,
    });
  }
  throw new ApplicationError("Report generation timed out. Please retry download.", {
    status: 408,
    endpoint: `report/${evidenceId}`,
  });
}

export async function getTimeline(evidenceId) {
  const response = await apiFetch(`timeline/${evidenceId}`);
  if (!response.ok) throw new Error(await getApiError(response, "Timeline not found"));
  return response.json();
}

/* ========================================= */
/* Report Export                               */
/* ========================================= */

export async function getReportFormats() {
  const response = await apiFetch("reports/formats");
  if (!response.ok) throw new Error("Failed to load report formats");
  return response.json();
}

const REPORT_DOWNLOAD_TIMEOUT_MS = 180000;

function parseFilenameFromDisposition(disposition, fallback) {
  if (!disposition) return fallback;
  const match = disposition.match(/filename\*?=(?:UTF-8''|")?([^";]+)/i);
  return match ? decodeURIComponent(match[1].replace(/"/g, "")) : fallback;
}

export async function downloadReport(
  evidenceId,
  format = "pdf",
  template = "full",
  onProgress
) {
  if (!evidenceId) throw new ApplicationError("Evidence ID required", { status: 400 });

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REPORT_DOWNLOAD_TIMEOUT_MS);
  onProgress?.(GENERATING_MSG);
  const endpoint = `report/${evidenceId}/download`;

  try {
    // Ensure report pipeline kicked off; download endpoint also auto-generates from cache
    const status = await getReportStatus(evidenceId);
    if (!status.ready) {
      await generateReport(evidenceId);
      if (status.status !== "processing") {
        await pollReportReady(evidenceId, {
          maxAttempts: 8,
          onProgress,
          signal: controller.signal,
        });
      }
    }

    const pipelineUrl = apiUrl(
      `${endpoint}?format=${encodeURIComponent(format)}${
        template && template !== "full"
          ? `&template=${encodeURIComponent(template)}`
          : ""
      }`
    );

    let response;
    try {
      response = await fetch(pipelineUrl, { signal: controller.signal });
    } catch (error) {
      console.log("[Report Download]", "Connectivity Error");
      throw toConnectivityError(error);
    }

    const contentType = (response.headers.get("content-type") || "").toLowerCase();
    if (contentType.includes("application/json")) {
      const body = await response.json().catch(() => ({}));
      const reason =
        body.reason || body.detail || body.message || "Failed to generate report.";
      throw new ApplicationError(reason, {
        status: response.status || 500,
        endpoint,
      });
    }

    if (response.status === 404) {
      const fallback = apiUrl(
        `reports/export/${evidenceId}?format=${encodeURIComponent(format)}&template=${encodeURIComponent(template)}`
      );
      try {
        response = await fetch(fallback, { signal: controller.signal });
      } catch (error) {
        console.log("[Report Download]", "Connectivity Error");
        throw toConnectivityError(error);
      }
    }

    if (response.status === 404) {
      console.log("[Report Download]", "404");
      throw new ApplicationError("Report not generated yet.", {
        status: 404,
        endpoint,
      });
    }

    if (!response.ok) {
      console.log("[Report Download]", response.status);
      throw await toApplicationError(
        response,
        "Failed to generate report.",
        endpoint
      );
    }

    console.log("[Report Download]", "Success", format);
    onProgress?.(`Downloading ${format.toUpperCase()}…`);
    const blob = await response.blob();
    const fallbackName = `${evidenceId}_${template}.${format}`;
    const filename = parseFilenameFromDisposition(
      response.headers.get("Content-Disposition"),
      fallbackName
    );

    onProgress?.("Downloading…");
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = filename;
    link.style.display = "none";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(objectUrl);

    return { success: true, filename, format, template };
  } catch (err) {
    if (err instanceof ApplicationError || err instanceof ConnectivityError) {
      throw err;
    }
    if (err?.name === "AbortError") {
      throw new ApplicationError("Report download timed out. Please retry.", {
        status: 408,
        endpoint,
      });
    }
    if (isConnectivityFailure(err)) {
      console.log("[Report Download]", "Connectivity Error");
      throw toConnectivityError(err);
    }
    console.log("[Report Download]", "Error", err?.message || err);
    throw new ApplicationError(err?.message || "Failed to generate report.", {
      endpoint,
    });
  } finally {
    clearTimeout(timeoutId);
  }
}

export const downloadPDF = (evidenceId, template = "full", onProgress) =>
  downloadReport(evidenceId, "pdf", template, onProgress);

export const downloadDOCX = (evidenceId, template = "full", onProgress) =>
  downloadReport(evidenceId, "docx", template, onProgress);

export const downloadHTML = (evidenceId, template = "full", onProgress) =>
  downloadReport(evidenceId, "html", template, onProgress);

export function getReportPreviewUrl(evidenceId, template = "full") {
  return apiUrl(
    `reports/preview/${evidenceId}/html?template=${encodeURIComponent(template)}`
  );
}

/** @deprecated Use downloadReport() */
export async function exportReport(evidenceId, format = "pdf", template = "full") {
  return downloadReport(evidenceId, format, template);
}

export function getReportDownloadUrl(evidenceId, format = "pdf", template = "full") {
  return apiUrl(
    `report/${evidenceId}/download?format=${encodeURIComponent(format)}&template=${encodeURIComponent(template)}`
  );
}

/* ========================================= */
/* Case Management                             */
/* ========================================= */

export async function getDashboardStats() {
  const response = await apiFetch("cases/dashboard/stats");
  if (!response.ok) throw new Error("Failed to load dashboard stats");
  const data = await response.json();
  return data.stats;
}

export async function listCases(limit = 50) {
  const response = await apiFetch(`cases?limit=${limit}`);
  if (!response.ok) throw new Error("Failed to list cases");
  return response.json();
}

export async function createCase(title, description = "") {
  const response = await apiFetch("cases", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, description }),
  });
  if (!response.ok) throw new Error(await getApiError(response, "Failed to create case"));
  return response.json();
}

export async function getCaseDetail(caseId) {
  const response = await apiFetch(`cases/${caseId}`);
  if (!response.ok) throw new Error("Case not found");
  return response.json();
}

export async function postCaseComment(caseId, body) {
  const response = await apiFetch(`cases/${caseId}/comments`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ body }),
  });
  if (!response.ok) throw new Error("Failed to post comment");
  return response.json();
}

/* ========================================= */
/* Learning AI                                 */
/* ========================================= */

export async function submitFeedback(payload) {
  const response = await apiFetch("learning/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error("Feedback submission failed");
  return response.json();
}

export async function getLearningStats() {
  const response = await apiFetch("learning/stats");
  if (!response.ok) throw new Error("Failed to load learning stats");
  return response.json();
}
