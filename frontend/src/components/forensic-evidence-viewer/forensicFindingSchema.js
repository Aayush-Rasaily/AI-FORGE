/**
 * forensicFindingSchema.js
 *
 * Canonical 17-field forensic finding normalizer for AI-FORGE.
 *
 * PURPOSE
 * ──────────────────────────────────────────────────────────────────────
 * The backend produces findings in different shapes depending on the
 * analysis path (image, document, video, signature, jury).
 * This module normalizes any raw region/finding object into the
 * standardized forensic finding format — the single authoritative
 * structure used by all UI components.
 *
 * FORENSIC PRINCIPLE
 * ──────────────────────────────────────────────────────────────────────
 * Severity reflects investigative importance, NOT model confidence.
 * A modified financial amount on an invoice is HIGH regardless of
 * whether the model is 55% or 95% confident.
 *
 * LANGUAGE GUARDRAIL
 * ──────────────────────────────────────────────────────────────────────
 * All generated text uses evidence-based hedging:
 *   "appears", "indicates", "suggests", "consistent with",
 *   "inconsistent with", "likely", "cannot be conclusively determined"
 *
 * Never claims:
 *   - A specific person manipulated the document
 *   - A specific software was used without metadata support
 *   - A document is definitively forged based on one finding alone
 */

import {
  translateEditType,
  translateTechTerm,
  getSeverityInfo,
  getLocationDescription,
  generateVerificationSteps,
} from "./forensicTranslator.js";

// ─── Verdict Levels ──────────────────────────────────────────────────────────

export const VERDICTS = {
  AUTHENTIC: "Authentic",
  LOW_RISK: "Low Risk",
  SUSPICIOUS: "Suspicious",
  LIKELY_MANIPULATED: "Likely Manipulated",
  MANIPULATED: "Manipulated",
};

// ─── Severity Levels (Investigative Importance) ───────────────────────────────

export const SEVERITY = {
  LOW: "LOW",
  MEDIUM: "MEDIUM",
  HIGH: "HIGH",
  CRITICAL: "CRITICAL",
};

export const SEVERITY_CONFIG = {
  CRITICAL: {
    label: "CRITICAL",
    color: "#dc2626",
    bg: "rgba(220,38,38,0.12)",
    border: "rgba(220,38,38,0.4)",
    text: "text-red-400",
    bgClass: "bg-red-500/10",
    borderClass: "border-red-500/40",
    icon: "🔴",
    description: "Requires immediate expert review",
  },
  HIGH: {
    label: "HIGH",
    color: "#ea580c",
    bg: "rgba(234,88,12,0.12)",
    border: "rgba(234,88,12,0.4)",
    text: "text-orange-400",
    bgClass: "bg-orange-500/10",
    borderClass: "border-orange-500/40",
    icon: "🟠",
    description: "Significant investigative concern",
  },
  MEDIUM: {
    label: "MEDIUM",
    color: "#ca8a04",
    bg: "rgba(202,138,4,0.12)",
    border: "rgba(202,138,4,0.4)",
    text: "text-yellow-400",
    bgClass: "bg-yellow-500/10",
    borderClass: "border-yellow-500/40",
    icon: "🟡",
    description: "Manual verification recommended",
  },
  LOW: {
    label: "LOW",
    color: "#16a34a",
    bg: "rgba(22,163,74,0.10)",
    border: "rgba(22,163,74,0.35)",
    text: "text-emerald-400",
    bgClass: "bg-emerald-500/10",
    borderClass: "border-emerald-500/40",
    icon: "🟢",
    description: "Minor anomaly — proceed with awareness",
  },
};

// ─── Severity Matrix (by edit type — investigative importance) ────────────────

/**
 * Compute evidence-based severity.
 * Severity reflects what this finding MEANS for an investigation,
 * not how confident the model is.
 *
 * @param {string} editType - normalized edit type string
 * @param {number} confidence - model confidence 0–100
 * @param {object} context - { mediaType, page, isLegalDocument }
 * @returns {string} SEVERITY level
 */
export function computeEvidenceSeverity(editType = "", context = {}) {
  const e = String(editType).toLowerCase();

  // CRITICAL requires supported legal, authorization, or identity impact.
  if (
    context.isCritical ||
    (context.isLegalDocument &&
      ((e.includes("signature") &&
        (e.includes("insert") || e.includes("forge") || e.includes("paste"))) ||
        e.includes("stamp_forgery") ||
        e.includes("stamp forgery")))
  ) {
    return SEVERITY.CRITICAL;
  }

  // HIGH — Financial, legal dates, signature inconsistencies, major text manipulation
  if (
    e.includes("amount") || e.includes("financial") || e.includes("price") ||
    e.includes("invoice") || e.includes("total") || e.includes("digit_insert") ||
    e.includes("signature") ||
    e.includes("deepfake") || e.includes("face_swap") || e.includes("face swap") ||
    e.includes("page_replacement") || e.includes("page replacement") ||
    e.includes("date_modification") || e.includes("date modification") ||
    e.includes("name_modification") || e.includes("name modification") ||
    e.includes("seal") || e.includes("ai_generation") || e.includes("ai generation") ||
    e.includes("gan") ||
    e.includes("page_insertion") || e.includes("page insertion")
  ) {
    return SEVERITY.HIGH;
  }

  // MEDIUM — Logo, metadata, copy-move, font inconsistencies, moderate text
  if (
    e.includes("logo") || e.includes("watermark") || e.includes("barcode") ||
    e.includes("qr") || e.includes("copy_move") || e.includes("copy move") ||
    e.includes("metadata") || e.includes("font") || e.includes("character_spacing") ||
    e.includes("text_replacement") || e.includes("text replacement") ||
    e.includes("splicing") || e.includes("region_replacement") ||
    e.includes("object_replacement")
  ) {
    return SEVERITY.MEDIUM;
  }

  // LOW — Minor anomalies
  return SEVERITY.LOW;
}

