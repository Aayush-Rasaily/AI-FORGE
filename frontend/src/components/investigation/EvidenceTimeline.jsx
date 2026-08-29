import {
  CheckCircle2,
  Clock3,
  FileCheck2,
  Fingerprint,
  SearchCheck,
} from "lucide-react";

import { toInvestigatorText } from "./investigatorPresentation";

const TECHNICAL_EVENTS = new Set([
  "prepare_image",
  "quick_scan",
  "deep_scan",
  "text_detect",
  "texture",
  "total",
  "module",
]);

const FINDING_EVENTS = {
  "Image Replacement": "Potential image replacement identified",
  "Signature Insertion": "Signature inconsistency identified",
  "Amount Modification": "Financial value modification identified",
  "Date Modification": "Date modification identified",
  "Metadata Anomaly": "Metadata anomaly identified",
  "Text Modification": "Text modification identified",
  "Font Inconsistency": "Font inconsistency identified",
  "OCR Mismatch": "Text inconsistency identified",
  "Compression Anomaly": "Compression anomaly identified",
  "Layout Manipulation": "Layout inconsistency identified",
  "Logo Replacement": "Potential logo replacement identified",
  "Visual Anomaly": "Visual inconsistency identified",
};

function eventIcon(type) {
  const value = String(type || "").toLowerCase();
  if (value.includes("complete")) return CheckCircle2;
  if (value.includes("hash") || value.includes("integrity")) return Fingerprint;
  if (value.includes("received") || value.includes("created")) return FileCheck2;
  return SearchCheck;
}

function eventTitle(event) {
  const value = String(
    event?.event || event?.type || event?.event_type || event?.action || ""
  ).toLowerCase();
  if (value.includes("upload") || value.includes("intake") || value.includes("register")) {
    return "Evidence received";
  }
  if (value.includes("document") && value.includes("creat")) return "Document created";
  if (value.includes("metadata") && value.includes("modif")) return "Metadata modified";
  if (value.includes("hash") || value.includes("integrity")) return "Evidence integrity recorded";
  if (value.includes("analysis") && value.includes("complete")) {
    return "Forensic analysis completed";
  }
  if (value.includes("custody") || value.includes("transfer")) return "Custody event recorded";
  return toInvestigatorText(
    event?.event || event?.action_description || event?.description,
    ""
  );
}

function normalizeBackendEvents(events, evidenceId) {
  return (Array.isArray(events) ? events : [])
    .filter(Boolean)
    .filter((event) => {
      const module = String(event.module || event.type || "").toLowerCase();
      return !TECHNICAL_EVENTS.has(module);
    })
    .map((event, index) => {
      const title = eventTitle(event);
      if (!title) return null;
      return {
        id: event.id || event.event_id || `recorded-${evidenceId}-${index}`,
        timestamp:
          event.timestamp ||
          event.event_timestamp ||
          event.created_at ||
          event.time ||
          null,
        event: title,
        evidence: toInvestigatorText(
          event.relevant_evidence ||
            event.action_description ||
            event.description ||
            event.detail ||
            event.message,
          `Evidence ${evidenceId}`
        ),
        location:
          event.location ||
          (event.page || event.page_number
            ? `Page ${event.page || event.page_number}`
            : ""),
      };
    })
    .filter(Boolean);
}

function findingEvents(findings, timestamp) {
  return findings.map((finding) => ({
    id: `finding-event-${finding.id}`,
    timestamp: finding.timestamp || finding.generated_at || timestamp || null,
    event: FINDING_EVENTS[finding.category] || "Evidence concern identified",
    evidence: finding.explanation,
    location: [
      finding.page ? `Page ${finding.page}` : "",
      finding.location !== "Document-wide finding" ? finding.location : "",
    ]
      .filter(Boolean)
      .join(" · "),
  }));
}

function EvidenceTimeline({
  events = [],
  evidenceId,
  findings = [],
  investigationTimestamp,
  analysisCompleted = false,
}) {
  const normalized = [
    ...normalizeBackendEvents(events, evidenceId),
    ...findingEvents(findings, investigationTimestamp),
  ];
  if (
    analysisCompleted &&
    !normalized.some((event) => event.event === "Forensic analysis completed")
  ) {
    normalized.push({
      id: `analysis-completed-${evidenceId}`,
      timestamp: investigationTimestamp || null,
      event: "Forensic analysis completed",
      evidence: `${findings.length} investigation finding${
        findings.length === 1 ? "" : "s"
      } recorded.`,
      location: "",
    });
  }

  const unique = normalized
    .filter(
      (event, index, list) =>
        list.findIndex(
          (candidate) =>
            candidate.event === event.event &&
            candidate.evidence === event.evidence &&
            candidate.location === event.location
        ) === index
    )
    .sort((a, b) => {
      if (!a.timestamp && !b.timestamp) return 0;
      if (!a.timestamp) return 1;
      if (!b.timestamp) return -1;
      return new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
    });

  if (unique.length === 0) {
    return (
      <div className="forge-empty-result">
        <Clock3 className="h-5 w-5" />
        <div>
          <strong>No evidential timeline available</strong>
          <p>No document activity or supported investigation events were recorded.</p>
        </div>
      </div>
    );
  }

  return (
    <ol className="forge-timeline">
      {unique.map((event) => {
        const Icon = eventIcon(event.event);
        return (
          <li key={event.id}>
            <span className="forge-timeline-marker">
              <Icon className="h-3.5 w-3.5" />
            </span>
            <div className="forge-timeline-content">
              <div className="forge-timeline-heading">
                <strong>{event.event}</strong>
                <time dateTime={event.timestamp || undefined}>
                  {event.timestamp
                    ? new Date(event.timestamp).toLocaleString()
                    : "Time not recorded"}
                </time>
              </div>
              <dl className="forge-timeline-details">
                <div>
                  <dt>Relevant evidence</dt>
                  <dd>{event.evidence}</dd>
                </div>
                {event.location && (
                  <div>
                    <dt>Page / location</dt>
                    <dd>{event.location}</dd>
                  </div>
                )}
              </dl>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

export default EvidenceTimeline;
