import {
  asArray,
  asObject,
  resolveFindings,
  resolveRegions,
} from "../forensic-evidence-viewer/forensicData.js";

const CATEGORY_RULES = [
  ["signature", "Signature Insertion"],
  ["logo", "Logo Replacement"],
  ["metadata", "Metadata Anomaly"],
  ["font", "Font Inconsistency"],
  ["ocr", "OCR Mismatch"],
  ["text recognition", "OCR Mismatch"],
  ["amount", "Amount Modification"],
  ["currency", "Amount Modification"],
  ["invoice value", "Amount Modification"],
  ["date", "Date Modification"],
  ["compression", "Compression Anomaly"],
  ["ela", "Compression Anomaly"],
  ["jpeg", "Compression Anomaly"],
  ["layout", "Layout Manipulation"],
  ["spacing", "Layout Manipulation"],
  ["copy move", "Image Replacement"],
  ["copy_move", "Image Replacement"],
  ["image replacement", "Image Replacement"],
  ["text", "Text Modification"],
];

const CATEGORY_TITLES = {
  "Text Modification": "Document text shows signs of modification",
  "Image Replacement": "Image content may have been replaced",
  "Signature Insertion": "Signature content requires authenticity review",
  "Metadata Anomaly": "File history contains an anomaly",
  "Font Inconsistency": "Typography differs from surrounding content",
  "OCR Mismatch": "Recognized text differs from the visible document",
  "Compression Anomaly": "Compression differs within the evidence",
  "Layout Manipulation": "Document layout is internally inconsistent",
  "Date Modification": "A date field may have been modified",
  "Amount Modification": "A financial value may have been modified",
  "Logo Replacement": "Logo content may have been replaced",
  "Visual Anomaly": "A localized visual anomaly requires review",
};

const RECOMMENDATIONS = {
  "Text Modification": "Compare the text with the originating record.",
  "Image Replacement": "Compare this area with the original image source.",
  "Signature Insertion": "Refer the signature to a qualified examiner.",
  "Metadata Anomaly": "Verify file history against custody and source records.",
  "Font Inconsistency": "Compare typography with an authenticated document.",
  "OCR Mismatch": "Confirm the visible value against the source record.",
  "Compression Anomaly": "Review the original file before relying on this copy.",
  "Layout Manipulation": "Compare layout with an authenticated template.",
  "Date Modification": "Verify the date against independent records.",
  "Amount Modification": "Verify the amount against transaction records.",
  "Logo Replacement": "Compare the logo with the issuer’s official artwork.",
  "Visual Anomaly": "Inspect the marked region against the original evidence.",
};

export function normalizePercent(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return null;
  return Math.min(100, Math.max(0, number <= 1 ? number * 100 : number));
}

function textValue(value) {
  if (Array.isArray(value)) return value.filter(Boolean).join(". ");
  if (value && typeof value === "object") {
    return value.description || value.reason || value.label || "";
  }
  return String(value || "");
}

export function toInvestigatorText(value, fallback = "") {
  let text = textValue(value).replace(/\s+/g, " ").trim();
  if (!text) return fallback;

  const replacements = [
    [/\bour AI (?:thinks|detected|identified|found)\b/gi, "Forensic examination identified"],
    [/\bthe (?:AI |neural network )?model (?:predicts|detected|indicates|found)\b/gi, "Analysis indicates"],
    [/\bneural (?:network|tampering detector)\b/gi, "forensic examination"],
    [/\bCNN tampering classifier flagged anomaly(?:\s*\([^)]*\))?/gi, "The examination identified an alteration pattern"],
    [/\bdeep learning\b/gi, "specialist examination"],
    [/\bclassification probability\b/gi, "assessment confidence"],
    [/\binference score\b/gi, "assessment result"],
    [/\bdetector confidence\b/gi, "evidential strength"],
    [/\bdetectors?\b/gi, "forensic checks"],
    [/\bmodules?\b/gi, "examinations"],
    [/\bensemble\b/gi, "combined examination"],
    [/\bError Level Analysis\b/gi, "Compression consistency examination"],
    [/\bELA\b/g, "compression consistency"],
    [/\bwavelet(?: subband)?\b/gi, "texture consistency"],
    [/\bcopy[- ]move\b/gi, "duplicated-content"],
    [/\bpixel structures?\b/gi, "visual structures"],
    [/\bedge(?: inconsistency)?\b/gi, "boundary consistency"],
    [/\b(?:RGB|HSV|LAB|YCbCr)(?: channels?| analysis)?\b/gi, "color consistency"],
    [/\bfrequency-domain analysis\b/gi, "structural consistency examination"],
    [/\bEXIF\b/gi, "file metadata"],
    [/\bGAN artifacts?\b/gi, "synthetic-content characteristics"],
    [/\bGAN detection\b/gi, "synthetic-content examination"],
    [/\bheatmap\b/gi, "localization review"],
    [/\bExtracted 0 suspicious region (?:masks?|regions?)\(s\)/gi, "No suspicious regions were localized"],
    [/\bmasks?\b/gi, "regions"],
    [/\bOCR\b/g, "text recognition"],
    [/\bAI[- ]generated\b/gi, "synthetic"],
    [/\bmodel output\b/gi, "examination result"],
    [/\bweighted fusion\b/gi, "consolidated assessment"],
    [/\bEditing software detected:\s*unknown software\b/gi, "File history contains an editing indicator"],
  ];
  replacements.forEach(([pattern, replacement]) => {
    text = text.replace(pattern, replacement);
  });

  text = text
    .replace(/\b(?:tensor|embedding)s?\b/gi, "")
    .replace(/\((?:texture_fallback|model fallback|unknown software)\)/gi, "")
    .replace(/\(\s*risk\s*=\s*\d+(?:\.\d+)?\s*\)/gi, "")
    .replace(/\b(?:risk|confidence|tampering)?\s*score\s*[=:]\s*\d+(?:\.\d+)?/gi, "")
    .replace(/\bmatched_points\s*[=:]\s*\d+/gi, "")
    .replace(/\s+([,.;:])/g, "$1")
    .replace(/\s{2,}/g, " ")
    .trim();

  return text || fallback;
}

