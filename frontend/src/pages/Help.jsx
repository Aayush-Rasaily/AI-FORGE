import { Link } from "react-router-dom";
import AppLayout from "../components/layout/AppLayout";

function Help() {
  return (
    <AppLayout title="Help" subtitle="Investigator workflow">
      <div className="forge-ops forge-help">
        <header className="forge-page-intro">
          <div>
            <p className="forge-label">Guidance</p>
            <h2>Using AI-FORGE</h2>
            <p>A short workflow for professional forensic review.</p>
          </div>
        </header>
        <ol>
          <li>
            <strong>Add evidence</strong>
            <p>Upload a document, image, or video from Overview or Investigations. An investigation record is created automatically.</p>
          </li>
          <li>
            <strong>Review the verdict</strong>
            <p>The overall conclusion is based on supported findings. It is an investigative assessment, not a legal determination.</p>
          </li>
          <li>
            <strong>Inspect findings</strong>
            <p>Select a finding to move to the exact page, region, or frame in the evidence viewer.</p>
          </li>
          <li>
            <strong>Compare when a reference is linked</strong>
            <p>A linked reference is supporting evidence. Its authenticity depends on recorded provenance.</p>
          </li>
          <li>
            <strong>Download reports</strong>
            <p>Generate the investigation report, evidence summary, or technical appendix for disclosure.</p>
          </li>
        </ol>
        <Link to="/dashboard" className="forge-primary-action">Return to overview</Link>
      </div>
    </AppLayout>
  );
}

export default Help;
