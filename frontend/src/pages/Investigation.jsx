import { useCallback, useEffect, useState } from "react";
import { FileSearch, Loader2, RefreshCw } from "lucide-react";
import { useSearchParams } from "react-router-dom";

import AppLayout from "../components/layout/AppLayout";
import EvidenceUploader from "../components/EvidenceUploader";
import InvestigationWorkspace from "../components/investigation/InvestigationWorkspace";
import { useBackend } from "../context/BackendConnectivity";
import {
  createCase,
  getInvestigation,
  getExplainableAI,
  getInvestigationSummary,
  getStoredReport,
  getTimeline,
  listRecentEvidence,
  runJuryAnalysis,
} from "../services/api";

function mediaTypeOf(payload, evidence) {
  const value = String(
    payload?.plan?.evidence_type || evidence?.media_type || "document"
  ).toLowerCase();
  if (value.includes("video")) return "video";
  if (value.includes("signature")) return "signature";
  if (value.includes("image")) return "image";
  return "document";
}

function normalizePersistedInvestigation(payload, evidence, timeline) {
  const evidenceId = payload?.evidence_id || evidence?.evidence_id;
  const dossier = payload?.forensic_dossier || payload?.dossier || payload || {};
  const storedJury =
    payload?.ai_jury ||
    dossier?.ai_jury ||
    payload?.jury?.ai_jury ||
    payload?.jury?.experts ||
    null;
  const juryExperts =
    payload?.jury_experts ||
    dossier?.jury_experts ||
    storedJury?.experts ||
    payload?.jury?.experts ||
    payload?.jury?.jury_experts ||
    null;
  const juryConsensus =
    payload?.jury_consensus ||
    dossier?.jury_consensus ||
    storedJury?.consensus ||
    payload?.jury?.consensus ||
    payload?.jury?.jury_consensus ||
    null;
  return {
    evidenceId,
    caseId: evidence?.investigation_id || payload?.investigation_id || null,
    filename:
      payload?.filename ||
      payload?.original_filename ||
      evidence?.original_filename ||
      evidenceId,
    fileType: mediaTypeOf(payload, evidence),
    status: payload?.status === "failed" ? "failed" : "completed",
    analysis: payload?.analysis || dossier?.analysis || {},
    tampering:
      payload?.tampering ||
      dossier?.document_tampering ||
      {},
    dashboard: payload?.dashboard || {},
    jury: {
      ...(payload?.jury || {}),
      ...(juryExperts ? { jury_experts: juryExperts } : {}),
      ...(juryConsensus ? { jury_consensus: juryConsensus } : {}),
    },
    juryConsensus,
    forensicDossier: dossier,
    explainableAI:
      payload?.explainable_ai ||
      payload?.analysis?.explainable_ai ||
      dossier?.explainable_ai ||
      null,
    investigationSummary:
      payload?.investigation_summary ||
      dossier?.investigation_summary ||
      null,
    documentAnalysis: payload?.document_analysis || dossier?.document_analysis || null,
    signatureResult:
      payload?.signature_result ||
      dossier?.signature_analysis ||
      dossier?.signature_verification ||
      null,
    deepfakeAnalysis:
      payload?.deepfake_analysis ||
      payload?.video_analysis?.deepfake_analysis ||
      dossier?.deepfake_analysis ||
      null,
    metadata:
      payload?.metadata ||
      payload?.analysis?.metadata ||
      dossier?.metadata ||
      dossier?.metadata_analysis ||
      null,
    investigation: payload || {},
    verdict: payload?.verdict,
    risk: payload?.risk || {
      score: payload?.risk_score,
      level: payload?.risk_level,
    },
    confidence: payload?.confidence,
    explanation: payload?.explanation,
    agents: payload?.agents || {},
    timeline,
    artifacts: {
      ...(payload?.artifacts || {}),
      ...(dossier?.overlay_files || {}),
    },
    reportsPending: payload?.reports_pending ?? false,
    hashes: {
      sha256: evidence?.sha256,
      sha512: evidence?.sha512,
    },
    intakeTimestamp:
      evidence?.intake_timestamp || payload?.created_at || payload?.completed_at,
  };
}

