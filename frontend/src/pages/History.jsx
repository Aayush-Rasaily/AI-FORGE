import { useCallback, useEffect, useMemo, useState } from "react";
import { ExternalLink, History as HistoryIcon, Search } from "lucide-react";
import { useNavigate } from "react-router-dom";

import AppLayout from "../components/layout/AppLayout";
import { listRecentEvidence } from "../services/api";
import { useBackend } from "../context/BackendConnectivity";

function formatDate(value) {
  if (!value) return "Not recorded";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Not recorded" : date.toLocaleString();
}

function History() {
  const navigate = useNavigate();
  const { online } = useBackend();
  const [records, setRecords] = useState([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadHistory = useCallback(async () => {
    if (!online) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const response = await listRecentEvidence(100);
      setRecords(Array.isArray(response?.evidence) ? response.evidence : []);
    } catch (loadError) {
      setError(loadError?.message || "History unavailable");
      setRecords([]);
    } finally {
      setLoading(false);
    }
  }, [online]);

  useEffect(() => {
    const timer = window.setTimeout(loadHistory, 0);
    window.addEventListener("ai-forge-evidence-changed", loadHistory);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("ai-forge-evidence-changed", loadHistory);
    };
  }, [loadHistory]);

  const filteredRecords = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return records;
    return records.filter((record) =>
      [record.investigation_id, record.evidence_id, record.original_filename, record.status]
        .some((value) => String(value || "").toLowerCase().includes(needle))
    );
  }, [query, records]);

  return (
    <AppLayout title="History" subtitle="Recorded evidence examinations">
      <div className="forge-ops">
        <header className="forge-page-intro">
          <div>
            <p className="forge-label">Case record</p>
            <h2>Investigation history</h2>
            <p>Review registered evidence and reopen a prior examination.</p>
          </div>
          <label className="forge-search-field">
            <Search className="h-4 w-4" aria-hidden="true" />
            <span className="sr-only">Search investigation history</span>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search cases or evidence"
            />
          </label>
        </header>

        {error && <div className="forge-inline-error">{error}</div>}
        {loading ? (
          <div className="forge-loading-state" role="status">Loading examination history…</div>
        ) : filteredRecords.length === 0 ? (
          <div className="forge-empty-result">
            <HistoryIcon className="h-5 w-5" />
            <div>
              <strong>{records.length ? "No matching examinations" : "No examination history"}</strong>
              <p>Completed and registered evidence will appear here.</p>
            </div>
          </div>
        ) : (
          <div className="forge-table-wrap">
            <table className="forge-table">
              <thead>
                <tr>
                  <th>Case</th>
                  <th>Evidence</th>
                  <th>Date</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredRecords.map((record) => (
                  <tr
                    key={record.evidence_id}
                    onClick={() => navigate(`/investigation?evidence=${encodeURIComponent(record.evidence_id)}`)}
                    tabIndex={0}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        navigate(`/investigation?evidence=${encodeURIComponent(record.evidence_id)}`);
                      }
                    }}
                  >
                    <td data-label="Case">{record.investigation_id || "Not assigned"}</td>
                    <td data-label="Evidence">{record.original_filename || record.evidence_id}</td>
                    <td data-label="Date">{formatDate(record.intake_timestamp)}</td>
                    <td data-label="Status">
                      <span className={`forge-pill forge-pill-${String(record.status || "recorded").toLowerCase()}`}>
                        {record.status || "Recorded"}
                      </span>
                    </td>
                    <td data-label="Action">
                      <button type="button" className="forge-table-action" onClick={() => navigate(`/investigation?evidence=${encodeURIComponent(record.evidence_id)}`)}>
                        <ExternalLink className="h-3.5 w-3.5" />
                        Open case
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AppLayout>
  );
}

export default History;
