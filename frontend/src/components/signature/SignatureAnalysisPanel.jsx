import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  FileSearch,
  Fingerprint,
  Image as ImageIcon,
  Loader2,
  Scale,
  ShieldAlert,
  Upload,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

import EvidenceUploader from "../EvidenceUploader";
import { useBackend } from "../../context/BackendConnectivity";
import {
  compareSignatures,
  createCase,
  getInvestigation,
  listRecentEvidence,
} from "../../services/api";

const MODES = [
  { id: "single", label: "Single signature analysis" },
  { id: "compare", label: "Signature comparison" },
];

function displayValue(value, fallback = "Not available") {
  return value == null || value === "" ? fallback : String(value);
}

function scoreLabel(value) {
  if (value == null || value === "") return "Not available";
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return String(value);
  return `${(numeric <= 1 ? numeric * 100 : numeric).toFixed(1)}%`;
}

function signaturePayload(result) {
  return (
    result?.signatureResult ||
    result?.signature_result ||
    result?.investigation?.signature_result ||
    result?.analysis?.signature_analysis ||
    result?.analysis?.signature ||
    result?.signature_analysis ||
    null
  );
}

function FileChoice({ label, file, onChange, inputId }) {
  return (
    <div className="forge-signature-upload">
      <div className="forge-signature-upload-header">
        <span>{label}</span>
        <Upload className="h-4 w-4" aria-hidden="true" />
      </div>
      <label htmlFor={inputId} className="forge-signature-dropzone">
        <ImageIcon className="h-6 w-6" aria-hidden="true" />
        <strong>{file ? file.name : "Choose signature image"}</strong>
        <span>PNG, JPG, or JPEG</span>
        <input
          id={inputId}
          type="file"
          accept=".png,.jpg,.jpeg,image/png,image/jpeg"
          onChange={(event) => onChange(event.target.files?.[0] || null)}
          className="sr-only"
        />
      </label>
    </div>
  );
}

function SignatureFindingCard({ finding, onViewEvidence }) {
  const bbox = finding?.bbox;
  return (
    <article className="forge-signature-finding">
      <div>
        <span className="forge-label">{displayValue(finding?.id, "Finding")}</span>
        <h3>{displayValue(finding?.label || finding?.title || finding?.type)}</h3>
      </div>
      <span className={`forge-severity forge-severity-${String(finding?.severity || "not-rated").toLowerCase()}`}>
        {displayValue(finding?.severity)}
      </span>
      <p>{displayValue(finding?.human_summary || finding?.explanation)}</p>
      <dl>
        <div><dt>Evidence strength</dt><dd>{scoreLabel(finding?.confidence)}</dd></div>
        <div><dt>Region</dt><dd>{bbox ? JSON.stringify(bbox) : "Not localized"}</dd></div>
      </dl>
      {onViewEvidence && bbox && (
        <button type="button" className="forge-secondary-action" onClick={onViewEvidence}>
          <FileSearch className="h-3.5 w-3.5" />
          View signature evidence
        </button>
      )}
    </article>
  );
}

