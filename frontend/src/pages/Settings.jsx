import AppLayout from "../components/layout/AppLayout";
import BackendStatus from "../components/ui/BackendStatus";
import { useBackend } from "../context/BackendConnectivity";

function Settings() {
  const { health, online } = useBackend();
  const device = health?.hardware?.device || health?.inference?.device || "Not reported";

  return (
    <AppLayout title="Settings" subtitle="Service and investigator preferences">
      <div className="forge-ops">
        <header className="forge-page-intro">
          <div>
            <p className="forge-label">System</p>
            <h2>Settings</h2>
            <p>Operational status for the forensic examination service.</p>
          </div>
        </header>
        <dl className="forge-settings-list">
          <div>
            <dt>Service status</dt>
            <dd><BackendStatus /></dd>
          </div>
          <div>
            <dt>Connection</dt>
            <dd>{online ? "Connected" : "Offline"}</dd>
          </div>
          <div>
            <dt>Processing device</dt>
            <dd>{device}</dd>
          </div>
        </dl>
      </div>
    </AppLayout>
  );
}

export default Settings;
