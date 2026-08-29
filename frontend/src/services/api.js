/**
 * AI-FORGE API client — single source of truth for backend HTTP.
 * Base: http://127.0.0.1:8000/api
 *
 * Error model (never mix):
 *   ConnectivityError  — network unreachable / timeout (health only drives Online/Offline)
 *   ApplicationError   — HTTP 4xx/5xx from a reachable backend
 */
import { API_BASE_URL, API_ORIGIN, apiUrl, originUrl } from "../config/api";
import {
  BackendGateError,
  prepareGatedFetch,
  isBackendGateOnline,
} from "./connectivityGate";

export { API_BASE_URL, API_ORIGIN, apiUrl, originUrl };
export { BackendGateError, isBackendGateOnline };

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
  constructor(message = "Backend Offline") {
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
  if (error instanceof BackendGateError) return true;
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
  if (error instanceof BackendGateError) {
    return new ConnectivityError(error.message);
  }
  return new ConnectivityError(
    error?.name === "AbortError" ? "Request cancelled" : "Connectivity Error"
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
 * Central fetch — gated by Backend Connectivity Manager.
 * Non-health requests are blocked while offline (no ERR_CONNECTION_REFUSED flood).
 */
export async function apiFetch(path, options = {}) {
  const url = path.startsWith("http") ? path : apiUrl(path);
  const token = typeof localStorage !== "undefined" ? localStorage.getItem("aiforge_access_token") : null;
  let gated;
  try {
    gated = prepareGatedFetch(url, options);
  } catch (error) {
    throw toConnectivityError(error);
  }

  try {
    return await fetch(url, {
      ...gated.options,
      headers: {
        Accept: "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers || {}),
      },
    });
  } catch (error) {
    if (error?.name === "AbortError") {
      throw toConnectivityError(error);
    }
    throw toConnectivityError(error);
  } finally {
    gated.cleanup();
  }
}

export function isBackendHealthy(health) {
  if (!health || typeof health !== "object") return false;
  const status = String(health.status || "").toLowerCase();
  return (
    status === "healthy" ||
    status === "ok" ||
    status === "success" ||
    status === "online" ||
    Boolean(health.service)
  );
}

const HEALTH_TIMEOUT_MS = 15000;

/**
 * Health check ONLY — sole authority for Online / Offline.
 * Always allowed by the gate (isHealthRequest).
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
      const statusMsg = `HTTP ${response.status} ${response.statusText}`;
      throw new ConnectivityError(`Health check failed: ${statusMsg}`);
    }

    const data = await response.json();

    if (!isBackendHealthy(data)) {
      throw new ConnectivityError("Health check returned unhealthy status payload");
    }

    return data;
  } catch (error) {
    if (controller.signal.aborted) {
      throw new ConnectivityError("Health check timed out");
    }
    throw toConnectivityError(error);
  } finally {
    clearTimeout(timer);
  }
}

export const checkHealth = checkBackendHealth;

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

export async function uploadEvidence(file, caseId) {
  if (!caseId) {
    throw new Error("A case must be selected before uploading evidence.");
  }
  const formData = new FormData();
  formData.append("file", file);
  let response;
  try {
    response = await apiFetch(`evidence/upload?investigation_id=${encodeURIComponent(caseId)}`, {
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
  if (!isBackendGateOnline()) {
    return { success: true, evidence: [] };
  }
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
  if (!isBackendGateOnline()) {
    if (onError) onError(new ConnectivityError("Backend Offline — progress stream blocked"));
    return () => {};
  }

  const url = apiUrl(`progress/stream/${jobId}`);
  const source = new EventSource(url);
  let closed = false;

  const close = () => {
    if (closed) return;
    closed = true;
    try {
      source.close();
    } catch {
      /* ignore */
    }
  };

  const gateWatcher = setInterval(() => {
    if (!isBackendGateOnline()) close();
  }, 1000);

  source.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onEvent(data);
      if (
        data.module === "pipeline" &&
        (data.status === "completed" || data.status === "failed")
      ) {
        close();
      }
    } catch (err) {
      console.warn("Progress parse error:", err);
    }
  };

  source.onerror = (err) => {
    close();
    if (onError) onError(err);
  };

  return () => {
    clearInterval(gateWatcher);
    close();
  };
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
    await _enrichAnalysisWithLocalization(evidenceId, data);
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
  await _enrichAnalysisWithLocalization(evidenceId, data);
  generateReport(evidenceId).catch(() => {});
  return data;
}