export function formatEvidenceTimestamp(seconds) {
  const value = Number(seconds);
  if (!Number.isFinite(value) || value < 0) return null;
  const minutes = Math.floor(value / 60);
  const remainder = value - minutes * 60;
  return `${String(minutes).padStart(2, "0")}:${remainder.toFixed(3).padStart(6, "0")}`;
}

function isGenericTitle(title, findingType) {
  const value = String(title || "").trim().toLowerCase();
  const kind = String(findingType || "").replace(/_/g, " ").toLowerCase();
  return !value || value === kind || ["anomaly", "localization", "finding"].includes(value);
}

export function composeInvestigatorTitle(region = {}, mediaType = "document") {
  const supplied = String(region.title || "").trim();
  const field = String(region.field || region.label || "").trim();
  const kind = String(region.type || region.edit_type || region.rawEditType || "").toLowerCase();
  const media = String(mediaType || region.media_type || "document").toLowerCase();
  const timestamp = formatEvidenceTimestamp(region.timestamp ?? region.time_seconds);

  const haystack = `${field} ${kind} ${supplied}`.toLowerCase();
  if (media === "video" && timestamp) {
    return `Potential visual manipulation identified at ${timestamp}.`;
  }
  if (/total amount|amount due|invoice amount/.test(haystack) || /amount|invoice|price/.test(kind)) {
    return field
      ? `The ${field.toLowerCase()} appears to have been modified.`
      : /total amount/.test(haystack)
        ? "The total amount appears to have been modified."
        : "Financial value appears to have been modified.";
  }
  if (/signature/.test(`${field} ${kind}`)) {
    return /insert|paste|overlay|copied/.test(kind)
      ? "Signature appears digitally inserted."
      : "Signature region shows characteristics inconsistent with surrounding content.";
  }
  if (/logo/.test(`${field} ${kind}`)) {
    return "Company logo appears inconsistent with surrounding document content.";
  }
  if (/date/.test(`${field} ${kind}`)) {
    return "The date field shows characteristics inconsistent with the surrounding text.";
  }
  if (/metadata/.test(kind)) {
    return "File history contains a timestamp or authorship inconsistency.";
  }
  if (/copy[_ -]?move/.test(kind)) {
    return "A region appears to have been copied and repositioned.";
  }
  if (supplied && !isGenericTitle(supplied, kind)) {
    return /[.?!]$/.test(supplied) ? supplied : `${supplied}.`;
  }
  if (field) {
    return `${field} shows characteristics inconsistent with surrounding content.`;
  }
  if (media === "image") {
    return "The highlighted region contains characteristics that differ from the surrounding image.";
  }
  return "A localized region shows characteristics inconsistent with surrounding content.";
}

function finiteNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function sourceDimensionsOf(region = {}, context = {}) {
  const source =
    region.source_dimensions ||
    region.sourceDimensions ||
    (region.bbox && typeof region.bbox === "object" ? region.bbox : {});
  const width = finiteNumber(
    source.width ?? region.source_width ?? region.image_width ?? context.sourceWidth
  );
  const height = finiteNumber(
    source.height ?? region.source_height ?? region.image_height ?? context.sourceHeight
  );
  return width > 0 && height > 0 ? { width, height } : null;
}

/**
 * Convert supported backend/legacy boxes to a canonical x/y/width/height box.
 * The box is normalized when source dimensions are known; otherwise pixel
 * coordinates remain explicit so the viewer can align them to the media.
 */