function categoryOf(raw) {
  const source = [
    raw?.category,
    raw?.type,
    raw?.module,
    raw?.edit_type,
    raw?.label,
    raw?.reason,
    raw?.description,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return (
    CATEGORY_RULES.find(([term]) => source.includes(term))?.[1] ||
    "Visual Anomaly"
  );
}

function locationOf(raw) {
  if (typeof raw?.location === "string" && raw.location.trim()) {
    return toInvestigatorText(raw.location);
  }
  if (raw?.field_name || raw?.field) return String(raw.field_name || raw.field);
  if (raw?.quadrant) return String(raw.quadrant);
  if (raw?.bbox || raw?.bounding_box || raw?.location) return "Marked document region";
  return "Document-wide finding";
}

function explanationOf(raw, category) {
  const evidence = asArray(raw?.evidence).filter(Boolean).slice(0, 2);
  return toInvestigatorText(
    raw?.plain_english_explanation ||
      raw?.explanation ||
      raw?.reason ||
      raw?.description ||
      raw?.investigation ||
      evidence,
    CATEGORY_TITLES[category]
  );
}

function findingKey(finding) {
  return [
    finding.category,
    finding.page,
    finding.location,
    finding.explanation.toLowerCase().replace(/\d+(?:\.\d+)?/g, "#"),
  ].join("|");
}

export function buildInvestigatorFindings(analysisResult, localization) {
  const analysis = asObject(analysisResult?.analysis);
  const documentPages =
    analysisResult?.documentAnalysis?.pages ||
    analysisResult?.investigation?.document_analysis?.pages ||
    analysis?.document_intelligence?.pages ||
    [];
  const pageFindings = asArray(documentPages).flatMap((page, pageIndex) =>
    asArray(page?.issues || page?.intelligence?.issues).map((issue) => ({
      ...issue,
      page: issue?.page ?? page?.page_number ?? pageIndex + 1,
      bbox_format: issue?.bbox_format || "xyxy",
    }))
  );
  const rawFindings = [
    ...resolveRegions(localization, analysisResult),
    ...resolveFindings(analysisResult, localization),
    ...pageFindings,
  ];
  const seen = new Set();

  const normalized = rawFindings
    .filter((raw) => raw && String(raw.type || "").toLowerCase() !== "none")
    .map((raw, index) => {
      const category = categoryOf(raw);
      const severity = String(
        raw.risk_level || raw.risk || raw.severity || "Not rated"
      ).toUpperCase();
      const finding = {
        ...raw,
        id: raw.id || raw.finding_id || `finding-${index + 1}`,
        number: index + 1,
        page: raw.page ?? raw.page_number ?? null,
        location: locationOf(raw),
        category,
        title: toInvestigatorText(
          raw.finding || raw.title || raw.label,
          CATEGORY_TITLES[category]
        ),
        confidence: normalizePercent(raw.confidence ?? raw.confidence_pct),
        severity,
        explanation: explanationOf(raw, category),
        recommendation: toInvestigatorText(
          raw.recommendation || raw.recommended_action,
          RECOMMENDATIONS[category]
        ),
      };
      return finding;
    });
  const localizedCategories = new Set(
    normalized
      .filter((finding) => finding.bbox || finding.bounding_box)
      .map((finding) => finding.category)
  );

  return normalized
    .filter(
      (finding) =>
        finding.bbox ||
        finding.bounding_box ||
        !localizedCategories.has(finding.category)
    )
    .filter((finding) => {
      const key = findingKey(finding);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .sort((a, b) => {
      const order = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1, "NOT RATED": 0 };
      return (order[b.severity] || 0) - (order[a.severity] || 0);
    })
    .map((finding, index) => ({ ...finding, number: index + 1 }));
}

function isRiskVerdict(verdict) {
  const value = String(verdict || "").toLowerCase();
  return ["risk", "tamper", "manipulat", "forg", "suspicious", "review"].some((term) =>
    value.includes(term)
  );
}

function sourceAgent(agents, sourceIds) {
  return sourceIds.map((id) => agents[id]).find(Boolean) || null;
}

function conciseReason(agent, fallback) {
  return toInvestigatorText(
    asArray(agent?.evidence)[0] ||
      agent?.reason ||
      agent?.explanation ||
      agent?.opinion,
    fallback
  );
}

export function buildJurorPerspectives(juryResult, analysisResult, findings) {
  const agents = asObject(juryResult?.agents);
  const fusion = asObject(juryResult?.fusion);
  const analysis = asObject(analysisResult?.analysis);
  const riskFusion = asObject(analysis?.risk_fusion);
  const ocrScore = riskFusion?.component_scores?.ocr;
  const ocrConfidence = riskFusion?.confidence_breakdown?.ocr_confidence;

  const definitions = [
    {
      id: "vision",
      name: "Vision Expert",
      sources: ["vision", "pixel", "noise", "deep_learning"],
      fallback: "Visual integrity was not separately assessed.",
    },
    {
      id: "forgery",
      name: "Forgery Expert",
      sources: ["tampering", "localization", "forgery"],
      fallback: "Forgery localization was not separately assessed.",
    },
    {
      id: "ocr",
      name: "OCR Expert",
      sources: ["ocr"],
      fallback: "Text consistency was not separately assessed.",
    },
    {
      id: "metadata",
      name: "Metadata Expert",
      sources: ["metadata"],
      fallback: "File history was not separately assessed.",
    },
    {
      id: "signature",
      name: "Signature Expert",
      sources: ["signature"],
      fallback: "No signature assessment was recorded.",
    },
    {
      id: "risk",
      name: "Risk Assessment Expert",
      sources: ["risk", "explainability"],
      fallback: "The consolidated risk assessment is unavailable.",
    },
  ];

  return definitions.map((definition) => {
    const agent = sourceAgent(agents, definition.sources);
    if (definition.id === "ocr" && !agent && ocrScore != null) {
      return {
        ...definition,
        verdict: Number(ocrScore) >= 0.45 ? "Requires review" : "No concern identified",
        confidence: normalizePercent(ocrConfidence),
        reasoning:
          findings.find((finding) =>
            ["OCR Mismatch", "Font Inconsistency", "Layout Manipulation"].includes(
              finding.category
            )
          )?.explanation || "Text and layout consistency checks were completed.",
      };
    }
    if (definition.id === "risk") {
      return {
        ...definition,
        verdict:
          agent?.verdict ||
          fusion?.final_verdict ||
          fusion?.verdict ||
          analysis?.verdict ||
          "Not assessed",
        confidence: normalizePercent(
          agent?.confidence ??
            fusion?.confidence_pct ??
            fusion?.confidence ??
            analysis?.confidence
        ),
        reasoning:
          findings[0]?.explanation ||
          conciseReason(agent, definition.fallback),
      };
    }
    return {
      ...definition,
      verdict: agent?.verdict || agent?.decision || "Not assessed",
      confidence: normalizePercent(agent?.confidence_pct ?? agent?.confidence),
      reasoning: conciseReason(agent, definition.fallback),
    };
  });
}

export function buildJurySummary(jurors, findings) {
  const assessed = jurors.filter((juror) => juror.verdict !== "Not assessed");
  const riskVotes = assessed.filter((juror) => isRiskVerdict(juror.verdict)).length;
  const concerns = [...new Set(findings.map((finding) => finding.title))].slice(0, 3);
  return {
    decision: `${riskVotes} of ${jurors.length} expert analyses indicate evidence requiring further review.`,
    concerns,
  };
}
