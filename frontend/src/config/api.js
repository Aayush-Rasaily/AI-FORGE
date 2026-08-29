/**
 * Centralized API configuration for AI-FORGE.
 * All HTTP calls MUST use API_BASE_URL (never localhost, never duplicate bases).
 */
export const API_ORIGIN = import.meta.env.VITE_API_ORIGIN || "http://127.0.0.1:8000";
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

export function apiUrl(path = "") {
  const cleaned = String(path || "").replace(/^\/+/, "");
  if (!cleaned) return API_BASE_URL;
  if (cleaned.startsWith("http://") || cleaned.startsWith("https://")) return cleaned;
  return `${API_BASE_URL}/${cleaned}`;
}

export function originUrl(path = "") {
  if (!path) return API_ORIGIN;
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  const cleaned = String(path).replace(/^\/+/, "");
  return `${API_ORIGIN}/${cleaned}`;
}