/* ========================================= */
/* Autonomous Investigation (Chief Investigator) */
/* ========================================= */

export async function investigateEvidence(evidenceId, { onProgress, forceDeep = false } = {}) {
  if (!evidenceId) throw new ApplicationError("Evidence ID required", { status: 400 });
  let unsubscribe = null;
  if (onProgress) {
    unsubscribe = subscribeAnalysisProgress(evidenceId, onProgress);
  }
  try {
    const path = `investigate/${evidenceId}${forceDeep ? "?force_deep=true" : ""}`;
    const response = await apiFetch(path, { method: "POST" });
    if (!response.ok) {
      throw await toApplicationError(
        response,
        "Autonomous investigation failed",
        path
      );
    }
    const data = await response.json();
    if (data.status === "failed") {
      throw new ApplicationError(data.reason || "Investigation failed", {
        status: 500,
        endpoint: path,
      });
    }
    notifyEvidenceChanged(evidenceId);
    if (data.reports_pending !== false) {
      generateReport(evidenceId).catch(() => {});
    }
    return data;
  } finally {
    if (unsubscribe) unsubscribe();
  }
}

export async function getInvestigation(evidenceId) {
  const response = await apiFetch(`investigate/${evidenceId}`);
  if (!response.ok) {
    throw await toApplicationError(response, "Investigation not found", `investigate/${evidenceId}`);
  }
  return response.json();
}

export async function askInvestigatorCopilot(question, evidenceId) {
  const response = await apiFetch("copilot/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, evidence_id: evidenceId || null }),
  });
  if (!response.ok) {
    throw await toApplicationError(response, "Copilot request failed", "copilot/ask");
  }
  return response.json();
}

export async function getFraudGraph(limitNodes = 200) {
  const response = await apiFetch(`graph/fraud?limit_nodes=${limitNodes}`);
  if (!response.ok) throw new Error(await getApiError(response, "Graph unavailable"));
  return response.json();
}

export async function searchInvestigationKnowledge(query, topK = 5) {
  const response = await apiFetch(
    `knowledge/search?q=${encodeURIComponent(query)}&top_k=${topK}`
  );
  if (!response.ok) throw new Error(await getApiError(response, "Knowledge search failed"));
  return response.json();
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

export async function compareSignatures(referenceFile, questionedFile) {
  if (!referenceFile || !questionedFile) {
    throw new Error("Reference and questioned signature files are required.");
  }
  const formData = new FormData();
  formData.append("reference", referenceFile);
  formData.append("questioned", questionedFile);
  const response = await apiFetch("signature/compare", {
    method: "POST",
    body: formData,
    headers: {},
  });
  if (!response.ok) {
    throw new Error(await getApiError(response, "Signature comparison failed"));
  }
  return response.json();
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
    await _enrichAnalysisWithLocalization(evidenceId, data);
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
}) {
  if (!evidenceId) throw new Error("Evidence ID is required for jury analysis.");

  const response = await apiFetch("jury/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      evidence_id: evidenceId || null,
    }),
  });

  if (!response.ok) {
    throw new Error(await getApiError(response, "AI Jury analysis failed"));
  }
  const data = await response.json();
  if (evidenceId) {
    notifyEvidenceChanged(evidenceId);
  }
  return data;
}

export async function getForensicArtifactJson(evidenceId, artifactType) {
  if (!evidenceId || !artifactType) return null;
  const response = await apiFetch(
    `evidence/artifacts/${encodeURIComponent(evidenceId)}/${encodeURIComponent(artifactType)}`
  );
  if (!response.ok) {
    throw await toApplicationError(
      response,
      `${artifactType} is unavailable`,
      `evidence/artifacts/${artifactType}`
    );
  }
  return response.json();
}

export function getExplainableAI(evidenceId) {
  return getForensicArtifactJson(evidenceId, "explainable_ai");
}

export function getInvestigationSummary(evidenceId) {
  return getForensicArtifactJson(evidenceId, "investigation_summary");
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
    if (!response.ok) return { status: "unknown", registry: {} };
    const data = await response.json();
    const registry = data.registry || {};
    const anyAvailable = Object.values(registry).some((entry) => entry?.available);
    return {
      ...data,
      registry,
      status: data.status || (anyAvailable ? "ready" : "generating"),
    };
  } catch {
    return { status: "unknown", registry: {} };
  }
}

