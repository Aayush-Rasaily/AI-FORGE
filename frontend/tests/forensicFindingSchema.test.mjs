import assert from "node:assert/strict";
import test from "node:test";

import {
  buildCanonicalFindings,
  buildOverallConclusion,
  computeEvidenceSeverity,
  normalizeFindingBbox,
} from "../src/components/forensic-evidence-viewer/forensicFindingSchema.js";

test("canonical backend findings retain evidence and traceability", () => {
  const findings = buildCanonicalFindings({
    evidenceId: "EVID-TEST",
    mediaType: "document",
    apiFindings: [{
      finding_id: "FF-TRACEABLE",
      title: "Amount appears modified",
      type: "invoice_amount",
      verdict: "Likely manipulated",
      severity: "HIGH",
      confidence: 0.94,
      page: 2,
      location: "Amount field",
      bbox: {
        x: 100,
        y: 200,
        width: 80,
        height: 30,
        coordinate_space: "pixels",
        source_width: 1000,
        source_height: 1200,
      },
      observed_evidence: [
        "Character spacing differs from adjacent financial values.",
      ],
      short_explanation: "The recorded difference warrants source comparison.",
      detailed_explanation: "The displayed value contains a supported rendering inconsistency.",
      potential_impact: "May affect the reliability of the stated amount.",
      recommended_review: "Compare with the issuer record.",
      evidence_chain: [{
        evidence_id: "EVID-TEST",
        source_artifact: "ocr_difference_report.json",
        method: "ocr_document_intelligence",
        sha256: "a".repeat(64),
      }],
    }],
  });

  assert.equal(findings.length, 1);
  assert.equal(findings[0].findingId, "FF-TRACEABLE");
  assert.equal(findings[0].confidence, 94);
  assert.deepEqual(findings[0].observedEvidence, [
    "Character spacing differs from adjacent financial values.",
  ]);
  assert.equal(findings[0].bbox.coordinateSpace, "normalized");
  assert.equal(findings[0].evidenceChain.hash, "a".repeat(64));
});

test("severity reflects impact rather than confidence", () => {
  assert.equal(computeEvidenceSeverity("invoice_amount"), "HIGH");
  assert.equal(computeEvidenceSeverity("metadata_anomaly"), "MEDIUM");
  assert.equal(
    computeEvidenceSeverity("inserted_signature", { isLegalDocument: true }),
    "CRITICAL"
  );
});

test("unsupported findings are not manufactured", () => {
  const findings = buildCanonicalFindings({
    evidenceId: "EVID-TEST",
    apiFindings: [{
      finding_id: "FF-EMPTY",
      type: "visual_anomaly",
      confidence: 0.99,
      evidence_chain: [{ evidence_id: "EVID-TEST", method: "unknown" }],
    }],
  });
  assert.deepEqual(findings, []);
  assert.equal(
    buildOverallConclusion(findings).overallVerdict,
    "INSUFFICIENT EVIDENCE"
  );
});

test("zero-area geometry is withheld", () => {
  assert.equal(normalizeFindingBbox({ bbox: [0, 0, 0, 0] }), null);
});

test("video findings retain exact frame and timestamp navigation", () => {
  const [finding] = buildCanonicalFindings({
    evidenceId: "VIDEO-1",
    mediaType: "video",
    apiFindings: [{
      finding_id: "FF-VIDEO",
      type: "duplicate_frame",
      severity: "MEDIUM",
      confidence: 0.81,
      frame: 450,
      time_seconds: 15,
      bbox: {
        x: 0.1,
        y: 0.2,
        width: 0.3,
        height: 0.4,
        coordinate_space: "normalized",
      },
      observed_evidence: ["A repeated frame sequence was recorded at this time."],
      short_explanation: "The repeated sequence warrants adjacent-frame review.",
      evidence_chain: [{ evidence_id: "VIDEO-1", method: "video" }],
    }],
  });
  assert.equal(finding.frame, 450);
  assert.equal(finding.timestamp, 15);
  assert.equal(finding.bbox.coordinateSpace, "normalized");
});

test("reference comparison values are normalized without authenticity assumptions", () => {
  const [finding] = buildCanonicalFindings({
    evidenceId: "EVID-EXAM",
    apiFindings: [{
      finding_id: "FF-COMPARE",
      type: "reference_value_difference",
      severity: "MEDIUM",
      confidence: 0.8,
      observed_evidence: ["The corresponding recorded values differ."],
      short_explanation: "The difference requires independent verification.",
      original_comparison: {
        reference_or_expected: "100.00",
        examined: "900.00",
      },
      evidence_chain: [
        { evidence_id: "EVID-EXAM", method: "reference_field_comparison" },
        { evidence_id: "EVID-REF", method: "reference_field_comparison" },
      ],
    }],
  });
  assert.equal(finding.originalComparison.available, true);
  assert.equal(finding.originalComparison.original, "100.00");
  assert.equal(finding.originalComparison.examined, "900.00");
  assert.equal(finding.evidenceChain.records.length, 2);
});

test("canonical empty findings remain authoritative over legacy fallback", () => {
  const findings = buildCanonicalFindings({
    evidenceId: "EVID-EMPTY",
    apiFindings: [],
    analysisResult: {
      analysis: {
        findings: ["A legacy-only anomaly was recorded."],
      },
    },
  });
  assert.deepEqual(findings, []);
});

test("findings answer what, where, what changed, why, and supporting evidence", () => {
  const [finding] = buildCanonicalFindings({
    evidenceId: "EVID-TEST",
    mediaType: "document",
    apiFindings: [{
      finding_id: "FF-FIVE",
      title: "The total amount appears to have been modified.",
      type: "financial_character_insertion",
      field: "Total Amount",
      verdict: "Likely manipulated",
      severity: "HIGH",
      confidence: 0.91,
      page: 1,
      location: "Page 1 · Premium Schedule · Total Amount",
      observed_evidence: [
        "Character spacing and rendering differ from surrounding financial values.",
      ],
      short_explanation: "The highlighted amount is inconsistent with adjacent typography.",
      original_comparison: {
        reference_or_expected: "2000",
        examined: "20000",
      },
      evidence_chain: [{ evidence_id: "EVID-TEST", method: "ocr_document_intelligence" }],
    }],
  });
  assert.match(finding.title, /total amount appears to have been modified/i);
  assert.match(finding.location, /Premium Schedule/i);
  assert.match(finding.whatChanged, /2000/);
  assert.match(finding.whatChanged, /20000/);
  assert.equal(finding.why, finding.explanation);
  assert.equal(finding.supportingEvidence[0], finding.observedEvidence[0]);
  const conclusion = buildOverallConclusion([finding]);
  assert.equal(conclusion.primaryFindings[0].title, finding.title);
});

test("null location and evidence entries do not crash normalization", () => {
  assert.doesNotThrow(() =>
    buildCanonicalFindings({
      evidenceId: "EVID-NULL-SHAPE",
      apiFindings: [{
        finding_id: "SIG-NULL-LOCATION",
        type: "signature",
        location: null,
        evidence: [null],
        confidence: 0.7,
      }],
    })
  );
});