export function normalizeFindingBbox(region = {}, context = {}) {
  const value =
    region.normalized_bbox ||
    region.bbox ||
    region.bounding_box ||
    region.coordinates ||
    null;
  if (!value) return null;

  let box;
  if (Array.isArray(value) && Array.isArray(value[0])) {
    const xs = value.map((point) => finiteNumber(point?.[0]) ?? 0);
    const ys = value.map((point) => finiteNumber(point?.[1]) ?? 0);
    const x = Math.min(...xs);
    const y = Math.min(...ys);
    box = { x, y, width: Math.max(...xs) - x, height: Math.max(...ys) - y };
  } else if (Array.isArray(value) && value.length >= 4) {
    const [x, y, third, fourth] = value.map((item) => finiteNumber(item) ?? 0);
    const format = String(region.bbox_format || region.coordinate_format || "").toLowerCase();
    box = format.includes("xyxy")
      ? { x, y, width: third - x, height: fourth - y }
      : { x, y, width: third, height: fourth };
  } else if (typeof value === "object") {
    const x = finiteNumber(value.x ?? value.left ?? value.x1) ?? 0;
    const y = finiteNumber(value.y ?? value.top ?? value.y1) ?? 0;
    box = {
      x,
      y,
      width:
        value.x2 != null
          ? (finiteNumber(value.x2) ?? x) - x
          : finiteNumber(value.width ?? value.w) ?? 0,
      height:
        value.y2 != null
          ? (finiteNumber(value.y2) ?? y) - y
          : finiteNumber(value.height ?? value.h) ?? 0,
    };
  }
  if (!box || box.width <= 0 || box.height <= 0) return null;

  const sourceDimensions = sourceDimensionsOf(region, context);
  const explicitlyNormalized =
    value === region.normalized_bbox ||
    String(
      value.coordinate_space ||
        region.coordinate_space ||
        region.bbox_space ||
        ""
    ).toLowerCase().includes("normal");
  const looksNormalized = Math.max(
    Math.abs(box.x), Math.abs(box.y), Math.abs(box.width), Math.abs(box.height)
  ) <= 1;
  if (explicitlyNormalized || looksNormalized) {
    return { ...box, coordinateSpace: "normalized", sourceDimensions };
  }
  if (sourceDimensions) {
    return {
      x: box.x / sourceDimensions.width,
      y: box.y / sourceDimensions.height,
      width: box.width / sourceDimensions.width,
      height: box.height / sourceDimensions.height,
      coordinateSpace: "normalized",
      sourceDimensions,
    };
  }
  return { ...box, coordinateSpace: "pixels", sourceDimensions: null };
}

// ─── Potential Impact by Edit Type ────────────────────────────────────────────

function getPotentialImpact(editType = "", mediaType = "") {
  const e = String(editType).toLowerCase();
  if (e.includes("signature")) {
    return "May affect the authenticity of document authorization or legal validity.";
  }
  if (e.includes("amount") || e.includes("financial") || e.includes("price") || e.includes("invoice")) {
    return "May affect the reliability of a stated financial value.";
  }
  if (e.includes("date")) {
    return "May affect the legal validity of the document's stated time of execution.";
  }
  if (e.includes("name")) {
    return "May indicate identity misrepresentation in the document.";
  }
  if (e.includes("seal") || e.includes("stamp")) {
    return "May affect the authenticity of official authorization represented by the seal.";
  }
  if (e.includes("logo")) {
    return "May indicate misrepresentation of the issuing organization.";
  }
  if (e.includes("deepfake") || e.includes("face")) {
    return "May constitute identity fraud or misrepresentation of the subject.";
  }
  if (e.includes("metadata")) {
    return "Suggests the document was modified after its stated creation date. Does not alone establish forgery.";
  }
  if (e.includes("page_replace") || e.includes("page_insert")) {
    return "May indicate that document content was substituted or supplemented after original creation.";
  }
  if (mediaType === "video") {
    return "May indicate the video has been altered to misrepresent events or identities.";
  }
  return "May indicate the document or evidence has been altered from its original state.";
}

// ─── Evidence Chain Builder ───────────────────────────────────────────────────

function buildEvidenceChain(region, evidenceId, findingId) {
  const effectiveCoords = normalizeFindingBbox(region);
  const canonicalChain = Array.isArray(region.evidence_chain)
    ? region.evidence_chain
    : [];
  const firstSource = canonicalChain[0] || {};
  const methods = canonicalChain
    .map((item) => item?.method)
    .filter(Boolean);

  return {
    findingId,
    sourceFile:
      firstSource.source_file ||
      firstSource.source_artifact ||
      region.source_file ||
      region.filename ||
      evidenceId ||
      "submitted-evidence",
    evidenceId: firstSource.evidence_id || evidenceId || null,
    page: region.page ?? null,
    frameNumber: region.frame_number ?? null,
    timestamp: region.timestamp ?? null,
    coordinates: effectiveCoords
      ? {
          x: effectiveCoords.x ?? effectiveCoords.left ?? null,
          y: effectiveCoords.y ?? effectiveCoords.top ?? null,
          w: effectiveCoords.width ?? null,
          h: effectiveCoords.height ?? null,
          coordinateSpace: effectiveCoords.coordinateSpace,
        }
      : null,
    analysisMethod: methods.length > 0 ? [...new Set(methods)] : buildAnalysisMethods(region),
    hash: firstSource.sha256 || region.hash || region.sha256 || null,
    evidenceCreatedAt:
      firstSource.observed_at || region.created_at || region.timestamp_created || null,
    investigationTimestamp:
      firstSource.generated_at || region.generated_at || null,
    records: canonicalChain,
  };
}

