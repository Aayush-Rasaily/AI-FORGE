import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { motion, AnimatePresence } from "framer-motion";
import { WifiOff, RefreshCw } from "lucide-react";
import {
  checkBackendHealth,
  isBackendHealthy,
  listRecentEvidence,
  apiFetch,
  ConnectivityError,
} from "../services/api";

/**
 * Offline only when health AND report probe AND analysis probe all fail.
 * If /api/health is healthy → always Online.
 */
const BackendContext = createContext({
  status: "connecting",
  backendOnline: false,
  online: false,
  apiError: null,
  health: null,
  evidence: [],
  setApiError: () => {},
  clearApiError: () => {},
  refreshHealth: async () => {},
  refreshEvidence: async () => {},
});

export function useBackend() {
  return useContext(BackendContext);
}

async function probeEndpoint(path) {
  try {
    const response = await apiFetch(path);
    return response.ok || response.status < 500;
  } catch (error) {
    if (error instanceof ConnectivityError) return false;
    return false;
  }
}

export function BackendProvider({ children }) {
  const [status, setStatus] = useState("connecting"); // connecting | online | offline
  const [health, setHealth] = useState(null);
  const [evidence, setEvidence] = useState([]);
  const [apiError, setApiError] = useState(null);
  const mounted = useRef(true);
  const pollRef = useRef(null);

  const clearApiError = useCallback(() => setApiError(null), []);

  const refreshEvidence = useCallback(async () => {
    try {
      const data = await listRecentEvidence(50);
      if (mounted.current) {
        setEvidence(data.evidence || data.items || []);
      }
    } catch {
      // Evidence list failures never flip Online/Offline alone
    }
  }, []);

  /**
   * Online if health is healthy.
   * Offline only if health fails AND report probe fails AND analysis probe fails.
   */
  const refreshHealth = useCallback(async () => {
    try {
      const data = await checkBackendHealth();
      if (!mounted.current) return;

      if (isBackendHealthy(data)) {
        setHealth(data);
        setStatus("online");
        refreshEvidence().catch(() => {});
        return;
      }
    } catch {
      // Health failed — confirm with report + analysis probes before Offline
    }

    if (!mounted.current) return;

    const [reportOk, analysisOk] = await Promise.all([
      probeEndpoint("report/health-probe/status"),
      probeEndpoint("evidence/recent?limit=1"),
    ]);

    if (!mounted.current) return;

    // Any reachable secondary endpoint → stay Online (partial outage)
    if (reportOk || analysisOk) {
      setHealth(null);
      setStatus("online");
      return;
    }

    setHealth(null);
    setStatus("offline");
  }, [refreshEvidence]);

  useEffect(() => {
    mounted.current = true;
    setStatus("connecting");
    refreshHealth();

    pollRef.current = setInterval(refreshHealth, 10000);

    const onEvidence = () => refreshEvidence();
    window.addEventListener("ai-forge-evidence-changed", onEvidence);
    const onStorage = (e) => {
      if (e.key === "ai-forge-evidence-sync") refreshEvidence();
    };
    window.addEventListener("storage", onStorage);

    let channel;
    if (typeof BroadcastChannel !== "undefined") {
      channel = new BroadcastChannel("ai-forge-evidence");
      channel.onmessage = () => refreshEvidence();
    }

    return () => {
      mounted.current = false;
      if (pollRef.current) clearInterval(pollRef.current);
      window.removeEventListener("ai-forge-evidence-changed", onEvidence);
      window.removeEventListener("storage", onStorage);
      channel?.close();
    };
  }, [refreshHealth, refreshEvidence]);

  const backendOnline = status === "online";

  const value = useMemo(
    () => ({
      status,
      backendOnline,
      online: backendOnline,
      apiError,
      health,
      evidence,
      setApiError,
      clearApiError,
      refreshHealth,
      refreshEvidence,
    }),
    [
      status,
      backendOnline,
      apiError,
      health,
      evidence,
      clearApiError,
      refreshHealth,
      refreshEvidence,
    ]
  );

  return (
    <BackendContext.Provider value={value}>
      {children}
      <AnimatePresence>
        {status === "offline" && (
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 24 }}
            className="fixed bottom-6 right-6 z-[100] max-w-sm rounded-2xl border border-red-500/30 bg-[#0B1120]/95 p-4 shadow-2xl backdrop-blur-xl"
          >
            <div className="flex items-start gap-3">
              <div className="rounded-xl bg-red-500/10 p-2">
                <WifiOff className="h-5 w-5 text-red-400" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-white">Backend Offline</p>
                <p className="mt-1 text-xs text-slate-400">
                  Health, report, and analysis endpoints are unreachable.
                </p>
                <button
                  type="button"
                  onClick={refreshHealth}
                  className="mt-3 inline-flex items-center gap-2 rounded-lg bg-red-500/15 px-3 py-1.5 text-xs font-medium text-red-300 transition hover:bg-red-500/25"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  Retry / Reconnect
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </BackendContext.Provider>
  );
}