function Investigation() {
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedEvidenceId = searchParams.get("evidence");
  const requestedCaseId = searchParams.get("case");
  const requestedNew = searchParams.get("new") === "1";
  const analysisMode = searchParams.get("mode");
  const analysisType =
    analysisMode === "document" ? "document" : analysisMode === "image" ? "image" : "investigate";
  const { backendOnline, status: backendStatus, reconnect } = useBackend();
  const [activeResult, setActiveResult] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [evidenceCount, setEvidenceCount] = useState(1);
  const [activeCaseId, setActiveCaseId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [showIntake, setShowIntake] = useState(false);
  const [files, setFiles] = useState([]);
  const [processing, setProcessing] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [caseName, setCaseName] = useState("");
  const [investigator, setInvestigator] = useState("");
  const [caseDescription, setCaseDescription] = useState("");

  const hydrate = useCallback(
    async (evidenceId, evidenceMeta = null, inventory = []) => {
      const [basePayload, timelineResponse, xai, summary] =
        await Promise.all([
          getInvestigation(evidenceId).catch(() => getStoredReport(evidenceId)),
          getTimeline(evidenceId).catch(() => null),
          getExplainableAI(evidenceId).catch(() => null),
          getInvestigationSummary(evidenceId).catch(() => null),
        ]);
      const storedJury =
        basePayload?.ai_jury ||
        basePayload?.jury?.ai_jury ||
        basePayload?.jury_experts ||
        basePayload?.jury?.jury_experts ||
        basePayload?.jury_consensus ||
        basePayload?.jury?.jury_consensus;
      const dossierJury =
        storedJury
          ? null
          : await runJuryAnalysis({ evidenceId }).catch(() => null);
      const payload = {
        ...(basePayload || {}),
        jury: {
          ...(basePayload?.jury || {}),
          ...(dossierJury || {}),
        },
        explainable_ai: xai || basePayload?.explainable_ai,
        investigation_summary: summary || basePayload?.investigation_summary,
      };
      const timelineData =
        timelineResponse?.timeline ||
        timelineResponse?.events ||
        payload?.timeline ||
        [];
      const events = Array.isArray(timelineData)
        ? timelineData
        : [
            ...(Array.isArray(timelineData?.custody)
              ? timelineData.custody
              : []),
            ...(Array.isArray(timelineData?.events)
              ? timelineData.events
              : []),
            ...(Array.isArray(timelineData?.modules)
              ? timelineData.modules
              : []),
          ];
      const result = normalizePersistedInvestigation(
        payload,
        evidenceMeta,
        events
      );
      const caseId = result.caseId;
      setActiveResult(result);
      setTimeline(events);
      setActiveCaseId(caseId);
      setEvidenceCount(
        caseId
          ? Math.max(
              1,
              inventory.filter((item) => item.investigation_id === caseId).length
            )
          : 1
      );
      setShowIntake(false);
      return result;
    },
    []
  );

  const loadActiveInvestigation = useCallback(async () => {
    if (!backendOnline) {
      if (backendStatus !== "connecting") {
        setLoading(false);
        setLoadError("The forensic service is offline. Reconnect to load the active investigation.");
      }
      return;
    }

    if (!requestedEvidenceId && (requestedNew || analysisMode || requestedCaseId)) {
      setActiveResult(null);
      setShowIntake(true);
      setActiveCaseId(requestedCaseId || null);
      setLoading(false);
      setLoadError("");
      return;
    }

    setLoading(true);
    setLoadError("");
    try {
      const recentResponse = await listRecentEvidence(20);
      const inventory = Array.isArray(recentResponse?.evidence)
        ? recentResponse.evidence
        : [];

      if (requestedEvidenceId) {
        const metadata =
          inventory.find((item) => item.evidence_id === requestedEvidenceId) ||
          null;
        await hydrate(requestedEvidenceId, metadata, inventory);
        return;
      }

      for (const evidence of inventory) {
        try {
          await hydrate(evidence.evidence_id, evidence, inventory);
          return;
        } catch {
          // Registered evidence may not have completed investigation data yet.
        }
      }

      setActiveResult(null);
      setTimeline([]);
      setEvidenceCount(0);
      setShowIntake(true);
    } catch (error) {
      setLoadError(error?.message || "Unable to load the active investigation.");
      setShowIntake(true);
    } finally {
      setLoading(false);
    }
  }, [
    analysisMode,
    backendOnline,
    backendStatus,
    hydrate,
    requestedCaseId,
    requestedEvidenceId,
    requestedNew,
  ]);

  useEffect(() => {
    const timer = window.setTimeout(loadActiveInvestigation, 0);
    return () => window.clearTimeout(timer);
  }, [loadActiveInvestigation]);

  const ensureCaseId = useCallback(
    async (file) => {
      if (activeCaseId) return activeCaseId;
      const date = new Date().toLocaleDateString();
      const response = await createCase(
        caseName.trim() || `Investigation — ${file?.name || "New evidence"} — ${date}`,
        [
          caseDescription.trim() || "Investigation created from the forensic workspace.",
          investigator.trim() ? `Investigator: ${investigator.trim()}` : "",
        ].filter(Boolean).join("\n")
      );
      const caseId = response?.case?.id;
      if (!caseId) throw new Error("The investigation record was not created.");
      setActiveCaseId(caseId);
      return caseId;
    },
    [activeCaseId, caseDescription, caseName, investigator]
  );

  const handleAnalysisResults = useCallback(
    (results) => {
      const completed = (Array.isArray(results) ? results : []).find(
        (item) => item?.status === "completed" && item?.evidenceId
      );
      if (!completed) return;
      const result = {
        ...completed,
        caseId: completed.caseId || activeCaseId,
      };
      setActiveResult(result);
      setTimeline(result.timeline || []);
      setEvidenceCount(Math.max(1, results.length));
      setShowIntake(false);
      setSearchParams(
        { evidence: result.evidenceId },
        { replace: true }
      );
    },
    [activeCaseId, setSearchParams]
  );

  const startNewInvestigation = () => {
    setActiveResult(null);
    setTimeline([]);
    setActiveCaseId(null);
    setFiles([]);
    setUploadError("");
    setCaseName("");
    setInvestigator("");
    setCaseDescription("");
    setShowIntake(true);
    setSearchParams({ new: "1" }, { replace: true });
  };

  const intakeTitle =
    analysisMode === "document"
      ? "Document analysis"
      : analysisMode === "image"
        ? "Image analysis"
        : analysisMode === "video"
          ? "Video analysis"
          : "Start an investigation";

  return (
    <AppLayout
      title="Investigations"
      subtitle="Evidence examination and case review"
      contextLabel={
        activeResult && !showIntake
          ? activeResult.filename || activeResult.evidenceId
          : null
      }
    >
      {loading ? (
        <div className="forge-loading-state" role="status">
          <Loader2 className="h-5 w-5 animate-spin" />
          <div>
            <strong>Loading investigation</strong>
            <p>Retrieving the examination record.</p>
          </div>
        </div>
      ) : activeResult && !showIntake ? (
        <InvestigationWorkspace
          key={activeResult.evidenceId}
          result={activeResult}
          timeline={timeline}
          evidenceCount={evidenceCount}
          onNewInvestigation={startNewInvestigation}
        />
      ) : (
        <div className="mx-auto max-w-3xl">
          <div className="forge-empty-header">
            <FileSearch className="h-6 w-6" />
            <div>
              <h1>{intakeTitle}</h1>
              <p>
                Add evidence to begin a forensic examination. An investigation
                record will be created automatically.
              </p>
            </div>
          </div>

          {loadError && (
            <div className="forge-inline-error">
              <span>{loadError}</span>
              <button type="button" onClick={reconnect}>
                <RefreshCw className="h-3.5 w-3.5" />
                Retry
              </button>
            </div>
          )}

          <div className="forge-panel p-4 md:p-5">
            <div className="forge-intake-steps" aria-label="Investigation intake steps">
              <span className="forge-intake-step forge-intake-step-active"><b>01</b> Case information</span>
              <span className="forge-intake-step"><b>02</b> Evidence upload</span>
              <span className="forge-intake-step"><b>03</b> Evidence review</span>
              <span className="forge-intake-step"><b>04</b> Examination</span>
            </div>
            <div className="forge-intake-form">
              <label>
                <span>Case name</span>
                <input
                  value={caseName}
                  onChange={(event) => setCaseName(event.target.value)}
                  placeholder="e.g. Policy claim review"
                />
              </label>
              <label>
                <span>Case ID</span>
                <input value={activeCaseId || "Assigned on intake"} readOnly />
              </label>
              <label>
                <span>Investigator</span>
                <input
                  value={investigator}
                  onChange={(event) => setInvestigator(event.target.value)}
                  placeholder="Investigator name"
                />
              </label>
              <label className="forge-intake-form-wide">
                <span>Description</span>
                <textarea
                  value={caseDescription}
                  onChange={(event) => setCaseDescription(event.target.value)}
                  placeholder="Record the scope or reason for examination"
                  rows={2}
                />
              </label>
            </div>
            <EvidenceUploader
              analysisType={analysisType}
              files={files}
              setFiles={setFiles}
              processing={processing}
              setProcessing={setProcessing}
              setResults={handleAnalysisResults}
              error={uploadError}
              setError={setUploadError}
              caseId={activeCaseId}
              ensureCaseId={ensureCaseId}
            />
          </div>
        </div>
      )}
    </AppLayout>
  );
}

export default Investigation;
