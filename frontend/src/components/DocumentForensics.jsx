import DocumentOcrPanel from "./ui/DocumentOcrPanel";
import DocumentPageViewer from "./ui/DocumentPageViewer";
import RiskGauge from "./ui/RiskGauge";

function DocumentForensics({ result }) {
  if (!result) {
    return (
      <div className="mt-8 rounded-xl border border-slate-800 bg-slate-900 p-8">
        <h3 className="text-xl font-bold text-white">Document Forensics</h3>
        <p className="mt-3 text-slate-400">No document forensic result available.</p>
        <p className="mt-2 text-sm text-slate-500">
          Upload a PDF document and click &quot;Analyze Document&quot; to begin forensic analysis.
        </p>
      </div>
    );
  }

  const pages = Array.isArray(result.pages) ? result.pages : [];
  const pageCount = result.page_count || pages.length || 0;
  const riskScore = Math.round(Number(result.risk_score || 0));
  const docConfidence = Math.round(
    Number(result.document_confidence_pct ?? (result.document_confidence || 0) * 100)
  );
  const verdict = result.overall_verdict || "UNKNOWN";
  const findings = result.findings || [];
  const missingPages = result.missing_pages || null;

  if (pages.length === 0) {
    return (
      <div className="mt-8 rounded-xl border border-slate-800 bg-slate-900 p-8">
        <h3 className="text-xl font-bold text-white">Document Forensics</h3>
        <p className="mt-3 text-slate-400">
          Document analysis completed, but no pages were returned by the backend.
        </p>
      </div>
    );
  }

  return (
    <div className="mt-10 space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-white">Document Forensics Dashboard</h2>
        <p className="mt-2 text-sm text-slate-400">
          LayoutLMv3 + Donut transformer analysis with page-wise tampering detection.
        </p>
      </div>

      {/* Document summary */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <p className="text-sm text-slate-400">Document</p>
          <p className="mt-2 truncate text-lg font-bold text-white">
            {result.document_name || result.document_type || "PDF"}
          </p>
          <p className="mt-1 text-xs text-slate-500">{pageCount} pages</p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <p className="text-sm text-slate-400">Tamper Risk</p>
          <p className="mt-2 text-2xl font-bold text-white">{riskScore}%</p>
          <p className="mt-1 text-xs text-slate-500">{verdict}</p>
        </div>

        <div className="flex items-center justify-center rounded-xl border border-slate-800 bg-slate-900 p-4">
          <RiskGauge score={docConfidence} label="Doc Authenticity" invert size={120} />
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <p className="text-sm text-slate-400">Total Findings</p>
          <p className="mt-2 text-2xl font-bold text-white">{findings.length}</p>
          <p className="mt-1 text-xs text-slate-500">
            {result.models?.layoutlmv3 ? "LayoutLMv3" : ""}
            {result.models?.donut ? " · Donut" : ""}
          </p>
        </div>
      </div>

      {/* Interactive page viewer */}
      <DocumentPageViewer pages={pages} missingPages={missingPages} />

      {/* OCR panel for active first page with OCR */}
      {pages[0]?.ocr && !pages[0].ocr.skipped_ocr && (
        <DocumentOcrPanel ocr={pages[0].ocr} pageImage={pages[0].image} />
      )}
    </div>
  );
}

export default DocumentForensics;