function buildAnalysisMethods(region) {
  const detectors = region.detectors || (region.detector ? [region.detector] : []);
  if (detectors.length > 0) return detectors;
  const e = String(region.edit_type || region.manipulation || region.type || "").toLowerCase();
  const methods = [];
  if (e.includes("ela") || e.includes("editing")) methods.push("ELA");
  if (e.includes("noise")) methods.push("Noise Analysis");
  if (e.includes("copy") || e.includes("move")) methods.push("Copy-Move Detection");
  if (e.includes("metadata")) methods.push("Metadata Forensics");
  if (e.includes("signature")) methods.push("Signature Analysis");
  if (e.includes("ocr") || e.includes("text")) methods.push("OCR Analysis");
  if (e.includes("gan") || e.includes("ai")) methods.push("Synthetic Content Detection");
  if (e.includes("face") || e.includes("deepfake")) methods.push("Face Forensics");
  return methods.length > 0 ? methods : ["Forensic Analysis"];
}

// ─── Observed Evidence Extractor ──────────────────────────────────────────────

function extractObservedEvidence(region) {
  // Prefer explicit backend-provided observed evidence
  if (region.observed_evidence) return region.observed_evidence;
  if (region.evidence_description) return region.evidence_description;
  if (region.evidence) return region.evidence;
  if (region.reason) return region.reason;
  if (region.description) return region.description;

  // Construct from available signals
  const observations = [];

  if (region.ela_score > 0) {
    const pct = region.ela_score <= 1 ? Math.round(region.ela_score * 100) : Math.round(region.ela_score);
    observations.push(`Editing artifact analysis score: ${pct}%.`);
  }
  if (region.noise_score > 0) {
    observations.push("Pixel-level inconsistencies detected in this region.");
  }
  if (region.copy_move_score > 0) {
    observations.push("Matching duplicate regions found within the evidence.");
  }
  if (region.font_inconsistency) {
    observations.push("Font rendering differs from adjacent text in the document.");
  }
  if (region.compression_anomaly || region.jpeg_artifact) {
    observations.push("Compression characteristics differ from surrounding content.");
  }
  if (region.edge_artifact) {
    observations.push("Edge characteristics around this region differ from natural boundaries.");
  }

  return observations.slice(0, 3).join(" ");
}

// ─── Explanation Builder ──────────────────────────────────────────────────────

function buildExplanation(region, editType, observedEvidence) {
  // Prefer explicit backend explanation
  if (region.plain_english_explanation) return applyForensicLanguageGuard(region.plain_english_explanation);
  if (region.plain_explanation) return applyForensicLanguageGuard(region.plain_explanation);
  if (region.explanation) return applyForensicLanguageGuard(region.explanation);

  const reason = region.reason || region.investigation || region.technical_explanation || "";
  if (typeof reason === "string" && reason) {
    return applyForensicLanguageGuard(reason.split("\n")[0].trim());
  }

  const observation = Array.isArray(observedEvidence)
    ? observedEvidence.join(" ")
    : observedEvidence;
  return applyForensicLanguageGuard(
    `${observation} The recorded evidence is consistent with a possible ${String(
      editType || "anomaly"
    ).toLowerCase()} and warrants contextual review; it does not alone establish intentional manipulation.`
  );
}

// ─── Original Comparison ──────────────────────────────────────────────────────

function buildOriginalComparison(region) {
  if (region.original_comparison && typeof region.original_comparison === "object") {
    const comparison = region.original_comparison;
    const original =
      comparison.original ??
      comparison.reference_value ??
      comparison.reference_or_expected;
    const examined =
      comparison.examined ??
      comparison.examined_value ??
      comparison.current;
    return {
      available: original != null || examined != null || Boolean(comparison.paired_regions),
      type: comparison.paired_regions ? "paired_regions" : "reference",
      label: comparison.field || "Corresponding evidence",
      original,
      examined,
      pairedRegions: comparison.paired_regions
        ? { regionA: comparison.region_a, regionB: comparison.region_b }
        : null,
      explanation: applyForensicLanguageGuard(
        comparison.explanation ||
          "The examined content is shown beside the corresponding reference or expected value."
      ),
      authenticityStatus: comparison.authenticity_status || "unknown",
    };
  }

  const diff = extractValueDiff(region);
  if (diff) {
    return {
      available: true,
      type: "value_diff",
      label: diff.label,
      original: diff.original,
      examined: diff.detected,
      explanation: `The ${diff.label.toLowerCase()} in the examined document differs from the value in the reference.`,
    };
  }

  if (region.reference_comparison) {
    return {
      available: true,
      type: "reference",
      explanation: applyForensicLanguageGuard(region.reference_comparison),
      original: null,
      examined: null,
    };
  }

  if (
    region.original_absent &&
    String(region.type || "").toLowerCase().includes("signature")
  ) {
    return {
      available: true,
      type: "presence_diff",
      explanation: "This element is absent from the reference document but present in the examined copy.",
      original: "Absent",
      examined: "Present",
    };
  }

  return { available: false };
}

