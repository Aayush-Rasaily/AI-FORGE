import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Plus,
  ShieldAlert,
} from "lucide-react";

import ForensicEvidenceViewer from "../forensic-evidence-viewer";
import {
  buildCanonicalFindings,
  buildOverallConclusion,
} from "../forensic-evidence-viewer/forensicFindingSchema";
import JuryDashboard from "./JuryDashboard";
import EvidenceTimeline from "./EvidenceTimeline";
import ExportReportPanel from "./ExportReportPanel";
import InvestigationEvidenceModules from "./InvestigationEvidenceModules";
import { getEvidenceFindings } from "../../services/api";

function Section({ number, title, description, children, id }) {
  return (
    <section id={id} className="forge-workspace-section" aria-labelledby={`${id}-title`}>
      <div className="forge-section-heading">
        <span className="forge-section-number">{String(number).padStart(2, "0")}</span>
        <div>
          <h2 id={`${id}-title`}>{title}</h2>
          {description && <p>{description}</p>}
        </div>
      </div>
      {children}
    </section>
  );
}

function InvestigationWorkspace({
  result,
  evidenceCount = 1,
  timeline = [],
  onNewInvestigation,
}) {
  const [findingsState, setFindingsState] = useState({
    evidenceId: null,
    response: null,
  });
  const [signatureFocusId, setSignatureFocusId] = useState(null);

  const investigation = result?.investigation || {};
  const jury = result?.jury || investigation?.jury || {};
  const juryData = {
    ...jury,
    agents: jury?.agents || result?.agents || investigation?.agents || {},
  };
  const juryConsensus = result?.juryConsensus || jury?.jury_consensus || jury?.juryConsensus || {};
  const narrative =
    result?.explainableAI?.overall_narrative ||
    result?.explainableAI?.investigation_summary?.overall_narrative ||
    result?.investigationSummary?.overall_narrative ||
    result?.analysis?.explainable_ai?.overall_narrative ||
    "";
  const evidenceId = result?.evidenceId || investigation?.evidence_id || null;
  const mediaType =
    result?.fileType ||
    investigation?.plan?.evidence_type ||
    investigation?.media_type ||
    "document";

  const refreshFindings = useCallback(() => {
    if (!evidenceId) {
      return { request: Promise.resolve(), cancel: () => {} };
    }
    let active = true;
    const request = getEvidenceFindings(evidenceId)
      .then((response) => {
        if (active) setFindingsState({ evidenceId, response });
      })
      .catch(() => {
        if (active) setFindingsState({ evidenceId, response: null });
      });
    return { request, cancel: () => { active = false; } };
  }, [evidenceId]);

  useEffect(() => {
    const operation = refreshFindings();
    return operation.cancel;
  }, [refreshFindings]);

  const investigatorFindings = useMemo(
    () => buildCanonicalFindings({
      apiFindings:
        findingsState.evidenceId === evidenceId &&
        Array.isArray(findingsState.response?.findings)
          ? findingsState.response.findings
          : undefined,
      analysisResult: result,
      evidenceId,
      mediaType,
    }),
    [evidenceId, findingsState, mediaType, result]
  );
  const forensicConclusion = useMemo(
    () => buildOverallConclusion(investigatorFindings, null, null),
    [investigatorFindings]
  );

  const verdict =
    juryConsensus.final_verdict ||
    jury?.final_verdict ||
    jury?.fusion?.final_verdict ||
    forensicConclusion.overallVerdict;
  const riskLevelRaw =
    String(juryConsensus.risk_level || jury?.risk_level || "").toUpperCase() ||
    (["critical", "high"].includes(forensicConclusion.verdictLevel)
      ? "HIGH"
      : forensicConclusion.verdictLevel === "medium"
        ? "MEDIUM"
        : forensicConclusion.verdictLevel === "inconclusive"
          ? "NOT DETERMINED"
          : "LOW");
  const riskLevel = riskLevelRaw.replace(/\s+RISK$/, "");
  const elevated = ["CRITICAL", "HIGH", "HIGH RISK", "MANIPULATED"].includes(riskLevel);
  const caution = ["MEDIUM", "SUSPICIOUS"].includes(riskLevel);
  const inconclusive =
    !verdict ||
    String(verdict).toLowerCase().includes("inconclusive") ||
    String(verdict).toLowerCase().includes("not determined");
  const verdictLabel = elevated
    ? "HIGH RISK DOCUMENT"
    : caution
      ? "REVIEW REQUIRED"
      : inconclusive
        ? "ASSESSMENT INCONCLUSIVE"
        : "LOW RISK DOCUMENT";
  const evidenceStrength =
    juryConsensus.consensus_level ||
    (investigatorFindings.some((finding) => ["critical", "high"].includes(String(finding.severity).toLowerCase()))
      ? "HIGH"
      : investigatorFindings.length > 0
        ? "MEDIUM"
        : "NOT DETERMINED");
  const filename =
    result?.filename ||
    investigation?.filename ||
    investigation?.original_filename ||
    "Unnamed evidence";
  const timestamp =
    result?.intakeTimestamp ||
    investigation?.completed_at ||
    investigation?.created_at ||
    timeline?.[0]?.timestamp ||
    timeline?.[0]?.event_timestamp;
  const explanation = narrative || forensicConclusion.combinedAssessment;

  return (
    <div className="forge-workspace">
      <Section
        number={1}
        id="investigation-summary"
        title="Investigation Summary"
        description="Active evidence and examination status"
      >
        <div className="forge-inv-header">
          {[
            ["Investigation ID", investigation?.investigation_id || result?.caseId || evidenceId || "Not recorded"],
            ["Document", filename],
            ["Status", result?.status === "completed" ? "Analysis complete" : result?.status || "Complete"],
            ["Analysis timestamp", timestamp ? new Date(timestamp).toLocaleString() : "Not recorded"],
            ["Evidence count", evidenceCount],
            ["Overall risk", riskLevel],
          ].map(([label, value]) => (
            <div className="forge-inv-header-item" key={label}>
              <span className="forge-inv-header-label">{label}</span>
              <span className="forge-inv-header-value">{value}</span>
            </div>
          ))}
          <button
            type="button"
            className="forge-secondary-action"
            onClick={onNewInvestigation}
          >
            <Plus className="h-3.5 w-3.5" />
            New evidence
          </button>
        </div>
      </Section>

      <Section
        number={2}
        id="overall-verdict"
        title="Overall Verdict"
        description="Consolidated forensic assessment"
      >
        <div
          className={`forge-verdict-panel forge-verdict-enter ${
            elevated
              ? "forge-verdict-danger"
              : inconclusive || caution
                ? "forge-verdict-warning"
                : "forge-verdict-safe"
          }`}
        >
          <div className="forge-verdict-icon" aria-hidden="true">
            {elevated ? (
              <ShieldAlert />
            ) : inconclusive ? (
              <AlertTriangle />
            ) : (
              <CheckCircle2 />
            )}
          </div>
          <div className="min-w-0 flex-1">
            <div className="forge-verdict-topline">
            <strong>{verdictLabel}</strong>
              <span>{verdict || "Verdict not recorded"}</span>
            </div>
            <p>{explanation}</p>
            {forensicConclusion.primaryFindings?.length > 0 && (
              <ol className="forge-verdict-findings">
                {forensicConclusion.primaryFindings.map((item) => (
                  <li key={item.findingId || item.number}>{item.title}</li>
                ))}
              </ol>
            )}
            <div className="forge-verdict-meta">
              <span>{investigatorFindings.length} evidence finding(s)</span>
              <span className="forge-confidence">Evidence strength: {evidenceStrength}</span>
            </div>
          </div>
        </div>
      </Section>

      <Section
        number={3}
        id="forensic-summary"
        title="Forensic Summary"
        description="Human-readable examination narrative"
      >
        <div className="forge-narrative-panel">
          <p>{narrative || "Investigation summary unavailable."}</p>
        </div>
      </Section>

      <InvestigationEvidenceModules
        evidenceId={evidenceId}
        result={result}
        onFindingSelect={(findingId) => {
          setSignatureFocusId(findingId);
          document.getElementById("document-viewer")?.scrollIntoView({
            behavior: "smooth",
            block: "start",
          });
        }}
      />

      <Section
        number={4}
        id="expert-jury"
        title="AI Jury"
        description="Independent specialist assessments for this evidence"
      >
        <JuryDashboard
          juryResult={juryData}
          analysisResult={result}
          findings={investigatorFindings}
          onFindingSelect={(findingId) => {
            setSignatureFocusId(findingId);
            document.getElementById("document-viewer")?.scrollIntoView({ behavior: "smooth" });
          }}
        />
      </Section>

      <ForensicEvidenceViewer
        evidenceId={evidenceId}
        analysisResult={result}
        mediaType={mediaType}
        findings={investigatorFindings}
        focusFindingId={signatureFocusId}
        onEvidenceChanged={() => refreshFindings().request}
        renderSection={(section, content) => (
          <Section
            number={section === "findings" ? 5 : 6}
            id={section === "findings" ? "evidence-findings" : "document-viewer"}
            title={section === "findings" ? "Evidence Findings" : "Interactive Evidence Viewer"}
            description={
              section === "findings"
                ? "Localized observations requiring investigator review"
                : "Select a finding to inspect its location in the evidence"
            }
          >
            {content}
          </Section>
        )}
      />

      <Section
        number={7}
        id="evidence-timeline"
        title="Evidence Timeline"
        description="Recorded examination and custody activity"
      >
        <EvidenceTimeline
          events={timeline}
          evidenceId={evidenceId}
          findings={investigatorFindings}
          investigationTimestamp={timestamp}
          analysisCompleted={Boolean(
            result &&
              (result.status === "completed" ||
                result.verdict ||
                result.analysis ||
                result.investigation)
          )}
        />
      </Section>

      <Section
        number={8}
        id="download-reports"
        title="Download Reports"
        description="Professional investigation reports for review and disclosure"
      >
        <ExportReportPanel
          evidenceId={evidenceId}
          reportsPending={result?.reportsPending ?? false}
        />
      </Section>
    </div>
  );
}

export default InvestigationWorkspace;