function SingleSignatureResult({ result, onViewEvidence }) {
  const signature = signaturePayload(result);
  if (!signature) {
    return (
      <div className="forge-empty-result">
        <Fingerprint className="h-5 w-5" />
        <div>
          <strong>Signature analysis unavailable</strong>
          <p>The examination did not return signature analysis data.</p>
        </div>
      </div>
    );
  }
  const findings = signature.findings || signature.signature_regions || [];
  const detected = signature.signature_present;
  return (
    <div className="forge-signature-result">
      <div className="forge-signature-result-header">
        <div>
          <span className="forge-label">Single signature examination</span>
          <h2>{detected === false ? "No signature detected" : "Signature detected"}</h2>
        </div>
        {detected !== false && <CheckCircle2 className="h-5 w-5 text-emerald-400" aria-label="Signature detected" />}
      </div>
      {detected === false ? (
        <p className="forge-signature-muted">No signature detected in the submitted evidence.</p>
      ) : (
        <>
          <dl className="forge-signature-facts">
            <div><dt>Signature count</dt><dd>{displayValue(signature.signature_count)}</dd></div>
            <div><dt>Signature type</dt><dd>{displayValue(signature.signature_type)}</dd></div>
            <div><dt>Evidence strength</dt><dd>{scoreLabel(signature.signature_confidence ?? signature.confidence)}</dd></div>
          </dl>
          <div className="forge-signature-findings">
            <div className="forge-section-heading">
              <span className="forge-section-number">01</span>
              <div><h2>Forensic findings</h2><p>Findings returned by the signature examination.</p></div>
            </div>
            {findings.length > 0 ? findings.map((finding, index) => (
              <SignatureFindingCard
                key={finding.id || `signature-finding-${index}`}
                finding={finding}
                onViewEvidence={onViewEvidence ? () => onViewEvidence(finding) : null}
              />
            )) : (
              <div className="forge-empty-result"><p>No signature findings were returned.</p></div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function ComparisonResult({ response, previews }) {
  const [view, setView] = useState("side-by-side");
  const result = response?.result || response?.signature_verification || response;
  const visualization = result?.visualizations?.difference_heatmap ||
    result?.visualizations?.signature_overlay ||
    result?.visualization_b64 ||
    result?.visualization;
  if (!result) return null;

  return (
    <section className="forge-signature-result" aria-labelledby="comparison-result-title">
      <div className="forge-signature-result-header">
        <div>
          <span className="forge-label">Model-backed comparison</span>
          <h2 id="comparison-result-title">{displayValue(result.verdict)}</h2>
        </div>
        <Scale className="h-5 w-5 text-blue-300" aria-hidden="true" />
      </div>
      <div className="forge-signature-facts">
        <div><span>Similarity score</span><strong>{scoreLabel(result.similarity_score ?? result.similarity)}</strong></div>
        <div><span>Evidence strength</span><strong>{displayValue(result.evidence_strength || result.evidenceStrength || scoreLabel(result.confidence))}</strong></div>
        <div><span>Comparison ID</span><strong>{displayValue(result.id || response?.evidence_id)}</strong></div>
      </div>
      <p className="forge-signature-explanation">{displayValue(result.reason || result.explanation)}</p>
      <div className="forge-signature-tabs" role="tablist" aria-label="Signature comparison views">
        {[
          ["side-by-side", "Side-by-side"],
          ["overlay", "Overlay"],
          ["difference", "Difference"],
        ].map(([id, label]) => (
          <button key={id} type="button" role="tab" aria-selected={view === id} className={view === id ? "forge-filter-active" : ""} onClick={() => setView(id)}>
            {label}
          </button>
        ))}
      </div>
      <div className="forge-signature-visual">
        {view === "side-by-side" ? (
          <div className="forge-signature-preview-grid">
            <figure><figcaption>Reference signature</figcaption><img src={previews.reference} alt="Reference signature" /></figure>
            <figure><figcaption>Questioned signature</figcaption><img src={previews.questioned} alt="Questioned signature" /></figure>
          </div>
        ) : visualization ? (
          <figure><figcaption>{view === "difference" ? "Difference visualization" : "Signature overlay"}</figcaption><img src={visualization} alt={`${view} signature comparison`} /></figure>
        ) : (
          <p>Comparison visualization unavailable.</p>
        )}
      </div>
      <div className="forge-signature-metrics">
        {[
          ["Shape similarity", result.shape_similarity],
          ["Curvature similarity", result.curvature_similarity],
          ["Slant", result.slant],
          ["Aspect ratio", result.aspect_ratio],
          ["Keypoint similarity", result.keypoint_similarity],
          ["Embedding similarity", result.embedding_similarity ?? result.siamese_similarity],
        ].map(([label, value]) => <div key={label}><span>{label}</span><strong>{scoreLabel(value)}</strong></div>)}
      </div>
      <div className="forge-signature-region-columns">
        <div><span>Matched regions</span><p>{result.matched_regions?.length ? JSON.stringify(result.matched_regions) : "Not available"}</p></div>
        <div><span>Different regions</span><p>{result.different_regions?.length ? JSON.stringify(result.different_regions) : "Not available"}</p></div>
      </div>
    </section>
  );
}

function SignatureAnalysisPanel() {
  const navigate = useNavigate();
  const { backendOnline } = useBackend();
  const [mode, setMode] = useState("single");
  const [singleResult, setSingleResult] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [referenceFile, setReferenceFile] = useState(null);
  const [questionedFile, setQuestionedFile] = useState(null);
  const [previews, setPreviews] = useState({ reference: "", questioned: "" });
  const [existingEvidence, setExistingEvidence] = useState([]);
  const [selectedEvidence, setSelectedEvidence] = useState("");
  const [caseId, setCaseId] = useState(null);
  const [loadingExisting, setLoadingExisting] = useState(false);
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const [singleFiles, setSingleFiles] = useState([]);
  const [singleProcessing, setSingleProcessing] = useState(false);
  const [singleError, setSingleError] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const urls = {
      reference: referenceFile ? URL.createObjectURL(referenceFile) : "",
      questioned: questionedFile ? URL.createObjectURL(questionedFile) : "",
    };
    const timer = window.setTimeout(() => setPreviews(urls), 0);
    return () => {
      window.clearTimeout(timer);
      Object.values(urls).forEach((url) => url && URL.revokeObjectURL(url));
    };
  }, [referenceFile, questionedFile]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      listRecentEvidence(50)
        .then((response) => setExistingEvidence(Array.isArray(response?.evidence) ? response.evidence : []))
        .catch(() => setExistingEvidence([]));
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  const ensureCaseId = useCallback(async (file) => {
    if (caseId) return caseId;
    const response = await createCase(
      `Signature examination — ${file?.name || "evidence"}`,
      "Created from the Signature Analysis workspace."
    );
    const id = response?.case?.id;
    if (!id) throw new Error("An investigation record could not be created.");
    setCaseId(id);
    return id;
  }, [caseId]);

  const handleExistingEvidence = async (evidenceId) => {
    setSelectedEvidence(evidenceId);
    setSingleResult(null);
    setError("");
    if (!evidenceId) return;
    setLoadingExisting(true);
    try {
      const result = await getInvestigation(evidenceId);
      setSingleResult({
        evidenceId,
        filename: result?.filename,
        investigation: result,
        analysis: result?.analysis,
        signature_result: result?.signature_result,
      });
    } catch (loadError) {
      setError(loadError?.message || "Signature analysis unavailable");
    } finally {
      setLoadingExisting(false);
    }
  };

  const handleSingleResults = (results) => {
    const completed = (Array.isArray(results) ? results : []).find((item) => item?.status === "completed" && item?.evidenceId);
    if (completed) setSingleResult(completed);
    setSingleError("");
  };

  const handleViewEvidence = (finding) => {
    if (!singleResult?.evidenceId) return;
    const page = finding?.page != null ? `&page=${encodeURIComponent(finding.page)}` : "";
    navigate(`/investigation?evidence=${encodeURIComponent(singleResult.evidenceId)}${page}#document-viewer`);
  };

  const handleCompare = async (event) => {
    event.preventDefault();
    if (!referenceFile || !questionedFile) {
      setError("Select both a reference and questioned signature.");
      return;
    }
    setComparisonLoading(true);
    setComparison(null);
    setError("");
    try {
      const response = await compareSignatures(referenceFile, questionedFile);
      setComparison(response);
    } catch (compareError) {
      setError(compareError?.message || "Signature comparison is currently unavailable.");
    } finally {
      setComparisonLoading(false);
    }
  };

  const hasSingleResult = useMemo(() => Boolean(singleResult), [singleResult]);

  return (
    <div className="forge-signature-page">
      <header className="forge-page-intro">
        <div>
          <p className="forge-label">Identity and document examination</p>
          <h2>Signature Analysis</h2>
          <p>Examine handwritten signatures and compare questioned signatures against reference specimens.</p>
        </div>
        <div className="forge-signature-status"><span className={backendOnline ? "forge-status-dot-online" : "forge-status-dot-offline"} /> {backendOnline ? "Forensic service online" : "Forensic service offline"}</div>
      </header>

      <div className="forge-signature-mode-tabs" role="tablist" aria-label="Signature analysis modes">
        {MODES.map((item) => <button key={item.id} type="button" role="tab" aria-selected={mode === item.id} className={mode === item.id ? "forge-filter-active" : ""} onClick={() => { setMode(item.id); setError(""); }}>{item.label}</button>)}
      </div>

      {error && <div className="forge-inline-error" role="alert"><AlertCircle className="h-4 w-4" />{error}</div>}

      {mode === "single" ? (
        <section className="forge-panel forge-signature-single" aria-labelledby="single-signature-title">
          <div className="forge-section-heading">
            <span className="forge-section-number">01</span>
            <div><h2 id="single-signature-title">Single signature analysis</h2><p>Upload evidence or select an existing examination record.</p></div>
          </div>
          <div className="forge-signature-existing">
            <label htmlFor="existing-signature-evidence">Select existing evidence</label>
            <select id="existing-signature-evidence" value={selectedEvidence} onChange={(event) => handleExistingEvidence(event.target.value)} disabled={loadingExisting}>
              <option value="">Choose an evidence record</option>
              {existingEvidence.map((item) => <option key={item.evidence_id} value={item.evidence_id}>{item.original_filename || item.evidence_id}</option>)}
            </select>
          </div>
          <EvidenceUploader
            analysisType="investigate"
            files={singleFiles}
            setFiles={setSingleFiles}
            processing={singleProcessing}
            setProcessing={setSingleProcessing}
            setResults={handleSingleResults}
            error={singleError}
            setError={(message) => {
              setSingleError(message);
              setError(message);
            }}
            caseId={caseId}
            ensureCaseId={ensureCaseId}
            showOfflineBanner={false}
          />
          {hasSingleResult && <SingleSignatureResult result={singleResult} onViewEvidence={handleViewEvidence} />}
        </section>
      ) : (
        <section className="forge-panel forge-signature-comparison" aria-labelledby="comparison-title">
          <div className="forge-section-heading">
            <span className="forge-section-number">01</span>
            <div><h2 id="comparison-title">Signature comparison</h2><p>Compare two supplied signature specimens using the existing forensic comparison service.</p></div>
          </div>
          <form onSubmit={handleCompare}>
            <div className="forge-signature-upload-grid">
              <FileChoice label="Reference signature" file={referenceFile} onChange={setReferenceFile} inputId="reference-signature-file" />
              <FileChoice label="Questioned signature" file={questionedFile} onChange={setQuestionedFile} inputId="questioned-signature-file" />
            </div>
            <button type="submit" className="forge-primary-action mt-4" disabled={comparisonLoading || !backendOnline}>
              {comparisonLoading ? <><Loader2 className="h-4 w-4 animate-spin" /> Comparing signatures</> : <><Scale className="h-4 w-4" /> Compare signatures</>}
            </button>
          </form>
          {comparison && <ComparisonResult response={comparison} previews={previews} />}
          {!comparison && !comparisonLoading && <div className="forge-empty-result mt-5"><ShieldAlert className="h-5 w-5" /><div><strong>Comparison result</strong><p>Submit a reference and questioned signature to receive the backend verdict.</p></div></div>}
        </section>
      )}
    </div>
  );
}

export default SignatureAnalysisPanel;