function extractValueDiff(region) {
  const candidates = [
    region.ocr_difference && {
      label: "Text content",
      original: region.ocr_difference.original ?? region.ocr_difference.before,
      detected: region.ocr_difference.detected ?? region.ocr_difference.after,
    },
    region.ocr_mismatch && {
      label: "Text content",
      original: region.ocr_mismatch.original ?? region.ocr_mismatch.before,
      detected: region.ocr_mismatch.detected ?? region.ocr_mismatch.after,
    },
    region.original_value !== undefined && region.detected_value !== undefined && {
      label: "Value",
      original: region.original_value,
      detected: region.detected_value,
    },
    region.original_amount !== undefined && region.modified_amount !== undefined && {
      label: "Amount",
      original: region.original_amount,
      detected: region.modified_amount,
    },
    region.before !== undefined && region.after !== undefined && {
      label: "Content",
      original: region.before,
      detected: region.after,
    },
    region.original_ocr !== undefined && region.detected_ocr !== undefined && {
      label: "OCR text",
      original: region.original_ocr,
      detected: region.detected_ocr,
    },
  ].filter(Boolean);

  for (const c of candidates) {
    if (c.original !== undefined && c.detected !== undefined &&
        String(c.original) !== String(c.detected)) {
      return { label: c.label, original: String(c.original), detected: String(c.detected) };
    }
  }
  return null;
}

// ─── Forensic Language Guardrail ──────────────────────────────────────────────

/**
 * Ensure text uses evidence-based forensic language.
 * Softens definitive claims into hedged observations.
 * Never invents evidence — only re-phrases existing text.
 */
export function applyForensicLanguageGuard(text) {
  if (!text || typeof text !== "string") return text;

  // Replace overly definitive language with hedged alternatives
  const replacements = [
    [/\bwas forged by\b/gi, "appears to have been forged"],
    [/\bwas manipulated by\b/gi, "appears to have been manipulated"],
    [/\bwas edited using\b/gi, "may have been edited using"],
    [/\bwas definitely edited\b/gi, "appears to have been edited"],
    [/\bis definitely (forged|fake|fraudulent)\b/gi, "appears to be $1"],
    [/\bproves (forgery|manipulation|fraud)\b/gi, "indicates possible $1"],
    [/\bconfirms (forgery|manipulation)\b/gi, "suggests $1"],
    [/\bperson [A-Za-z]+ (edited|manipulated|forged)\b/gi, "this document appears to have been $1"],
    [/\bX manipulated\b/gi, "manipulation appears to have occurred"],
    [/\bwas created by\b/gi, "may have been created using"],
    [/\bis a fake\b/gi, "shows characteristics inconsistent with an authentic document"],
    [/\bis fraudulent\b/gi, "contains indicators that may suggest fraud"],
  ];

  let result = text;
  for (const [pattern, replacement] of replacements) {
    result = result.replace(pattern, replacement);
  }
  if (/^(manipulated|forged|fake|fraudulent)$/i.test(result.trim())) {
    result = `Indicators consistent with possible ${result.trim().toLowerCase()} content`;
  }

  // Ensure first sentence isn't an absolute declaration
  if (/^(This document|This file|This image|This video) (is|was) (forged|fake|fraudulent|manipulated)/.test(result)) {
    result = result.replace(
      /^(This document|This file|This image|This video) (is|was) (forged|fake|fraudulent|manipulated)/,
      "$1 appears to have been $3"
    );
  }

  return result;
}

// ─── Location Builder ─────────────────────────────────────────────────────────

function buildLocationString(region) {
  if (typeof region.location === "string" && region.location.trim()) {
    return region.location.trim();
  }
  const parts = [];

  if (region.page != null && Number(region.page) > 0) {
    parts.push(`Page ${region.page}`);
  }
  if (region.timestamp != null || region.time_seconds != null) {
    const stamped = formatEvidenceTimestamp(region.timestamp ?? region.time_seconds);
    if (stamped) parts.push(stamped);
  }
  if (region.frame != null || region.frame_number != null) {
    parts.push(`Frame ${region.frame ?? region.frame_number}`);
  }

  // Semantic region labels
  const label = region.label || region.region_label || "";
  const e = String(region.edit_type || region.type || "").toLowerCase();
  let regionName = "";
  if (/signature/i.test(label) || e.includes("signature")) regionName = "Signature Block";
  else if (/logo/i.test(label) || e.includes("logo")) regionName = "Logo Region";
  else if (/seal|stamp/i.test(label) || e.includes("seal")) regionName = "Official Seal";
  else if (/amount|price|total|invoice/i.test(label) || e.includes("amount") || e.includes("financial")) regionName = "Amount Field";
  else if (/date/i.test(label) || e.includes("date")) regionName = "Date Field";
  else if (/name/i.test(label) || e.includes("name")) regionName = "Name Field";
  else if (/face/i.test(label) || e.includes("face")) regionName = "Face Region";

  if (regionName) parts.push(regionName);

  // Add positional hint from bbox
  const nb = region.normalized_bbox;
  const b = nb || region.bbox || region.bounding_box || {};
  let x = b.x ?? b.left ?? null;
  let y = b.y ?? b.top ?? null;
  const w = b.w ?? b.width ?? 0;
  const h = b.h ?? b.height ?? 0;
  if (x != null && y != null) {
    const cx = x + w / 2;
    const cy = y + h / 2;
    const vPos = cy < 0.33 ? "Top" : cy > 0.67 ? "Bottom" : "Center";
    const hPos = cx < 0.33 ? "Left" : cx > 0.67 ? "Right" : "";
    const pos = [vPos, hPos].filter(Boolean).join(" ");
    if (!regionName && pos) parts.push(pos);
  }

  return parts.length > 0 ? parts.join(" · ") : "Location not specified";
}

