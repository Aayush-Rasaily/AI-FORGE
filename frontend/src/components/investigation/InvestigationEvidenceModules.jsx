import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  FileText,
  Image,
  Info,
  PenTool,
  ScanSearch,
  Shield,
  Video,
} from "lucide-react";

import {
  getArtifactUrl,
  getArtifactsStatus,
  getLocalization,
  getOCRDifferenceReport,
} from "../../services/api";
import { useBackend } from "../../context/BackendConnectivity";

function firstObject(...values) {
  return values.find((value) => {
    if (!value || typeof value !== "object") return false;
    return Array.isArray(value) ? value.length > 0 : Object.keys(value).length > 0;
  }) || null;
}

function collection(data, ...keys) {
  if (!data || typeof data !== "object") return [];
  for (const key of keys) {
    if (Array.isArray(data[key])) return data[key].filter(Boolean);
  }
  return [];
}

function text(value, fallback = "") {
  if (value == null || value === "") return fallback;
  if (Array.isArray(value)) return value.filter(Boolean).map(String).join("; ");
  if (typeof value === "object") return fallback;
  return String(value);
}

function compactRecord(value) {
  if (!value || typeof value !== "object") return text(value);
  return Object.entries(value)
    .slice(0, 6)
    .map(([key, entry]) => `${key}: ${text(entry, "recorded")}`)
    .join(" · ");
}

function evidenceStrength(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "";
  const normalized = number <= 1 ? number * 100 : number;
  if (normalized >= 80) return "Strong";
  if (normalized >= 50) return "Moderate";
  return "Limited";
}

function rowId(row) {
  return row?.finding_id || row?.findingId || row?.id || row?.region_id || null;
}

function findingTitle(row, fallback) {
  return text(
    row?.title || row?.label || row?.edit_type || row?.change_type || row?.type || row?.field || row?.category,
    fallback
  ).replaceAll("_", " ");
}

function findingReason(row) {
  return text(
    row?.human_summary ||
      row?.description ||
      row?.technical_reason ||
      row?.reason ||
      row?.explanation ||
      row?.why,
    "Reason not recorded."
  );
}

function locationText(row) {
  if (typeof row?.location === "string") return row.location;
  if (row?.location?.description) return text(row.location.description);
  if (row?.where) return text(row.where);
  if (row?.page != null) return `Page ${row.page}`;
  if (row?.bbox) return "Localized region";
  return "Location not recorded";
}

function resolveArtifact(value, evidenceId) {
  if (!value || typeof value !== "string") return "";
  if (value.startsWith("/api/") || value.startsWith("http")) return getArtifactUrl(value);
  const normalized = value.replaceAll("\\", "/");
  if (normalized.startsWith("/data/") || normalized.startsWith("data/") || normalized.includes("/data/")) {
    const dataPath = normalized.slice(normalized.toLowerCase().lastIndexOf("data/"));
    return getArtifactUrl(dataPath);
  }
  const filename = normalized.split("/").pop();
  return evidenceId && filename
    ? getArtifactUrl(`/api/localization/${evidenceId}/file/${filename}`)
    : getArtifactUrl(value);
}

function ModuleCard({ icon: Icon, title, description, children, available }) {
  return (
    <article className="forge-module-card">
      <div className="forge-module-card-heading">
        <Icon className="h-4 w-4" aria-hidden="true" />
        <div>
          <h3>{title}</h3>
          <p>{description}</p>
        </div>
      </div>
      {available ? children : (
        <div className="forge-module-empty">
          <Info className="h-3.5 w-3.5" />
          <span>No evidence detected in this module.</span>
        </div>
      )}
    </article>
  );
}