export function isArtifactAvailable(registry, artifactType) {
  const entry = registry?.[artifactType];
  if (!entry) return false;
  return Boolean(entry.available);
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

const GENERATING_MSG =
  "Generating professional forensic report… Estimated time: 3–5 seconds";

let _performanceConfig = null;

function _defaultPerformanceConfig() {
  return {
    report_poll_interval_ms: Number(import.meta.env.VITE_REPORT_POLL_INTERVAL_MS || 500),
    report_poll_max_attempts: Number(import.meta.env.VITE_REPORT_POLL_MAX_ATTEMPTS || 12),
    artifact_poll_interval_ms: Number(import.meta.env.VITE_ARTIFACT_POLL_INTERVAL_MS || 1500),
    artifact_poll_max_attempts: Number(import.meta.env.VITE_ARTIFACT_POLL_MAX_ATTEMPTS || 20),
    sla_targets: {
      image_sec: Number(import.meta.env.VITE_SLA_IMAGE_SEC || 5),
      pdf_sec: Number(import.meta.env.VITE_SLA_PDF_SEC || 10),
      video_sec: Number(import.meta.env.VITE_SLA_VIDEO_SEC || 20),
    },
  };
}

/** Cached SLA + polling intervals from GET /api/health (single source of truth). */
export async function getPerformanceConfig(force = false) {
  if (_performanceConfig && !force) return _performanceConfig;
  const fallback = _defaultPerformanceConfig();
  try {
    const response = await apiFetch("health");
    if (response.ok) {
      const health = await response.json();
      const polling = health.polling || {};
      _performanceConfig = {
        report_poll_interval_ms:
          polling.report_poll_interval_ms ?? fallback.report_poll_interval_ms,
        report_poll_max_attempts:
          polling.report_poll_max_attempts ?? fallback.report_poll_max_attempts,
        artifact_poll_interval_ms:
          polling.artifact_poll_interval_ms ?? fallback.artifact_poll_interval_ms,
        artifact_poll_max_attempts:
          polling.artifact_poll_max_attempts ?? fallback.artifact_poll_max_attempts,
        sla_targets: health.sla_targets || fallback.sla_targets,
      };
      return _performanceConfig;
    }
  } catch {
    /* use fallback */
  }
  _performanceConfig = fallback;
  return _performanceConfig;
}

/**
 * Bounded artifact polling — replaces per-component setInterval duplication.
 */
export async function pollArtifactsReady(
  evidenceId,
  { intervalMs, maxAttempts, onUpdate, signal } = {}
) {
  if (!evidenceId) return { status: "unknown" };
  const cfg = await getPerformanceConfig();
  const waitMs = intervalMs ?? cfg.artifact_poll_interval_ms;
  const attemptsMax = maxAttempts ?? cfg.artifact_poll_max_attempts;

  for (let attempt = 0; attempt < attemptsMax; attempt += 1) {
    if (signal?.aborted) throw new Error("Polling cancelled");
    const status = await getArtifactsStatus(evidenceId);
    const registry = status.registry || {};
    const coreReady = ["ela", "edges", "wavelet", "copy_move"].some(
      (key) => registry[key]?.available
    );
    if (status.status === "ready" || coreReady) {
      onUpdate?.(status);
      return status;
    }
    await new Promise((r) => setTimeout(r, waitMs));
  }
  return { status: "timeout", registry: {} };
}

/**
 * Lightweight report readiness poll (uses server-configured intervals).
 */
export async function pollReportReadyLight(evidenceId, options = {}) {
  const cfg = await getPerformanceConfig();
  return pollReportReady(evidenceId, {
    intervalMs: options.intervalMs ?? cfg.report_poll_interval_ms,
    maxAttempts: options.maxAttempts ?? cfg.report_poll_max_attempts,
    onProgress: options.onProgress,
    signal: options.signal,
  });
}

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

export async function getLocalization(evidenceId, { refresh = false } = {}) {
  if (!isBackendGateOnline()) {
    throw new ConnectivityError("Backend Offline — localization blocked");
  }
  const q = refresh ? "?refresh=true" : "";
  const response = await apiFetch(`localization/${evidenceId}${q}`);
  if (!response.ok) {
    throw await toApplicationError(
      response,
      "Forgery localization failed",
      `localization/${evidenceId}`
    );
  }
  return response.json();
}

export async function getTimeline(evidenceId) {
  const response = await apiFetch(`timeline/${evidenceId}`);
  if (!response.ok) throw new Error(await getApiError(response, "Timeline not found"));
  return response.json();
}

export async function getEvidenceLocalization(evidenceId) {
  if (!isBackendGateOnline()) {
    throw new ConnectivityError("Backend Offline — localization blocked");
  }
  const response = await apiFetch(`evidence/${evidenceId}/localization`);
  if (!response.ok) {
    throw await toApplicationError(
      response,
      "Evidence localization failed",
      `evidence/${evidenceId}/localization`
    );
  }
  return response.json();
}

/** Canonical forensic findings. A null result signals legacy-adapter fallback. */
export async function getEvidenceFindings(evidenceId) {
  if (!evidenceId || !isBackendGateOnline()) return null;
  try {
    const response = await apiFetch(`evidence/${encodeURIComponent(evidenceId)}/findings`);
    if (response.status === 404 || response.status === 405 || response.status === 501) {
      return null;
    }
    if (!response.ok) {
      throw await toApplicationError(
        response,
        "Forensic findings are unavailable",
        `evidence/${evidenceId}/findings`
      );
    }
    return response.json();
  } catch (error) {
    if (error instanceof ConnectivityError || error instanceof BackendGateError) return null;
    throw error;
  }
}

/** Linked reference metadata. A null result means no link or endpoint unavailable. */
export async function getEvidenceReference(evidenceId) {
  if (!evidenceId || !isBackendGateOnline()) return null;
  try {
    const response = await apiFetch(`evidence/${encodeURIComponent(evidenceId)}/reference`);
    if ([404, 405, 501].includes(response.status)) return null;
    if (!response.ok) {
      throw await toApplicationError(
        response,
        "Reference evidence is unavailable",
        `evidence/${evidenceId}/reference`
      );
    }
    const data = await response.json();
    return data?.reference ? data : null;
  } catch (error) {
    if (error instanceof ConnectivityError || error instanceof BackendGateError) return null;
    throw error;
  }
}

export async function linkEvidenceReference(evidenceId, referenceEvidenceId) {
  if (!evidenceId || !referenceEvidenceId) {
    throw new ApplicationError("Both evidence IDs are required", { status: 400 });
  }
  try {
    const response = await apiFetch(`evidence/${encodeURIComponent(evidenceId)}/reference`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        reference_id: referenceEvidenceId,
        relationship: "supporting_reference",
        authenticity_status: "unknown",
      }),
    });
    if ([404, 405, 501].includes(response.status)) {
      return { success: false, unavailable: true, reference: null };
    }
    if (!response.ok) {
      throw await toApplicationError(
        response,
        "Reference evidence could not be linked",
        `evidence/${evidenceId}/reference`
      );
    }
    notifyEvidenceChanged(evidenceId);
    return response.json();
  } catch (error) {
    if (error instanceof ConnectivityError || error instanceof BackendGateError) {
      return { success: false, unavailable: true, reference: null };
    }
    throw error;
  }
}