// ─── Finding ID Generator ─────────────────────────────────────────────────────

function generateFindingId(region, index) {
  if (region.findingId) return region.findingId;
  if (region.finding_id) return region.finding_id;
  if (region.id) return `FND-${String(region.id).slice(0, 8).toUpperCase()}`;
  if (region.region_id) return `FND-${String(region.region_id).slice(0, 8).toUpperCase()}`;
  return `FND-${String(index + 1).padStart(3, "0")}`;
}

// ─── Main Normalizer — buildStandardFinding ───────────────────────────────────

/**
 * Normalize any raw backend region/finding object into the canonical
 * 17-field forensic finding format.
 *
 * @param {object} region - raw finding from backend
 * @param {number} index - 0-based position in findings array
 * @param {string} evidenceId - evidence ID for traceability
 * @param {object} context - { mediaType, isLegalDocument }
 * @returns {object} canonical forensic finding
 */
export function buildStandardFinding(region, index = 0, evidenceId = null, context = {}) {
  if (!region) return null;

  // ── 1. Core identity ──
  const findingId = generateFindingId(region, index);
  const rawScore = Number(region.confidence_pct ?? region.confidence ?? region.score ?? 0);
  const confidence = rawScore <= 1 ? Math.round(rawScore * 100) : Math.round(rawScore);

  // ── 2. Edit type (plain language) ──
  const rawEditType = region.rawEditType || region.edit_type || region.editType || region.manipulation || region.type || "";
  const editTypePlain = translateEditType(rawEditType);
  const title = composeInvestigatorTitle(
    { ...region, rawEditType, type: rawEditType },
    context.mediaType || region.mediaType || region.media_type
  );

  // ── 3. Severity (investigative importance) ──
  const suppliedSeverity = String(region.severity || region.risk_level || "").toUpperCase();
  const severity = SEVERITY_CONFIG[suppliedSeverity]
    ? suppliedSeverity
    : computeEvidenceSeverity(rawEditType, context);

  // ── 4. Verdict ──
  let verdict;
  const sevConf = severity === SEVERITY.CRITICAL || severity === SEVERITY.HIGH;
  if (confidence >= 75 || sevConf) {
    verdict = VERDICTS.LIKELY_MANIPULATED;
  } else if (confidence >= 50) {
    verdict = VERDICTS.SUSPICIOUS;
  } else if (confidence >= 30) {
    verdict = VERDICTS.LOW_RISK;
  } else {
    verdict = VERDICTS.AUTHENTIC;
  }
  if (region.verdict) verdict = applyForensicLanguageGuard(String(region.verdict));

  // ── 5. Location ──
  const location = region.location !== null && typeof region.location === "object"
    ? (typeof region.location.description === "string" && region.location.description.trim()
        ? region.location.description.trim()
        : buildLocationString(region))
    : buildLocationString(region);
  const page = finiteNumber(region.page ?? region.page_number);
  const frame = finiteNumber(region.frame ?? region.frame_number);
  const timestamp = finiteNumber(region.timestamp ?? region.time_seconds);
  const frameOrTimestamp = timestamp ?? frame;
  const bbox = normalizeFindingBbox(region, context);

  // ── 6. Observed Evidence ──
  const rawObservedEvidence =
    region.observedEvidence || region.observation || extractObservedEvidence(region);
  const observedEvidence = Array.isArray(rawObservedEvidence)
    ? rawObservedEvidence
        .map((item) =>
          applyForensicLanguageGuard(
            typeof item === "string"
              ? item
              : item?.description || item?.reason || item?.label || ""
          )
        )
        .filter(Boolean)
    : applyForensicLanguageGuard(rawObservedEvidence);

  // ── 7. Explanation ──
  const explanation = applyForensicLanguageGuard(
    region.short_explanation ||
      region.detailed_explanation ||
      region.reason ||
      region.explanation ||
      buildExplanation(region, editTypePlain, observedEvidence)
  );

  // ── 8. Original Comparison ──
  const originalComparison =
    region.originalComparison ||
    buildOriginalComparison(region);
  const observationText = Array.isArray(observedEvidence)
    ? observedEvidence[0]
    : observedEvidence;
  const whatChanged = applyForensicLanguageGuard(
    originalComparison?.available &&
      originalComparison.original != null &&
      originalComparison.examined != null
      ? `Reference shows ${originalComparison.original}. Examined copy shows ${originalComparison.examined}.`
      : observationText || title
  );

  // ── 9. Potential Impact ──
  const potentialImpact = applyForensicLanguageGuard(
    region.potentialImpact ||
      region.impact ||
      region.potential_impact ||
      getPotentialImpact(rawEditType, context.mediaType || "")
  );

  // ── 10. Recommended Review ──
  const suppliedReview =
    region.recommendedReview ||
    region.recommended_review ||
    region.recommendation;
  const verificationSteps = suppliedReview
    ? (Array.isArray(suppliedReview) ? suppliedReview : [suppliedReview])
    : generateVerificationSteps(editTypePlain);

  // ── 11. Evidence Chain ──
  const evidenceChain =
    region.evidenceChain ||
    buildEvidenceChain(region, evidenceId, findingId);

  // ── 12. Supporting reasons ──
  const reasons = [];
  if (region.reason) reasons.push(applyForensicLanguageGuard(region.reason));
  if (typeof region.investigation === "string") {
    region.investigation
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean)
      .slice(0, 2)
      .forEach((l) => reasons.push(applyForensicLanguageGuard(l)));
  }
  if (Array.isArray(region.evidence)) {
    region.evidence.slice(0, 2).forEach((e) =>
      reasons.push(applyForensicLanguageGuard(typeof e === "string" ? e : e?.description || ""))
    );
  }

  // ── 13. Legacy compatibility fields ──
  const legacySeverity = getSeverityInfo(confidence); // for backward compat with existing components

  return {
    // Identity
    findingId,
    displayNumber: index + 1,
    index,

    // Classification
    title,
    type: region.type || rawEditType || editTypePlain,
    editType: editTypePlain,
    rawEditType,
    verdict,
    severity,
    severityConfig: SEVERITY_CONFIG[severity],
    confidence,

    // Location
    location: region.location || location,
    page,
    frame,
    timestamp,
    frameOrTimestamp,
    bbox,
    relatedBboxes: originalComparison?.pairedRegions
      ? [originalComparison.pairedRegions.regionA, originalComparison.pairedRegions.regionB].filter(Boolean)
      : [],
    sourceDimensions: bbox?.sourceDimensions || sourceDimensionsOf(region, context),
    mediaType: context.mediaType || region.mediaType || region.media_type || "document",

    // Evidence
    observedEvidence,
    whatChanged,
    why: explanation,
    supportingEvidence: observedEvidence,
    explanation,
    detailedExplanation:
      region.detailed_explanation || region.explanation || explanation,
    reasons: reasons.slice(0, 4),
    originalComparison,

    // Impact
    potentialImpact,
    recommendedReview: verificationSteps,

    // Traceability
    evidenceChain,

    // Analysis provenance
    detectors: evidenceChain.analysisMethod,

    // Backward compatibility with existing components
    legacySeverity,
    whatHappened: title,
    locationText: location,
    plainEnglish: explanation,
    verificationSteps,

    // Raw region for Technical Evidence panel
    raw: region.raw || region,
  };
}

