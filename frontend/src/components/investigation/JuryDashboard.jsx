import {
  AlertTriangle,
  Eye,
  FileSearch,
  FileText,
  Fingerprint,
  LayoutPanelTop,
  Scale,
  ShieldCheck,
} from "lucide-react";

import {
  buildJurySummary,
} from "./investigatorPresentation";

const ICONS = {
  ocr_text: FileText,
  document_structure: LayoutPanelTop,
  vision: Eye,
  forgery: FileSearch,
  ocr: FileText,
  metadata: Fingerprint,
  signature: ShieldCheck,
  risk: Scale,
  image_forensics: FileSearch,
  signature_identity: ShieldCheck,
  deepfake_synthetic: Eye,
};

function verdictState(verdict) {
  const value = String(verdict || "").toLowerCase();
  if (["tamper", "manipulat", "forg", "suspicious", "risk", "review"].some((term) => value.includes(term))) {
    return "risk";
  }
  if (value.includes("not assessed") || value.includes("inconclusive")) {
    return "neutral";
  }
  return "safe";
}

function JuryDashboard({ juryResult = {}, findings = [], onFindingSelect }) {
  const dossierExperts = juryResult?.jury_experts || juryResult?.experts;
  const jurors = Array.isArray(dossierExperts) && dossierExperts.length > 0
    ? dossierExperts.map((expert) => ({
        id: expert.expert_id,
        name: expert.expert_name,
        verdict: expert.vote,
        confidence: expert.confidence == null ? null : Number(expert.confidence) * 100,
        reasoning: expert.reasoning || "Reasoning not available.",
        supportingFindings: expert.supporting_findings || [],
        contradictingFindings: expert.contradicting_findings || [],
      }))
    : [];
  const summary = buildJurySummary(jurors, findings);
  const consensus = juryResult?.jury_consensus || {};

  return (
    <div className="forge-jury-panel">
      {jurors.length > 0 ? (
      <div className="forge-jury-table-wrap">
        <table className="forge-jury-table">
          <thead>
            <tr>
              <th scope="col">Expert</th>
              <th scope="col">Vote</th>
              <th scope="col">Reason</th>
              <th scope="col">Confidence</th>
            </tr>
          </thead>
          <tbody>
            {jurors.map((juror, index) => {
              const Icon = ICONS[juror.id] || Scale;
              const state = verdictState(juror.verdict);
              const references = [
                ...(juror.supportingFindings || []),
                ...(juror.contradictingFindings || []),
              ];
              return (
                <tr key={juror.id || `expert-${index}`}>
                  <td>
                    <span className="forge-jury-expert">
                      <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                      {juror.name}
                    </span>
                  </td>
                  <td>
                    <span className={`forge-juror-status forge-juror-status-${state}`}>
                      {juror.verdict || "INCONCLUSIVE"}
                    </span>
                  </td>
                  <td>
                    <p className="forge-jury-reason">{juror.reasoning}</p>
                    {references.length > 0 && (
                      <div className="forge-jury-references">
                        {references.map((findingId) => (
                          <button
                            key={findingId}
                            type="button"
                            className="forge-juror-evidence-link"
                            onClick={() => onFindingSelect?.(findingId)}
                          >
                            {findingId}
                          </button>
                        ))}
                      </div>
                    )}
                  </td>
                  <td>{juror.confidence == null ? "Not recorded" : `${Math.round(juror.confidence)}%`}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      ) : (
        <div className="forge-empty-result">
          <p>No dossier-backed Jury assessment was recorded for this investigation.</p>
        </div>
      )}

      <div className="forge-jury-decision">
        <div>
          <span className="forge-label">Consensus assessment</span>
          <strong>
            {consensus.final_verdict || juryResult.final_verdict || "INCONCLUSIVE"}
          </strong>
          <p>
            {consensus.consensus_level || "INCONCLUSIVE"} consensus ·{" "}
            {consensus.agreement_percentage == null ? "Agreement not recorded" : `${consensus.agreement_percentage}% agreement`}
          </p>
        </div>
        <div>
          <span className="forge-label">Consensus reasoning</span>
          {consensus.final_reasoning ? (
            <p>{consensus.final_reasoning}</p>
          ) : summary.concerns.length > 0 ? (
            <ul>{summary.concerns.map((concern) => <li key={concern}>{concern}</li>)}</ul>
          ) : (
            <p><AlertTriangle className="mr-1 inline h-3.5 w-3.5" />Consensus data unavailable.</p>
          )}
        </div>
      </div>
    </div>
  );
}

export default JuryDashboard;
