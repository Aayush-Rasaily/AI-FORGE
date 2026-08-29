import { formatEvidenceTimestamp } from "./forensicFindingSchema";

function locationLabel(region) {
  if (region.page) return `Page ${region.page}`;
  const stamped = formatEvidenceTimestamp(region.timestamp);
  if (stamped) return stamped;
  if (region.frame != null) return `Frame ${region.frame}`;
  return "Location not specified";
}

export default function EvidencePanel({ region, isSelected }) {
  if (!region) return null;
  const comparison = region.originalComparison;
  const reviewActions = Array.isArray(region.recommendedReview)
    ? region.recommendedReview
    : [region.recommendedReview].filter(Boolean);
  const chain = region.evidenceChain || {};
  const observations = Array.isArray(region.supportingEvidence || region.observedEvidence)
    ? region.supportingEvidence || region.observedEvidence
    : [region.observedEvidence].filter(Boolean);
  const findingNumber = String(region.displayNumber || region.number || 1).padStart(2, "0");

  return (
    <div className="forge-finding-record">
      <div className="forge-finding-record-heading">
        <div>
          <span>{region.findingId || `Finding ${findingNumber}`}</span>
          <strong>{region.title}</strong>
        </div>
        <span
          className={`forge-severity forge-severity-${String(
            region.severity || "not-rated"
          ).toLowerCase().replace(/\s+/g, "-")}`}
        >
          {region.severity || "Not rated"}
        </span>
      </div>

      <div className="forge-finding-reference">
        <span>{locationLabel(region)}</span>
        <span aria-hidden="true">·</span>
        <span>{region.location}</span>
      </div>

      <dl className="forge-finding-facts">
        <div>
          <dt>Verdict</dt>
          <dd>{region.verdict || "Requires review"}</dd>
        </div>
        <div>
          <dt>Evidence strength</dt>
          <dd>{region.severity || "Not recorded"}</dd>
        </div>
        <div>
          <dt>Severity</dt>
          <dd>{region.severity || "Not rated"}</dd>
        </div>
      </dl>

      <div className="forge-finding-narrative">
        <div>
          <span>What is suspicious</span>
          <p>{region.title}</p>
        </div>
        <div>
          <span>Where</span>
          <p>{[locationLabel(region), region.location].filter(Boolean).join(" · ")}</p>
        </div>
        <div>
          <span>Observation</span>
          <p>{region.whatChanged || observations[0] || "The highlighted region differs from surrounding content."}</p>
        </div>
        <div>
          <span>Technical reason</span>
          <p>{region.why || region.explanation}</p>
        </div>
        <div>
          <span>Supporting evidence</span>
          {observations.length > 1 ? (
            <ul>
              {observations.map((observation) => (
                <li key={observation}>{observation}</li>
              ))}
            </ul>
          ) : (
            <p>{observations[0] || "No supporting observation was recorded."}</p>
          )}
        </div>
        {comparison?.available && (
          <div>
            <span>Comparison with original / reference</span>
            {comparison.original != null && comparison.examined != null && (
              <p>
                Reference: {comparison.original} · Examined: {comparison.examined}
              </p>
            )}
            <p>{comparison.explanation}</p>
          </div>
        )}
        <div>
          <span>Potential impact</span>
          <p>{region.potentialImpact}</p>
        </div>
        <div>
          <span>Recommendation</span>
          {reviewActions.length > 1 ? (
            <ul>
              {reviewActions.map((action) => <li key={action}>{action}</li>)}
            </ul>
          ) : (
            <p>{reviewActions[0] || region.recommendation}</p>
          )}
        </div>
      </div>

      <span className="forge-view-evidence">View evidence</span>

      <details
        className="forge-finding-trace"
        onClick={(event) => event.stopPropagation()}
      >
        <summary>Traceability</summary>
        <dl>
          <div><dt>Finding ID</dt><dd>{region.findingId}</dd></div>
          <div><dt>Evidence ID</dt><dd>{chain.evidenceId || "Not recorded"}</dd></div>
          <div><dt>Source</dt><dd>{chain.sourceFile || "Submitted evidence"}</dd></div>
          <div>
            <dt>Location</dt>
            <dd>
              {[
                region.page != null ? `Page ${region.page}` : null,
                region.frame != null ? `Frame ${region.frame}` : null,
                region.timestamp != null ? formatEvidenceTimestamp(region.timestamp) : null,
              ].filter(Boolean).join(" · ") || "Not recorded"}
            </dd>
          </div>
          <div><dt>Methods</dt><dd>{(chain.analysisMethod || []).join(", ") || "Not recorded"}</dd></div>
          {chain.hash && <div><dt>Source hash</dt><dd>{chain.hash}</dd></div>}
        </dl>
      </details>

      {isSelected && <span className="sr-only">Selected finding. This is the evidence region.</span>}
    </div>
  );
}