function legacyFindingCandidates(analysisResult = {}, localization = null) {
  const analysis = analysisResult?.analysis || {};
  const pages =
    analysisResult?.documentAnalysis?.pages ||
    analysisResult?.investigation?.document_analysis?.pages ||
    analysis?.document_intelligence?.pages ||
    [];
  const pageIssues = (Array.isArray(pages) ? pages : []).flatMap((page, pageIndex) =>
    (Array.isArray(page?.issues || page?.intelligence?.issues)
      ? page.issues || page.intelligence.issues
      : []
    ).map((issue) => ({
      ...issue,
      page: issue.page ?? page.page_number ?? pageIndex + 1,
      bbox_format: issue.bbox_format || "xyxy",
      source_width: issue.source_width ?? page.width ?? page.image_width,
      source_height: issue.source_height ?? page.height ?? page.image_height,
    }))
  );
  const candidates = [
    localization?.regions,
    localization?.findings,
    analysisResult?.findings,
    analysisResult?.human_findings,
    analysisResult?.explainableAI?.findings,
    analysisResult?.explainable_ai?.findings,
    analysisResult?.jury?.forensic_dossier?.findings,
    analysisResult?.forensic_dossier?.findings,
    analysisResult?.localization?.regions,
    analysis?.localization?.regions,
    analysis?.regions,
    analysis?.findings,
    analysis?.risk_fusion?.findings,
    pageIssues,
  ];
  return candidates.flatMap((candidate) => Array.isArray(candidate) ? candidate : []);
}

/**
 * Single UI collection adapter. Canonical endpoint findings are authoritative;
 * legacy analysis/localization is only consulted when that collection is absent.
 */