export async function deleteEvidenceReference(evidenceId) {
  if (!evidenceId) throw new ApplicationError("Evidence ID required", { status: 400 });
  try {
    const response = await apiFetch(`evidence/${encodeURIComponent(evidenceId)}/reference`, {
      method: "DELETE",
    });
    if ([404, 405, 501].includes(response.status)) {
      return { success: false, unavailable: true, reference: null };
    }
    if (!response.ok) {
      throw await toApplicationError(
        response,
        "Reference evidence could not be removed",
        `evidence/${evidenceId}/reference`
      );
    }
    notifyEvidenceChanged(evidenceId);
    return response.json();
  } catch (error) {
    if (error instanceof ConnectivityError || error instanceof BackendGateError) {
      return { success: false, unavailable: true, reference: null };
    }
    throw error;
  }
}

export async function getOCRDifferenceReport(evidenceId) {
  if (!isBackendGateOnline()) {
    throw new ConnectivityError("Backend Offline — OCR report blocked");
  }
  const response = await apiFetch(`evidence/${evidenceId}/ocr-report`);
  if (!response.ok) {
    throw await toApplicationError(
      response,
      "OCR Difference report failed",
      `evidence/${evidenceId}/ocr-report`
    );
  }
  return response.json();
}

async function _enrichAnalysisWithLocalization(evidenceId, data) {
  if (!data || !data.analysis) return;
  try {
    const loc = await getEvidenceLocalization(evidenceId);
    if (loc && loc.success !== false) {
      data.analysis.localization = loc;
    }
  } catch (e) {
    console.warn("Could not fetch evidence localization", e);
  }
  try {
    const ocr = await getOCRDifferenceReport(evidenceId);
    if (ocr && ocr.success !== false) {
      data.analysis.ocrReport = ocr;
    }
  } catch (e) {
    console.warn("Could not fetch OCR difference report", e);
  }
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
        await pollReportReadyLight(evidenceId, {
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
      const gated = prepareGatedFetch(pipelineUrl, { signal: controller.signal });
      try {
        response = await fetch(pipelineUrl, gated.options);
      } finally {
        gated.cleanup();
      }
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
        const gated = prepareGatedFetch(fallback, { signal: controller.signal });
        try {
          response = await fetch(fallback, gated.options);
        } finally {
          gated.cleanup();
        }
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

    return {
      success: true,
      filename,
      format,
      template,
      verification_id: response.headers.get("X-Verification-Id") || null,
      verification_hash: response.headers.get("X-Verification-Hash") || null,
      verification_url: response.headers.get("X-Verification-Url") || null,
    };
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

/** POST export — returns verification metadata without re-downloading the blob. */
export async function exportReportMetadata(evidenceId, format = "pdf", template = "full") {
  const response = await apiFetch(`reports/export/${evidenceId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ format, template }),
  });
  if (!response.ok) {
    throw new Error(await getApiError(response, "Report export failed"));
  }
  return response.json();
}

/** Verify a digitally signed report by QR / cover-page verification ID. */
export async function verifyExportedReport(verificationId) {
  const response = await apiFetch(`reports/verify/${encodeURIComponent(verificationId)}`);
  if (!response.ok) {
    throw new Error(await getApiError(response, "Report verification failed"));
  }
  return response.json();
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
  if (!isBackendGateOnline()) {
    return {
      total_investigations: 0,
      open_investigations: 0,
      high_risk_cases: 0,
      total_evidence: 0,
      total_analyses: 0,
      pending_assignments: 0,
    };
  }
  try {
    const response = await apiFetch("cases/dashboard/stats");
    if (!response.ok) {
      return {
        total_investigations: 0,
        open_investigations: 0,
        high_risk_cases: 0,
        total_evidence: 0,
        total_analyses: 0,
        pending_assignments: 0,
      };
    }
    const data = await response.json();
    return data.stats || {};
  } catch {
    return {
      total_investigations: 0,
      open_investigations: 0,
      high_risk_cases: 0,
      total_evidence: 0,
      total_analyses: 0,
      pending_assignments: 0,
    };
  }
}

export async function listCases(limit = 50) {
  const response = await apiFetch(`cases?limit=${limit}`);
  if (!response.ok) throw new Error("Failed to list cases");
  return response.json();
}

export async function createCase(
  title,
  description = "",
  { organization = "", department = "", priority = "normal" } = {}
) {
  const response = await apiFetch("cases", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, description, organization, department, priority }),
  });
  if (!response.ok) throw new Error(await getApiError(response, "Failed to create case"));
  return response.json();
}

export async function getCaseMeta() {
  const response = await apiFetch("cases/meta");
  if (!response.ok) throw new Error("Failed to load case metadata");
  return response.json();
}

export async function updateCaseStatus(caseId, status) {
  const response = await apiFetch(`cases/${caseId}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
  if (!response.ok) throw new Error("Failed to update case status");
  return response.json();
}

export async function updateCasePriority(caseId, priority) {
  const response = await apiFetch(`cases/${caseId}/priority`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ priority }),
  });
  if (!response.ok) throw new Error("Failed to update case priority");
  return response.json();
}

export async function assignCaseInvestigator(caseId, investigatorId, { name, role = "lead" } = {}) {
  const response = await apiFetch(`cases/${caseId}/assign`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      investigator_id: investigatorId,
      investigator_name: name,
      role,
    }),
  });
  if (!response.ok) throw new Error("Failed to assign investigator");
  return response.json();
}

