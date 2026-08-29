import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { ConnectivityError, checkHealth } from "../services/api";
import { setBackendGateStatus } from "../services/connectivityGate";

const BackendConnectivityContext = createContext(null);

export function BackendProvider({ children }) {
  const [status, setStatus] = useState("connecting");
  const [backendOnline, setBackendOnline] = useState(false);
  const [healthData, setHealthData] = useState(null);
  const [checking, setChecking] = useState(false);
  const checkInFlight = useRef(null);

  const check = useCallback(() => {
    if (checkInFlight.current) return checkInFlight.current;

    const request = (async () => {
      setChecking(true);
      try {
        const data = await checkHealth();
        setHealthData(data);
        setBackendOnline(true);
        setStatus("online");
        setBackendGateStatus("online");
      } catch (err) {
        if (!(err instanceof ConnectivityError)) {
          console.warn("[Backend Health Failure]", err);
        }
        setBackendOnline(false);
        setStatus("offline");
        setBackendGateStatus("offline");
      } finally {
        setChecking(false);
      }
    })();

    checkInFlight.current = request;
    request.then(
      () => {
        if (checkInFlight.current === request) checkInFlight.current = null;
      },
      () => {
        if (checkInFlight.current === request) checkInFlight.current = null;
      }
    );
    return request;
  }, []);

  useEffect(() => {
    check();
  }, [check]);

  // Automatic retry every 5 seconds when disconnected/connecting, 30 seconds when online
  useEffect(() => {
    const retryIntervalMs = status === "online" ? 30000 : 5000;
    const timer = setInterval(() => {
      check();
    }, retryIntervalMs);
    return () => clearInterval(timer);
  }, [check, status]);

  const value = useMemo(
    () => ({
      status,
      backendOnline,
      online: backendOnline,
      healthData,
      health: healthData,
      checking,
      reconnect: check,
      refreshHealth: check,
      checkHealth: check,
    }),
    [status, backendOnline, healthData, checking, check]
  );

  return (
    <BackendConnectivityContext.Provider value={value}>
      {children}
    </BackendConnectivityContext.Provider>
  );
}

export function useBackend() {
  const ctx = useContext(BackendConnectivityContext);
  if (!ctx) {
    return {
      status: "online",
      backendOnline: true,
      online: true,
      healthData: null,
      health: null,
      checking: false,
      reconnect: () => {},
      refreshHealth: () => {},
      checkHealth: () => {},
    };
  }
  return ctx;
}

export default BackendConnectivityContext;
