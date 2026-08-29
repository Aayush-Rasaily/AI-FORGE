import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { FileSearch, FileText } from "lucide-react";

import AppLayout from "../components/layout/AppLayout";
import ExportReportPanel from "../components/investigation/ExportReportPanel";
import { getInvestigation, listRecentEvidence } from "../services/api";
import { useBackend } from "../context/BackendConnectivity";

function Reports() {
  const { online } = useBackend();
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState("");
  const [investigation, setInvestigation] = useState(null);

  useEffect(() => {
    if (!online) return undefined;
    let active = true;
    listRecentEvidence(30)
      .then((response) => {
        if (!active) return;
        const evidence = Array.isArray(response?.evidence) ? response.evidence : [];
        setItems(evidence);
        setSelected((current) => current || evidence[0]?.evidence_id || "");
      })
      .catch(() => {
        if (active) setItems([]);
      });
    return () => {
      active = false;
    };
  }, [online]);

  useEffect(() => {
    if (!selected || !online) {
      return undefined;
    }
    let active = true;
    getInvestigation(selected)
      .then((data) => active && setInvestigation(data))
      .catch(() => active && setInvestigation(null));
    return () => {
      active = false;
    };
  }, [online, selected]);

  const signature =
    investigation?.signature_result ||
    investigation?.analysis?.signature_analysis ||
    investigation?.signature_analysis ||
    null;
  const signatureFindings = signature?.findings || signature?.signature_regions || [];

  return (
    <AppLayout title="Reports" subtitle="Investigation disclosure packages">
      <div className="forge-ops">
        <header className="forge-page-intro">
          <div>
            <p className="forge-label">Disclosure</p>
            <h2>Investigation reports</h2>
            <p>Download the examination report, evidence summary, or technical appendix for selected evidence.</p>
          </div>
        </header>

        {items.length === 0 ? (
          <div className="forge-empty-result">
            <FileText className="h-5 w-5" />
            <div>
              <strong>No reportable investigations</strong>
              <p>Upload and examine evidence before generating a professional report.</p>
              <Link to="/dashboard" className="forge-primary-action mt-3 inline-flex">
                Add evidence
              </Link>
            </div>
          </div>
        ) : (
          <>
            <label className="forge-field">
              <span>Evidence record</span>
              <select value={selected} onChange={(event) => setSelected(event.target.value)}>
                {items.map((item) => (
                  <option key={item.evidence_id} value={item.evidence_id}>
                    {item.original_filename || item.evidence_id}
                  </option>
                ))}
              </select>
            </label>
            {signature && (
              <section className="forge-report-section" aria-labelledby="signature-report-title">
                <div className="forge-section-heading">
                  <FileSearch className="h-4 w-4" aria-hidden="true" />
                  <div>
                    <h2 id="signature-report-title">Signature Examination</h2>
                    <p>Signature evidence included in this investigation record.</p>
                  </div>
                </div>
                <dl className="forge-signature-facts">
                  <div><dt>Signature detected</dt><dd>{signature.signature_present === false ? "No" : "Yes"}</dd></div>
                  <div><dt>Signature count</dt><dd>{signature.signature_count ?? "Not available"}</dd></div>
                  <div><dt>Signature type</dt><dd>{signature.signature_type ?? "Not available"}</dd></div>
                  <div><dt>Comparison verdict</dt><dd>{signature.verdict ?? "Not available"}</dd></div>
                </dl>
                {signatureFindings.length > 0 && (
                  <ul className="forge-report-signature-findings">
                    {signatureFindings.map((finding, index) => (
                      <li key={finding.id || index}>
                        <strong>{finding.label || finding.title || finding.type || "Signature finding"}</strong>
                        <span>{finding.human_summary || finding.explanation || "Not available"}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            )}
            <ExportReportPanel evidenceId={selected} />
          </>
        )}
      </div>
    </AppLayout>
  );
}

export default Reports;
