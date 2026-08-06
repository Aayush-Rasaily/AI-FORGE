/**
 * Centralized API configuration for AI-FORGE.
 * All HTTP calls MUST use API_BASE_URL (never localhost, never duplicate bases).
 */
export const API_ORIGIN = "http://127.0.0.1:8000";
export const API_BASE_URL = `${API_ORIGIN}/api`;

export function apiUrl(path = "") {
  const cleaned = String(path || "").replace(/^\/+/, "");
  if (!cleaned) return API_BASE_URL;
  return `${API_BASE_URL}/${cleaned}`;
}

export function originUrl(path = "") {
  if (!path) return API_ORIGIN;
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  const cleaned = String(path).replace(/^\/+/, "");
  return `${API_ORIGIN}/${cleaned}`;
}
