import { RefreshCw } from "lucide-react";
import { useBackend } from "../../context/BackendConnectivity";

function BackendStatus({ className = "" }) {
  const { status, refreshHealth, backendOnline } = useBackend();
  const label =
    status === "online" ? "Connected" : status === "offline" ? "Offline" : "Connecting";

  return (
    <button
      type="button"
      onClick={refreshHealth}
      className={`forge-status forge-status-${status === "online" ? "ok" : status === "offline" ? "error" : "busy"} ${className}`}
      title="Refresh service status"
      aria-label={`Service ${label}`}
      data-backend-online={backendOnline ? "true" : "false"}
    >
      <span className="forge-status-dot" />
      <span>{label}</span>
      {status === "offline" && <RefreshCw className="h-3 w-3" />}
    </button>
  );
}

export default BackendStatus;