export function buildCanonicalFindings({
  apiFindings,
  analysisResult = {},
  localization = null,
  evidenceId = null,
  mediaType = null,
} = {}) {
  const preferred = Array.isArray(apiFindings) ? apiFindings : null;
  const source = (preferred ?? legacyFindingCandidates(analysisResult, localization))
    .map((finding) =>
      typeof finding === "string"
        ? {
            type: "recorded_anomaly",
            title: "Recorded forensic anomaly",
            observed_evidence: finding,
            explanation: finding,
          }
        : finding
    );
  const seen = new Set();
  return source
    .filter((finding) => finding && String(finding.type || "").toLowerCase() !== "none")
    .map((finding, index) =>
      buildStandardFinding(finding, index, evidenceId, {
        mediaType:
          finding.mediaType ||
          finding.media_type ||
          mediaType ||
          analysisResult?.fileType ||
          "document",
      })
    )
    .filter(Boolean)
    .filter((finding) =>
      Array.isArray(finding.observedEvidence)
        ? finding.observedEvidence.length > 0
        : Boolean(String(finding.observedEvidence || "").trim())
    )
    .filter((finding) => {
      const box = finding.bbox;
      const key = finding.findingId || [
        finding.type,
        finding.page,
        finding.frame,
        finding.timestamp,
        box?.x,
        box?.y,
        finding.title,
      ].join("|");
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .map((finding, index) => ({
      ...finding,
      index,
      displayNumber: index + 1,
      number: index + 1,
      id: finding.findingId,
      category: finding.editType,
      recommendation: finding.recommendedReview?.[0] || "Independent review is recommended.",
    }));
}

// ─── Overall Conclusion Builder ───────────────────────────────────────────────

/**
 * Build the overall forensic conclusion from all standardized findings.
 *
 * @param {object[]} findings - array of canonical finding objects
 * @param {object} juryData - jury fusion data from backend
 * @param {object} analysisResult - raw analysis result
 * @returns {object} conclusion object
 */
export function buildOverallConclusion(findings = [], juryData = null, analysisResult = null) {
  const total = findings.length;
  const critical = findings.filter((f) => f.severity === SEVERITY.CRITICAL).length;
  const high = findings.filter((f) => f.severity === SEVERITY.HIGH).length;
  const medium = findings.filter((f) => f.severity === SEVERITY.MEDIUM).length;

  // Derive verdict from findings + jury
  const juryVerdict =
    juryData?.fusion?.verdict ||
    juryData?.verdict ||
    analysisResult?.jury?.fusion?.verdict ||
    null;

  const analysisVerdict =
    analysisResult?.analysis?.verdict ||
    analysisResult?.verdict ||
    null;

  let overallVerdict;
  let verdictLevel;

  if (critical >= 2 || (critical >= 1 && high >= 1)) {
    overallVerdict = "LIKELY TAMPERED";
    verdictLevel = "critical";
  } else if (critical >= 1 || high >= 2) {
    overallVerdict = "LIKELY TAMPERED";
    verdictLevel = "high";
  } else if (high >= 1 || medium >= 2) {
    overallVerdict = "SUSPICIOUS";
    verdictLevel = "medium";
  } else if (total > 0) {
    overallVerdict = "ANOMALIES DETECTED";
    verdictLevel = "low";
  } else {
    overallVerdict = "INSUFFICIENT EVIDENCE";
    verdictLevel = "inconclusive";
  }

  // Honour jury/analysis verdict if present
  const rawVerdict = String(juryVerdict || analysisVerdict || "").toLowerCase();
  if (
    total > 0 &&
    (rawVerdict.includes("tamper") ||
      rawVerdict.includes("forg") ||
      rawVerdict.includes("manip") ||
      rawVerdict.includes("fake"))
  ) {
    overallVerdict = "LIKELY TAMPERED";
    verdictLevel = "high";
  }

  // Build primary finding summaries (top 5)
  const primaryFindings = [...findings]
    .sort((a, b) => {
      const order = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
      return (order[a.severity] ?? 4) - (order[b.severity] ?? 4);
    })
    .slice(0, 5)
    .map((f, i) => ({
      number: i + 1,
      title: f.title,
      severity: f.severity,
      findingId: f.findingId,
    }));

  // Overall narrative — from jury dossier or generated
  const juryNarrative =
    juryData?.forensic_dossier?.executive_summary ||
    juryData?.fusion?.forensic_dossier?.executive_summary ||
    analysisResult?.jury?.forensic_dossier?.executive_summary ||
    null;

  let combinedAssessment;
  if (verdictLevel === "inconclusive") {
    combinedAssessment =
      "The available analysis did not produce a reviewable forensic finding. This is insufficient to establish either authenticity or manipulation; source verification and expert review may still be required.";
  } else if (juryNarrative) {
    combinedAssessment = applyForensicLanguageGuard(juryNarrative);
  } else if (verdictLevel === "low") {
    combinedAssessment =
      "Analysis identified minor anomalies that warrant awareness. The available evidence is insufficient to conclusively determine whether the evidence was intentionally manipulated.";
  } else if (verdictLevel === "medium") {
    combinedAssessment =
      "The examination identified suspicious elements that require verification. The findings indicate anomalies inconsistent with the expected characteristics of unmodified content.";
  } else {
    combinedAssessment =
      "The examination identified multiple independent indicators of potential post-creation modification. The combined evidence suggests this material may have been modified after its original creation. Expert review is strongly recommended before relying on this evidence.";
    if (primaryFindings.length) {
      combinedAssessment +=
        " Primary findings: " +
        primaryFindings.map((item) => item.title.replace(/\.$/, "")).join("; ") +
        ".";
    }
  }

  const disclaimer =
    "This analysis is based on available digital evidence. Forensic findings indicate anomalies but do not constitute legal proof of forgery without expert examination and contextual verification.";

  return {
    overallVerdict,
    verdictLevel,
    totalFindings: total,
    criticalCount: critical,
    highCount: high,
    mediumCount: medium,
    lowCount: total - critical - high - medium,
    primaryFindings,
    combinedAssessment,
    disclaimer,
    juryNarrative: juryNarrative ? applyForensicLanguageGuard(juryNarrative) : null,
  };
}

// ─── Re-export helpers used by other files ────────────────────────────────────
// (These are imported from forensicTranslator — re-exported for convenience)
export { translateEditType, translateTechTerm, getSeverityInfo, getLocationDescription, generateVerificationSteps };

