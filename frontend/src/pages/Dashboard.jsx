import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  AlertTriangle,
  ChevronRight,
  Download,
  FileSearch,
  FileText,
  Image,
  Microscope,
  PenTool,
  Plus,
  RefreshCw,
  Shield,
  Video,
} from "lucide-react";

import AppLayout from "../components/layout/AppLayout";
import EvidenceUploader from "../components/EvidenceUploader";
import {
  createCase,
  getDashboardStats,
  listRecentEvidence,
} from "../services/api";
import { useBackend } from "../context/BackendConnectivity";

function mediaFamily(value) {
  const key = String(value || "").toLowerCase();
  if (key.includes("video") || ["mp4", "mov", "avi", "mkv", "webm"].includes(key)) return "video";
  if (key.includes("image") || ["jpg", "jpeg", "png", "webp", "bmp", "tif", "tiff"].includes(key)) return "image";
  return "document";
}

function formatDate(value) {
  if (!value) return "Not recorded";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Not recorded" : date.toLocaleDateString();
}

function relativeTime(value) {
  if (!value) return "Time not recorded";
  const timestamp = new Date(value).getTime();
  if (!Number.isFinite(timestamp)) return "Time not recorded";
  const minutes = Math.max(0, Math.round((Date.now() - timestamp) / 60000));
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} hr ago`;
  return `${Math.round(hours / 24)} d ago`;
}

function typeLabel(value) {
  const family = mediaFamily(value);
  if (family === "video") return "Video";
  if (family === "image") return "Image";
  return "Document";
}

function riskFromCase(record) {
  const priority = String(record?.priority || "").toLowerCase();
  const verdict = String(record?.verdict || "").toLowerCase();
  if (priority === "critical" || /tamper|forg|manipul|fake/.test(verdict)) return "High";
  if (priority === "high" || /suspicious|anomal|review/.test(verdict)) return "Medium";
  if (/authentic|genuine|clean/.test(verdict)) return "Low";
  return "";
}

function Dashboard() {
  const navigate = useNavigate();
  const { online, reconnect } = useBackend();
  const [stats, setStats] = useState(null);
  const [recent, setRecent] = useState([]);
  const [loading, setLoading] = useState(true);
  const [files, setFiles] = useState([]);
  const [processing, setProcessing] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [caseId, setCaseId] = useState(null);
  const [loadError, setLoadError] = useState("");

  const loadData = useCallback(async () => {
    if (!online) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const [dashboard, evidence] = await Promise.all([
        getDashboardStats(),
        listRecentEvidence(20),
      ]);
      setLoadError("");
      setStats(dashboard || {});
      setRecent(Array.isArray(evidence?.evidence) ? evidence.evidence : []);
    } catch {
      setLoadError("Dashboard data is unavailable.");
      setStats(null);
      setRecent([]);
    } finally {
      setLoading(false);
    }
  }, [online]);

  useEffect(() => {
    const timer = window.setTimeout(loadData, 0);
    window.addEventListener("ai-forge-backend-online", loadData);
    window.addEventListener("ai-forge-evidence-changed", loadData);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("ai-forge-backend-online", loadData);
      window.removeEventListener("ai-forge-evidence-changed", loadData);
    };
  }, [loadData]);

  const completedCases = Math.max(
    0,
    Number(stats?.total_investigations || 0) - Number(stats?.open_investigations || 0)
  );
  const metrics = [
    [
      "Active investigations",
      stats?.open_investigations,
      Number(stats?.open_investigations || 0) > 0
        ? "Currently under examination"
        : "No active examinations",
    ],
    ["Completed", completedCases, "Closed case records"],
    [
      "High risk",
      stats?.high_risk_cases,
      Number(stats?.high_risk_cases || 0) > 0
        ? "Require investigator attention"
        : "No high-risk cases recorded",
    ],
    [
      "Pending review",
      stats?.pending_assignments,
      Number(stats?.pending_assignments || 0) > 0
        ? "Unresolved case assignments"
        : "No unresolved reviews",
    ],
  ];
  if (stats?.signature_examinations != null) {
    metrics.push(["Signature examinations", stats.signature_examinations, "Recorded signature reviews"]);
  }

  const activeInvestigations = (Array.isArray(stats?.recent_cases) ? stats.recent_cases : []).filter((record) =>
    ["open", "investigating", "pending"].includes(String(record?.status || "").toLowerCase())
  );
  const activities = recent.filter((record) => record?.intake_timestamp).slice(0, 6);
  const riskSummary = Object.entries(stats?.fraud_categories || {}).filter(([, value]) => Number(value) > 0);

  async function ensureCaseId(file) {
    if (caseId) return caseId;
    const response = await createCase(
      `Investigation — ${file?.name || "New evidence"} — ${new Date().toLocaleDateString()}`,
      "Created from the investigation control center."
    );
    const id = response?.case?.id;
    if (!id) throw new Error("The investigation record was not created.");
    setCaseId(id);
    return id;
  }

  function handleAnalysisResults(results) {
    const completed = (Array.isArray(results) ? results : []).find(
      (item) => item?.status === "completed" && item?.evidenceId
    );
    if (completed) navigate(`/investigation?evidence=${encodeURIComponent(completed.evidenceId)}`);
  }

  return (
    <AppLayout title="Overview" subtitle="Forensic operations center">
      <div className="forge-dashboard">
        <header className="forge-dashboard-hero">
          <div>
            <p className="forge-label">Investigation control center</p>
            <h2>Overview</h2>
            <p>Monitor active examinations, evidence processing, and forensic findings.</p>
          </div>
          <div className="forge-dashboard-actions">
            <Link to="/cases" className="forge-secondary-action">View cases</Link>
            <Link to="/investigation?new=1" className="forge-primary-action">
              <Plus className="h-4 w-4" />
              New investigation
            </Link>
          </div>
        </header>

        <section className="forge-intelligence-summary" aria-label="Investigation summary">
          {metrics.map(([label, value, description]) => (
            <div key={label} className="forge-intelligence-metric">
              <span>{label}</span>
              <strong>{loading || !stats ? "—" : value ?? 0}</strong>
              <small>{description}</small>
            </div>
          ))}
        </section>
        {loadError && <div className="forge-inline-error" role="status">{loadError}</div>}

        <div className="forge-dashboard-grid">
          <section className="forge-dashboard-section" aria-labelledby="active-investigations-title">
            <div className="forge-dashboard-section-heading">
              <div><p className="forge-label">Requires attention</p><h2 id="active-investigations-title">Active investigations</h2></div>
              <Link to="/cases" className="forge-inline-link">All cases <ChevronRight className="h-3.5 w-3.5" /></Link>
            </div>
            {activeInvestigations.length === 0 ? (
              <div className="forge-dashboard-empty">
                <Microscope className="h-5 w-5" />
                <strong>No active investigations</strong>
                <p>Start a new investigation by submitting evidence.</p>
                <Link to="/investigation?new=1" className="forge-secondary-action"><Plus className="h-3.5 w-3.5" /> New investigation</Link>
              </div>
            ) : (
              <div className="forge-active-list">
                {activeInvestigations.map((record) => {
                  const risk = riskFromCase(record);
                  const linkedEvidence = recent.find(
                    (item) => item?.investigation_id === record?.id
                  );
                  const evidenceId =
                    record?.latest_evidence_id ||
                    record?.evidence_id ||
                    linkedEvidence?.evidence_id;
                  return (
                    <button
                      type="button"
                      className="forge-active-row"
                      key={record.id}
                      onClick={() => navigate(
                        evidenceId
                          ? `/investigation?evidence=${encodeURIComponent(evidenceId)}`
                          : "/cases"
                      )}
                    >
                      <span className="forge-active-row-main">
                        <strong>{record.title || record.id}</strong>
                        <small>{record.id} · {record.evidence_count ?? "Evidence count not recorded"} evidence item(s)</small>
                      </span>
                      <span className="forge-active-row-meta">
                        <em>{caseStatus(record)}</em>
                        <em className={risk ? `forge-risk-text-${risk.toLowerCase()}` : ""}>{risk || "Risk not recorded"}</em>
                        <small>{relativeTime(record.updated_at || record.last_activity_at || record.created_at)}</small>
                      </span>
                      <ChevronRight className="h-4 w-4" aria-hidden="true" />
                    </button>
                  );
                })}
              </div>
            )}
          </section>

          <section className="forge-dashboard-section" aria-labelledby="activity-title">
            <div className="forge-dashboard-section-heading">
              <div><p className="forge-label">Recorded events</p><h2 id="activity-title">Investigation activity</h2></div>
            </div>
            {activities.length === 0 ? (
              <div className="forge-dashboard-empty">
                <AlertTriangle className="h-5 w-5" />
                <strong>No recent activity</strong>
                <p>Evidence events will appear after an examination begins.</p>
              </div>
            ) : (
              <ol className="forge-activity-list">
                {activities.map((record) => (
                  <li key={record.evidence_id}>
                    <span className="forge-activity-marker" aria-hidden="true" />
                    <div>
                      <strong>Evidence registered</strong>
                      <small>{record.original_filename || record.evidence_id}</small>
                      <small>{record.investigation_id || "Case not assigned"} · {relativeTime(record.intake_timestamp)}</small>
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </section>
        </div>

        <section className="forge-dashboard-intake" aria-labelledby="start-investigation-title">
          <div className="forge-dashboard-intake-copy">
            <p className="forge-label">Primary operation</p>
            <h2 id="start-investigation-title">Start new investigation</h2>
            <p>Submit evidence and begin a documented forensic examination.</p>
            <div className="forge-dashboard-intake-links">
              <Link to="/cases" className="forge-secondary-action">Select existing evidence</Link>
              <span>PDF · JPG · PNG · MP4 · MOV</span>
            </div>
          </div>
          {!online && (
            <div className="forge-inline-error">
              <span>The forensic service is offline. Uploads are paused.</span>
              <button type="button" onClick={reconnect}><RefreshCw className="h-3.5 w-3.5" /> Retry</button>
            </div>
          )}
          <div className="forge-dashboard-uploader">
            <EvidenceUploader
              analysisType="investigate"
              files={files}
              setFiles={setFiles}
              processing={processing}
              setProcessing={setProcessing}
              setResults={handleAnalysisResults}
              error={uploadError}
              setError={setUploadError}
              caseId={caseId}
              ensureCaseId={ensureCaseId}
              showOfflineBanner={false}
            />
          </div>
        </section>

        <section className="forge-pipeline-preview" aria-labelledby="pipeline-preview-title">
          <div className="forge-dashboard-section-heading">
            <div><p className="forge-label">Examination path</p><h2 id="pipeline-preview-title">Forensic pipeline</h2></div>
            <span className="forge-muted-note">Visual reference only</span>
          </div>
          <div className="forge-pipeline-track">
            {["Evidence intake", "Document / image / video analysis", "Signature analysis", "Tampering detection", "Localization", "Explainable analysis", "AI Jury", "Final assessment"].map((stage, index) => (
              <div className="forge-pipeline-stage" key={stage}>
                <span>{String(index + 1).padStart(2, "0")}</span><strong>{stage}</strong>
                {index < 7 && <ChevronRight className="h-4 w-4" aria-hidden="true" />}
              </div>
            ))}
          </div>
        </section>

        <section className="forge-capabilities" aria-labelledby="capabilities-title">
          <div className="forge-dashboard-section-heading">
            <div><p className="forge-label">Available examination modules</p><h2 id="capabilities-title">Forensic capabilities</h2></div>
          </div>
          <div className="forge-capability-grid">
            {[
              [FileText, "Document forensics", "Examine text, layout, metadata, and document structure.", "/investigation?mode=document"],
              [Image, "Image forensics", "Review compression, noise, edges, and copy-move evidence.", "/investigation?mode=image"],
              [Video, "Video / deepfake", "Inspect frames, temporal changes, and synthetic media signals.", "/investigation?mode=video"],
              [PenTool, "Signature analysis", "Examine and compare handwritten signatures using the trained verification model.", "/signature-analysis"],
              [Shield, "Tampering detection", "Correlate supported evidence of document and image alteration.", "/investigation"],
              [Microscope, "AI Jury", "Review independent dossier-backed forensic assessments.", "/investigation#expert-jury"],
            ].map(([Icon, label, description, to]) => (
              <Link to={to} className="forge-capability" key={label}>
                <Icon className="h-4 w-4" aria-hidden="true" />
                <span><strong>{label}</strong><small>{description}</small><em>Open module <ChevronRight className="h-3.5 w-3.5" /></em></span>
              </Link>
            ))}
          </div>
        </section>

        {riskSummary.length > 0 && (
          <section className="forge-risk-summary" aria-labelledby="risk-summary-title">
            <div className="forge-dashboard-section-heading">
              <div><p className="forge-label">Recorded classifications</p><h2 id="risk-summary-title">Forensic risk summary</h2></div>
            </div>
            <div className="forge-risk-summary-grid">
              {riskSummary.map(([label, value]) => <div key={label}><span>{label}</span><strong>{value}</strong></div>)}
            </div>
          </section>
        )}

        <section className="forge-dashboard-section" aria-labelledby="recent-evidence-title">
          <div className="forge-dashboard-section-heading">
            <div><p className="forge-label">Evidence register</p><h2 id="recent-evidence-title">Recent evidence</h2></div>
            <Link to="/history" className="forge-inline-link">View history <ChevronRight className="h-3.5 w-3.5" /></Link>
          </div>
          {recent.length === 0 ? (
            <div className="forge-dashboard-empty"><FileSearch className="h-5 w-5" /><strong>No evidence registered</strong><p>Start a new investigation by submitting evidence.</p></div>
          ) : (
            <div className="forge-table-wrap">
              <table className="forge-table">
                <thead><tr><th>Evidence</th><th>Case</th><th>Type</th><th>Status</th><th>Received</th><th>Action</th></tr></thead>
                <tbody>
                  {recent.slice(0, 8).map((item) => (
                    <tr key={item.evidence_id}>
                      <td data-label="Evidence">{item.original_filename || item.evidence_id}</td>
                      <td data-label="Case">{item.investigation_id || "Not assigned"}</td>
                      <td data-label="Type">{typeLabel(item.media_type)}</td>
                      <td data-label="Status"><span className={`forge-pill forge-pill-${String(item.status || "recorded").toLowerCase()}`}>{item.status || "Recorded"}</span></td>
                      <td data-label="Received">{formatDate(item.intake_timestamp)}</td>
                      <td data-label="Action"><button type="button" className="forge-table-action" onClick={() => navigate(`/investigation?evidence=${encodeURIComponent(item.evidence_id)}`)}>Open evidence</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <nav className="forge-quick-access" aria-label="Dashboard shortcuts">
          <Link to="/reports" className="forge-quick-link"><Download className="h-3.5 w-3.5" />Reports</Link>
          <Link to="/investigation#evidence-findings" className="forge-quick-link"><AlertTriangle className="h-3.5 w-3.5" />Review findings</Link>
        </nav>
      </div>
    </AppLayout>
  );
}

function caseStatus(record) {
  const value = String(record?.status || "");
  return value ? value.replace(/^./, (letter) => letter.toUpperCase()) : "Status not recorded";
}

export default Dashboard;