export async function createCaseTask(caseId, payload) {
  const response = await apiFetch(`cases/${caseId}/assignments`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error("Failed to create task");
  return response.json();
}

export async function updateCaseTaskStatus(assignmentId, status) {
  const response = await apiFetch(`cases/assignments/${assignmentId}?status=${encodeURIComponent(status)}`, {
    method: "PATCH",
  });
  if (!response.ok) throw new Error("Failed to update task");
  return response.json();
}

export async function getCaseTimeline(caseId) {
  const response = await apiFetch(`cases/${caseId}/timeline`);
  if (!response.ok) throw new Error("Failed to load timeline");
  return response.json();
}

export async function getCaseAuditLog(caseId) {
  const response = await apiFetch(`cases/${caseId}/audit`);
  if (!response.ok) throw new Error("Failed to load audit log");
  return response.json();
}

export async function listInvestigators() {
  const response = await apiFetch("cases/investigators/list");
  if (!response.ok) throw new Error("Failed to list investigators");
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

export async function getCaseGraph(caseId, focusEvidenceId, { rebuild = false } = {}) {
  const params = new URLSearchParams();
  if (focusEvidenceId) params.set("focus_evidence_id", focusEvidenceId);
  if (rebuild) params.set("rebuild", "true");
  const qs = params.toString() ? `?${params}` : "";
  const response = await apiFetch(`cases/${caseId}/graph${qs}`);
  if (!response.ok) throw new Error("Failed to load case graph");
  return response.json();
}

export async function getCaseCorrelation(caseId, { rebuild = false } = {}) {
  const qs = rebuild ? "?rebuild=true" : "";
  const response = await apiFetch(`cases/${caseId}/correlation${qs}`);
  if (!response.ok) throw new Error("Failed to load case correlation");
  return response.json();
}

export async function rebuildCaseGraph(caseId) {
  const response = await apiFetch(`cases/${caseId}/graph/rebuild`, { method: "POST" });
  if (!response.ok) throw new Error("Failed to rebuild case graph");
  return response.json();
}

export async function linkEvidenceToCase(caseId, evidenceId) {
  const response = await apiFetch(`cases/${caseId}/evidence/${evidenceId}`, { method: "POST" });
  if (!response.ok) throw new Error("Failed to link evidence to case");
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

export async function getEvaluationDashboard() {
  const response = await apiFetch("learning/evaluation");
  if (!response.ok) throw new Error("Failed to load evaluation dashboard");
  return response.json();
}

export async function getDetectorWeights() {
  const response = await apiFetch("learning/weights");
  if (!response.ok) throw new Error("Failed to load detector weights");
  return response.json();
}

export async function submitDetectorFeedback(payload) {
  const response = await apiFetch("learning/detector-feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error("Detector feedback submission failed");
  return response.json();
}

export async function listBenchmarkDatasets() {
  const response = await apiFetch("learning/benchmark/datasets");
  if (!response.ok) throw new Error("Failed to load benchmark datasets");
  return response.json();
}

export async function getBenchmarkResults() {
  const response = await apiFetch("learning/benchmark/results");
  if (!response.ok) throw new Error("Failed to load benchmark results");
  return response.json();
}

export async function runBenchmark(datasetType) {
  const qs = datasetType ? `?dataset_type=${encodeURIComponent(datasetType)}` : "";
  const response = await apiFetch(`learning/benchmark/run${qs}`, { method: "POST" });
  if (!response.ok) throw new Error("Benchmark run failed");
  return response.json();
}

/* ========================================= */
/* AI Investigator Copilot                     */
/* ========================================= */

export async function askCopilot(evidenceId, message, { sessionId } = {}) {
  if (!isBackendGateOnline()) {
    throw new ConnectivityError("Backend Offline — copilot blocked");
  }
  const response = await apiFetch(`copilot/${evidenceId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      session_id: sessionId || undefined,
    }),
  });
  if (!response.ok) {
    throw await toApplicationError(response, "Copilot request failed", `copilot/${evidenceId}/chat`);
  }
  return response.json();
}

export async function getCopilotContext(evidenceId) {
  const response = await apiFetch(`copilot/${evidenceId}/context`);
  if (!response.ok) throw new Error("Failed to load copilot context");
  return response.json();
}
