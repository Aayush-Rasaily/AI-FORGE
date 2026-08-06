import { useEffect, useRef, useCallback } from "react";

import { API_ORIGIN } from "../config/api";

const WS_BASE = API_ORIGIN.replace(/^http/, "ws");

export function useWebSocketProgress(jobId, { onEvent, onDone, onError, enabled = true } = {}) {
  const wsRef = useRef(null);
  const onEventRef = useRef(onEvent);
  const onDoneRef = useRef(onDone);
  onEventRef.current = onEvent;
  onDoneRef.current = onDone;

  const connect = useCallback(() => {
    if (!jobId || !enabled) return;

    const url = `${WS_BASE}/api/ws/progress/${jobId}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onmessage = (msg) => {
      try {
        const data = JSON.parse(msg.data);
        if (data.type === "progress" && onEventRef.current) {
          onEventRef.current(data);
        }
        if (data.type === "done" && onDoneRef.current) {
          onDoneRef.current(data);
          ws.close();
        }
        if (data.type === "error" && onError) {
          onError(data);
        }
      } catch {
        // ignore parse errors
      }
    };

    ws.onerror = () => onError?.({ message: "WebSocket connection failed" });
    ws.onclose = () => { wsRef.current = null; };
  }, [jobId, enabled, onError]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  return { reconnect: connect };
}

export default useWebSocketProgress;
