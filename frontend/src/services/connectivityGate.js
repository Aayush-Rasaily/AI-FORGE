/**
 * Global backend connectivity gate.
 * Only /api/health may run while offline. All other fetches are blocked
 * and in-flight requests are aborted to prevent ERR_CONNECTION_REFUSED floods.
 */

import { API_ORIGIN, apiUrl } from "../config/api";

/** @type {"connecting"|"online"|"offline"} */
let _status = "connecting";
const _listeners = new Set();
/** @type {Set<AbortController>} */
const _controllers = new Set();
/** @type {Array<() => void>} */
const _resumeQueue = [];

export class BackendGateError extends Error {
  constructor(message = "Backend Offline — request blocked") {
    super(message);
    this.name = "BackendGateError";
    this.code = "BACKEND_OFFLINE";
    this.kind = "connectivity";
  }
}

export function getBackendGateStatus() {
  return _status;
}

export function isBackendGateOnline() {
  return _status === "online";
}

export function subscribeBackendGate(listener) {
  _listeners.add(listener);
  return () => _listeners.delete(listener);
}

function _emit() {
  for (const fn of _listeners) {
    try {
      fn(_status);
    } catch {
      /* ignore listener errors */
    }
  }
}

export function setBackendGateStatus(next) {
  if (next === _status) return;
  const prev = _status;
  _status = next;
  _emit();

  if (next === "offline" || next === "connecting") {
    abortAllPendingRequests("Backend went offline");
  }

  if (next === "online" && prev !== "online") {
    const queued = _resumeQueue.splice(0, _resumeQueue.length);
    for (const fn of queued) {
      try {
        fn();
      } catch {
        /* ignore */
      }
    }
    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("ai-forge-backend-online"));
    }
  }
}

export function onBackendOnline(callback) {
  if (_status === "online") {
    try {
      callback();
    } catch {
      /* ignore */
    }
    return () => {};
  }
  _resumeQueue.push(callback);
  return () => {
    const idx = _resumeQueue.indexOf(callback);
    if (idx >= 0) _resumeQueue.splice(idx, 1);
  };
}

export function registerAbortController(controller) {
  _controllers.add(controller);
  return () => _controllers.delete(controller);
}

export function abortAllPendingRequests(reason = "Backend Offline") {
  for (const c of Array.from(_controllers)) {
    try {
      c.abort(reason);
    } catch {
      /* ignore */
    }
    _controllers.delete(c);
  }
}

export function isHealthRequest(url) {
  const u = String(url || "").toLowerCase();
  return (
    u.includes("/api/health") ||
    u.endsWith("/health") ||
    u.includes("health")
  );
}

/**
 * Merge caller signal with a tracked AbortController.
 * When offline (non-health), throws immediately without fetch.
 */
export function prepareGatedFetch(url, options = {}) {
  const health = isHealthRequest(url);
  if (!health && _status !== "online") {
    throw new BackendGateError();
  }

  const controller = new AbortController();
  registerAbortController(controller);

  const parent = options.signal;
  if (parent) {
    if (parent.aborted) {
      controller.abort(parent.reason);
    } else {
      parent.addEventListener(
        "abort",
        () => controller.abort(parent.reason),
        { once: true }
      );
    }
  }

  return {
    controller,
    options: {
      ...options,
      signal: controller.signal,
    },
    cleanup: () => _controllers.delete(controller),
  };
}

export function buildApiUrl(path) {
  if (String(path).startsWith("http")) return path;
  return apiUrl(path);
}

export { API_ORIGIN };