function EvidenceRows({ rows, onFindingSelect }) {
  if (!rows.length) {
    return <p className="forge-module-muted">No finding-level evidence recorded.</p>;
  }
  return (
    <div className="forge-module-findings">
      {rows.slice(0, 8).map((row, index) => {
        const id = rowId(row);
        const strength = evidenceStrength(row?.confidence ?? row?.score);
        const before =
          row?.original ??
          row?.before ??
          row?.old_value ??
          row?.original_value ??
          row?.reference_value ??
          row?.expected;
        const after =
          row?.detected ??
          row?.after ??
          row?.new_value ??
          row?.detected_value ??
          row?.examined_value ??
          row?.observed;
        return (
          <div className="forge-module-finding" key={id || `${row.type}-${index}`}>
            <div>
              <strong>{findingTitle(row, "Recorded finding")}</strong>
              <small>
                {locationText(row)}
                {row?.page != null ? ` · Page ${row.page}` : ""}
                {row?.severity ? ` · ${text(row.severity)}` : ""}
              </small>
            </div>
            {(before != null || after != null) && (
              <small className="forge-module-value-diff">
                Recorded change: {text(before, "not recorded")} → {text(after, "not recorded")}
              </small>
            )}
            <p>{findingReason(row)}</p>
            {strength && <span>Evidence strength: {strength}</span>}
            {id && row?.bbox && (
              <button type="button" onClick={() => onFindingSelect?.(id)}>
                View evidence
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}

function OcrModule({ data, onFindingSelect }) {
  const rows = collection(data, "findings", "differences", "changes", "fields");
  return (
    <ModuleCard
      icon={FileText}
      title="OCR difference examination"
      description="Recorded text and numeric discrepancies"
      available={Boolean(data)}
    >
      <EvidenceRows rows={rows} onFindingSelect={onFindingSelect} />
      {data?.summary && <p className="forge-module-summary-text">{text(data.summary)}</p>}
    </ModuleCard>
  );
}

function TamperingModule({ data, onFindingSelect }) {
  const rows = collection(data, "findings", "regions", "detections", "anomalies");
  const signals = collection(data, "signals", "methods");
  return (
    <ModuleCard
      icon={ScanSearch}
      title="Tampering examination"
      description="Recorded alteration, rendering, and compression evidence"
      available={Boolean(data)}
    >
      <EvidenceRows rows={rows} onFindingSelect={onFindingSelect} />
      {signals.length > 0 && (
        <p className="forge-module-summary-text">
          Recorded signals: {signals.map((signal) => text(signal)).filter(Boolean).join("; ")}
        </p>
      )}
    </ModuleCard>
  );
}

function SignatureModule({ data, evidenceId, onFindingSelect }) {
  const rows = collection(data, "findings", "signature_regions", "regions");
  const similarity = data?.similarity_score ?? data?.similarity;
  const similarityDisplay = similarity == null
    ? ""
    : Number(similarity) <= 1
      ? `${Math.round(Number(similarity) * 100)}%`
      : `${text(similarity)}%`;
  const visualizations = data?.visualizations || data?.visualization || data?.artifact_urls || {};
  const visualizationItems = [
    ["Signature overlay", visualizations.signature_overlay || visualizations.overlay],
    ["Matching regions", visualizations.matching_regions || visualizations.matches],
    ["Difference heatmap", visualizations.difference_heatmap || visualizations.difference],
  ]
    .map(([label, value]) => ({ label, url: resolveArtifact(value, evidenceId) }))
    .filter((item) => item.url);
  return (
    <ModuleCard
      icon={PenTool}
      title="Signature examination"
      description="Detection, verification, and identity evidence"
      available={Boolean(data)}
    >
      <dl className="forge-module-facts">
        {data?.signature_present != null && <div><dt>Detected signatures</dt><dd>{data.signature_present ? "Yes" : "No"}</dd></div>}
        {data?.signature_count != null && <div><dt>Signature count</dt><dd>{data.signature_count}</dd></div>}
        {data?.signature_type && <div><dt>Type</dt><dd>{text(data.signature_type)}</dd></div>}
        {data?.verdict && <div><dt>Verification verdict</dt><dd>{text(data.verdict)}</dd></div>}
        {similarity != null && <div><dt>Similarity</dt><dd>{similarityDisplay}</dd></div>}
      </dl>
      <EvidenceRows rows={rows} onFindingSelect={onFindingSelect} />
      {visualizationItems.length > 0 && (
        <div className="forge-module-artifacts">
          {visualizationItems.map((item) => (
            <a href={item.url} target="_blank" rel="noreferrer" key={item.label}>
              <img src={item.url} alt={item.label} />
              <span>{item.label}</span>
            </a>
          ))}
        </div>
      )}
    </ModuleCard>
  );
}

function DeepfakeModule({ data, onFindingSelect }) {
  const heatmap = resolveArtifact(data?.heatmap_url || data?.heatmap, data?.evidence_id);
  const rows = collection(data, "findings", "regions", "detections");
  return (
    <ModuleCard
      icon={Video}
      title="Synthetic media examination"
      description="Deepfake and generative-content indicators"
      available={Boolean(data)}
    >
      <dl className="forge-module-facts">
        {(data?.detected ?? data?.deepfake_detected ?? data?.is_deepfake) != null && (
          <div><dt>Deepfake detected</dt><dd>{(data.detected ?? data.deepfake_detected ?? data.is_deepfake) ? "Yes" : "No"}</dd></div>
        )}
        {data?.face_swap_detected != null && <div><dt>Face swap indicator</dt><dd>{data.face_swap_detected ? "Present" : "Not detected"}</dd></div>}
        {data?.gan_detected != null && <div><dt>Generative indicator</dt><dd>{data.gan_detected ? "Present" : "Not detected"}</dd></div>}
        {data?.verdict && <div><dt>Assessment</dt><dd>{text(data.verdict)}</dd></div>}
        {(data?.confidence ?? data?.synthetic_score) != null && (
          <div><dt>Evidence strength</dt><dd>{evidenceStrength(data.confidence ?? data.synthetic_score) || "Recorded"}</dd></div>
        )}
      </dl>
      {(data?.summary || data?.reason || data?.explanation) && (
        <p className="forge-module-summary-text">{text(data.summary || data.reason || data.explanation)}</p>
      )}
      <EvidenceRows rows={rows} onFindingSelect={onFindingSelect} />
      {heatmap && <a className="forge-module-artifact-link" href={heatmap} target="_blank" rel="noreferrer">Open recorded heatmap</a>}
    </ModuleCard>
  );
}

function MetadataModule({ data }) {
  const values = [
    ["Original metadata", data?.original_metadata],
    ["Edited metadata", data?.edited_metadata],
    ["Creation", data?.creation || data?.created || data?.creation_timestamp],
    ["Modified", data?.modified || data?.modified_timestamp || data?.metadataModificationDate],
    ["Author", data?.author],
    ["Software", data?.software || data?.editing_software],
    ["Producer", data?.producer],
    ["Visible document date", data?.visibleDocumentDate || data?.visible_document_date],
  ].filter(([, value]) => value != null && value !== "");
  const genericValues = values.length > 0
    ? []
    : Object.entries(data || {})
      .filter(([, value]) => value != null && typeof value !== "function")
      .slice(0, 8);
  const displayValues = [...values, ...genericValues];
  return (
    <ModuleCard
      icon={Shield}
      title="Metadata and provenance"
      description="File history, authoring, and timestamp records"
      available={Boolean(data)}
    >
      {displayValues.length > 0 ? (
        <dl className="forge-module-facts">
          {displayValues.map(([label, value]) => <div key={label}><dt>{label.replaceAll("_", " ")}</dt><dd>{compactRecord(value)}</dd></div>)}
        </dl>
      ) : (
        <p className="forge-module-muted">No metadata fields were recorded.</p>
      )}
      {data?.discrepancyExplanation && <p className="forge-module-summary-text">{text(data.discrepancyExplanation)}</p>}
    </ModuleCard>
  );
}

function ExplainableFindings({ result, onFindingSelect }) {
  const dossier = result?.forensicDossier || result?.forensic_dossier || {};
  const explainable = result?.explainableAI || result?.explainable_ai || {};
  const summary = result?.investigationSummary || result?.investigation_summary || {};
  const findings =
    collection(explainable, "findings", "human_findings").length > 0
      ? collection(explainable, "findings", "human_findings")
      : collection(summary, "findings", "human_findings").length > 0
        ? collection(summary, "findings", "human_findings")
        : collection(dossier, "human_findings", "findings");

  return (
    <section className="forge-explainable-findings" aria-labelledby="explainable-findings-title">
      <div className="forge-section-heading">
        <div>
          <h2 id="explainable-findings-title">Explainable examination</h2>
          <p>What changed, where it was observed, and why it matters</p>
        </div>
      </div>
      {findings.length > 0 ? (
        <div className="forge-explainable-grid">
          {findings.slice(0, 12).map((finding, index) => {
            const id = rowId(finding);
            const evidence = collection(finding, "evidence", "supporting_evidence");
            const evidenceText = evidence.length > 0
              ? evidence.map((item) => text(item)).filter(Boolean).join("; ")
              : text(finding.observed_evidence);
            return (
              <article className="forge-explainable-card" key={id || `explanation-${index}`}>
                <div className="forge-explainable-card-topline">
                  <h3>{findingTitle(finding, "Recorded finding")}</h3>
                  {finding.severity && <span>{text(finding.severity)}</span>}
                </div>
                <dl>
                  <div><dt>Where</dt><dd>{locationText(finding)}</dd></div>
                  <div><dt>Observation</dt><dd>{text(finding.observation || finding.description || finding.human_summary, "Not recorded")}</dd></div>
                  <div><dt>Reason</dt><dd>{text(finding.reason || finding.explanation || finding.technical_reason, "Not recorded")}</dd></div>
                  {(evidence.length > 0 || evidenceText) && <div><dt>Evidence</dt><dd>{evidenceText}</dd></div>}
                  <div><dt>Impact</dt><dd>{text(finding.impact || finding.potential_impact, "Not recorded")}</dd></div>
                  <div><dt>Recommendation</dt><dd>{text(finding.recommendation || finding.recommended_action, "Not recorded")}</dd></div>
                </dl>
                {id && finding.bbox && (
                  <button type="button" onClick={() => onFindingSelect?.(id)}>View evidence</button>
                )}
              </article>
            );
          })}
        </div>
      ) : (
        <div className="forge-module-empty">
          <Info className="h-4 w-4" />
          <span>No explainable finding narrative was recorded.</span>
        </div>
      )}
    </section>
  );
}

export default function InvestigationEvidenceModules({
  evidenceId,
  result,
  onFindingSelect,
}) {
  const { backendOnline } = useBackend();
  const [ocrReport, setOcrReport] = useState(null);
  const [localization, setLocalization] = useState(null);
  const [artifactCatalog, setArtifactCatalog] = useState(null);
  const [errors, setErrors] = useState([]);
  const [loadingModules, setLoadingModules] = useState(false);

  useEffect(() => {
    if (!evidenceId || !backendOnline) return undefined;
    let active = true;
    const loadingTimer = window.setTimeout(() => {
      if (active) setLoadingModules(true);
    }, 0);
    Promise.allSettled([
      getOCRDifferenceReport(evidenceId),
      getLocalization(evidenceId),
      getArtifactsStatus(evidenceId),
    ]).then(([ocrResult, localizationResult, artifactResult]) => {
      if (!active) return;
      const nextErrors = [];
      if (ocrResult.status === "fulfilled") setOcrReport(ocrResult.value);
      else nextErrors.push("OCR difference data is unavailable.");
      if (localizationResult.status === "fulfilled") setLocalization(localizationResult.value);
      else nextErrors.push("Localization data is unavailable.");
      if (artifactResult?.status === "fulfilled") setArtifactCatalog(artifactResult.value);
      else nextErrors.push("Recorded artifact status is unavailable.");
      setErrors(nextErrors);
      setLoadingModules(false);
    });
    return () => {
      active = false;
      window.clearTimeout(loadingTimer);
      setLoadingModules(false);
    };
  }, [backendOnline, evidenceId]);

  const modules = useMemo(() => {
    const analysis = result?.analysis || {};
    const investigation = result?.investigation || {};
    const videoAnalysis = result?.videoAnalysis || investigation.video_analysis || {};
    const metadataAgent = result?.agents?.metadata?.data || {};
    return {
      ocr: firstObject(
        ocrReport,
        analysis.ocrReport,
        analysis.ocr_difference,
        investigation.ocr_difference
      ),
      tampering: firstObject(
        result?.tampering,
        result?.documentAnalysis?.tampering,
        investigation.document_tampering,
        investigation.document_analysis?.tampering,
        analysis.document_tampering,
        analysis.tampering
      ),
      signature: firstObject(
        result?.signatureResult,
        result?.signature_result,
        investigation.signature_analysis,
        analysis.signature_analysis,
        result?.signature_verification
      ),
      deepfake: firstObject(
        result?.deepfakeAnalysis,
        result?.deepfake_analysis,
        videoAnalysis.deepfake_analysis,
        videoAnalysis.deepfake,
        investigation.deepfake_analysis,
        analysis.deepfake_analysis,
        analysis.deepfake,
        result?.deepfake_analysis
      ),
      metadata: firstObject(
        result?.metadata,
        metadataAgent.raw_metadata,
        metadataAgent.metadata_agent,
        analysis.metadata_forensics,
        analysis.metadata,
        investigation.metadata_forensics,
        result?.metadata
      ),
    };
  }, [ocrReport, result]);

  const gallery = useMemo(() => {
    const views = localization?.views || {};
    const files = localization?.views || localization?.overlay_files || localization?.files || {};
    const artifacts = {
      ...Object.fromEntries(
        Object.entries(artifactCatalog?.registry || {})
          .filter(([, entry]) => entry?.available && entry?.artifact_path)
          .map(([key, entry]) => [key, entry.artifact_path])
      ),
      ...(result?.artifacts || {}),
    };
    return [
      ["Original", views.original || files.original || artifacts.original],
      ["Localized overlay", views.combined_overlay || views.highlighted || views.annotated || views.overlay || files.combined_overlay || files.highlight || artifacts.combined_overlay],
      ["Heatmap", views.forensic_heatmap || views.heatmap || files.forensic_heatmap || files.heatmap || artifacts.forensic_heatmap],
      ["Mask / bounding boxes", views.localization_mask || views.forgery_mask || views.mask_binary || views.mask || files.localization_mask || files.mask_binary || files.mask || artifacts.localization_mask],
    ]
      .map(([label, value]) => ({ label, url: resolveArtifact(value, evidenceId) }))
      .filter((item) => item.url);
  }, [artifactCatalog, evidenceId, localization, result?.artifacts]);

  return (
    <>
      <section className="forge-evidence-modules" aria-labelledby="evidence-summary-title">
        <div className="forge-section-heading">
          <div>
            <h2 id="evidence-summary-title">Evidence summary</h2>
            <p>Recorded forensic output by examination module</p>
          </div>
        </div>
        {errors.length > 0 && (
          <div className="forge-inline-notice forge-inline-notice-warning" role="status">
            <AlertTriangle className="h-4 w-4" />
            <span>{errors.join(" ")}</span>
          </div>
        )}
        {loadingModules && (
          <div className="forge-inline-notice" role="status">
            <span>Retrieving recorded module evidence…</span>
          </div>
        )}
        <div className="forge-module-grid">
          <OcrModule data={modules.ocr} onFindingSelect={onFindingSelect} />
          <TamperingModule data={modules.tampering} onFindingSelect={onFindingSelect} />
          <SignatureModule data={modules.signature} evidenceId={evidenceId} onFindingSelect={onFindingSelect} />
          <DeepfakeModule data={modules.deepfake} onFindingSelect={onFindingSelect} />
          <MetadataModule data={modules.metadata} />
        </div>
      </section>

      <section className="forge-evidence-gallery" aria-labelledby="evidence-gallery-title">
        <div className="forge-section-heading">
          <div>
            <h2 id="evidence-gallery-title">Evidence gallery</h2>
            <p>Recorded visual artifacts from the examination</p>
          </div>
        </div>
        {gallery.length > 0 ? (
          <div className="forge-gallery-grid">
            {gallery.map((item) => (
              <a href={item.url} target="_blank" rel="noreferrer" key={item.label} className="forge-gallery-item">
                <img src={item.url} alt={`${item.label} evidence artifact`} />
                <span>{item.label}</span>
              </a>
            ))}
          </div>
        ) : (
          <div className="forge-module-empty">
            <Image className="h-4 w-4" />
            <span>No recorded visual evidence artifacts are available.</span>
          </div>
        )}
      </section>
      <ExplainableFindings result={result} onFindingSelect={onFindingSelect} />
    </>
  );
}
