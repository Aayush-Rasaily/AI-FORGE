import ErrorBoundary from "../ui/ErrorBoundary";
import ForensicEvidenceViewer from "./ForensicEvidenceViewer";

function ForensicEvidenceViewerSafe(props) {
  return (
    <ErrorBoundary
      name="ForensicEvidenceViewer"
      title="Forensic Evidence Viewer unavailable"
      message="The evidence viewer encountered an error. You can retry or continue using other investigation tools."
    >
      <ForensicEvidenceViewer {...props} />
    </ErrorBoundary>
  );
}

export default ForensicEvidenceViewerSafe;
