/**
 * forensicTranslator.js
 *
 * Central plain-language translation engine for AI-FORGE.
 * Converts raw AI/technical terms into investigative language
 * understandable by non-technical users (police, magistrates, lawyers).
 *
 * NEVER invents or hallucinates evidence.
 * All translations are deterministic mappings of existing data.
 */

// ─── Technical term → Plain language map ────────────────────────────────────

const TECH_TERM_MAP = {
  "ela anomaly": "Possible image editing detected",
  "ela score": "Image editing likelihood",
  ela: "Editing artifact analysis",
  "error level analysis": "Image editing detection",
  "compression anomaly": "Possible editing detected through compression analysis",
  "jpeg artifact": "Image compression inconsistency detected",
  "jpeg block": "JPEG compression inconsistency",
  "noise residual": "Pixel-level inconsistency detected",
  "noise inconsistency": "Inconsistent pixel patterns detected",
  "noise map": "Inconsistency visualization",
  "noise analysis": "Pixel consistency check",
  noise: "Pixel inconsistency",
  "copy move": "Copied content detected",
  "copy-move": "Copied content detected",
  copy_move: "Content copied and repositioned",
  copymove: "Content was duplicated or repositioned",
  "matched points": "Matching duplicated regions found",
  "ransac inliers": "Confirmed duplicate regions",
  "metadata mismatch": "Document was modified after original creation",
  "metadata inconsistency": "File information does not match original",
  "metadata changes": "Document metadata was altered",
  metadata_forensics: "Document creation history analysis",
  "exif mismatch": "Photo information records do not match",
  "sha256 mismatch": "The evidence appears to have been modified after it was originally uploaded.",
  "integrity passed": "The evidence remains unchanged since submission.",
  "creation date mismatch": "Document dates are inconsistent",
  "modification date": "Document last modified date",
  "signature similarity": "Signature comparison result",
  "signature mismatch": "Signature differs from reference",
  "signature verification": "Signature authenticity check",
  "stroke dynamics": "Signature stroke pattern analysis",
  "pressure pattern": "Pen pressure consistency check",
  "gan detection": "AI-generated content detection",
  gan: "AI image generation detector",
  ai_generation: "AI-synthesized content analysis",
  "ai generated probability": "Likelihood of AI generation",
  "synthetic artifact": "AI-generated visual artifact",
  deepfake: "AI face manipulation detection",
  "deepfake probability": "Likelihood of face manipulation",
  wavelet: "Frequency-domain analysis",
  "wavelet score": "Frequency manipulation likelihood",
  "wavelet analysis": "Signal frequency inconsistency check",
  "edge detection": "Boundary analysis",
  "edge density": "Boundary irregularity measure",
  multispectral: "Multi-layer color analysis",
  "spectral fusion": "Combined color-channel analysis result",
  rgb: "Color channel analysis",
  hsv: "Color tone analysis",
  lab: "Color space analysis",
  ycbcr: "Video color analysis",
  frequency: "Frequency pattern analysis",
  "forgery mask": "Manipulation area map",
  "localization mask": "Detected manipulation areas",
  "localization heatmap": "Manipulation likelihood map",
  heatmap: "Manipulation likelihood visualization",
  "segmentation overlay": "Evidence region overlay",
  "bounding box": "Detected area coordinates",
  "forgery localization": "Exact location of manipulation",
  localization: "Manipulation location mapping",
  ocr: "Text recognition analysis",
  "ocr mismatch": "Text content inconsistency detected",
  "text modification": "Text was altered",
  "text replacement": "Text content was replaced",
  "font inconsistency": "Different fonts detected in same document",
  "ink inconsistency": "Different ink or print patterns detected",
  "face forensics": "Facial authenticity analysis",
  "face swap": "A face appears to have been replaced",
  "face manipulation": "Facial content was altered",
  "cnn confidence": "AI detection certainty",
  ensemble: "Combined AI analysis",
  fusion: "Combined analysis result",
  "risk score": "Manipulation likelihood score",
  "forgery probability": "Likelihood of document forgery",
  "authenticity score": "Document authenticity likelihood",
  "detector confidence": "AI analysis certainty",
  "majority vote": "Combined AI opinion",
  "risk fusion": "Combined risk assessment",
  "investigation panel": "Analysis summary",
  "temporal anomaly": "Irregular changes detected over time",
  "face replacement": "A face appears to have been artificially replaced",
  "lip sync mismatch": "The lip movement does not match the spoken audio",
  "object insertion": "An object appears artificially inserted into the video",
  "frame deletion": "The video contains missing or dropped frames",
  "frame interpolation": "The video contains artificially generated transition frames",
  "frame repetition": "The video contains repeated frames",
  "audio-video synchronization": "Audio and video streams are out of sync",
  "temporal gap": "An unnatural gap in time was detected",
  "lighting inconsistency": "The lighting changes abruptly between frames",
  "blink inconsistency": "The person's facial movements differ from natural motion",
  "expression inconsistency": "The facial expression appears artificially generated",
  "audio sync score": "Lip sync consistency measure"
};

/**
 * Translate a technical forensic term to plain language.
 */
export function translateTechTerm(term) {
  if (!term) return "";
  const lower = String(term).toLowerCase().trim();
  if (TECH_TERM_MAP[lower]) return TECH_TERM_MAP[lower];
  for (const [key, value] of Object.entries(TECH_TERM_MAP)) {
    if (lower.includes(key)) return value;
  }
  return term.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

// ─── Edit type → Plain label ─────────────────────────────────────────────────

const EDIT_TYPE_MAP = {
  copy_move: "Content copied and repositioned",
  copymove: "Content copied and repositioned",
  ela: "Image editing detected",
  noise: "Pixel-level inconsistency detected",
  logo_replacement: "Logo appears to have been replaced",
  logo: "Logo appears to have been replaced",
  signature_pasted: "Signature appears to have been inserted",
  signature_forgery: "Signature appears to be forged",
  signature: "Signature inconsistency detected",
  price_edited: "Amount or price appears to have been changed",
  amount_modified: "Financial amount appears to have been altered",
  text_replacement: "Text content appears to have been replaced",
  text_overwrite: "Text appears to have been written over",
  text_insertion: "Additional text appears to have been inserted",
  date_modification: "Date appears to have been changed",
  name_modification: "Name appears to have been altered",
  seal_replacement: "Official seal appears to have been replaced",
  seal: "Official seal inconsistency detected",
  face_swap: "A face appears to have been replaced",
  deepfake: "Face manipulation detected",
  qr_code: "QR code appears to have been modified",
  barcode: "Barcode appears to have been altered",
  invisible_text: "Hidden or invisible text detected",
  page_replacement: "This page appears to have been substituted",
  page_insertion: "An additional page appears to have been inserted",
  object_replacement: "An object appears to have been replaced",
  forgery: "Forgery indicators detected",
  gan: "AI-generated content detected",
  ai_generation: "Content appears to be AI-generated",
  splicing: "Image region appears to have been cut and inserted",
  metadata: "Document metadata was altered after creation",
  whitespace: "Whitespace manipulation detected",
  paragraph_insertion: "Additional content appears to have been inserted",
  table_modification: "Table data appears to have been changed",
};

/**
 * Translate a raw edit type code to a plain-language description.
 */
export function translateEditType(type) {
  if (!type) return "Manipulation detected";
  const key = String(type).toLowerCase().trim().replace(/[- ]/g, "_");
  return EDIT_TYPE_MAP[key] || EDIT_TYPE_MAP[type] || translateTechTerm(type);
}

// ─── Severity labels ─────────────────────────────────────────────────────────

export function getSeverityInfo(score) {
  const s = Number(score) || 0;
  const pct = s <= 1 ? s * 100 : s;
  if (pct >= 75) {
    return {
      label: "Confirmed Manipulation",
      short: "CONFIRMED",
      color: "red",
      borderClass: "border-red-500",
      bgClass: "bg-red-500/15",
      textClass: "text-red-400",
      badgeBg: "bg-red-500",
      hex: "#ef4444",
      dot: "🔴",
      recommendVerify: true,
    };
  }
  if (pct >= 50) {
    return {
      label: "Suspicious — Likely Manipulated",
      short: "SUSPICIOUS",
      color: "orange",
      borderClass: "border-orange-400",
      bgClass: "bg-orange-400/15",
      textClass: "text-orange-300",
      badgeBg: "bg-orange-400",
      hex: "#fb923c",
      dot: "🟠",
      recommendVerify: true,
    };
  }
  if (pct >= 30) {
    return {
      label: "Needs Manual Verification",
      short: "VERIFY",
      color: "yellow",
      borderClass: "border-yellow-400",
      bgClass: "bg-yellow-400/15",
      textClass: "text-yellow-300",
      badgeBg: "bg-yellow-400",
      hex: "#facc15",
      dot: "🟡",
      recommendVerify: true,
    };
  }
  return {
    label: "Appears Genuine",
    short: "GENUINE",
    color: "green",
    borderClass: "border-emerald-400",
    bgClass: "bg-emerald-400/15",
    textClass: "text-emerald-300",
    badgeBg: "bg-emerald-400",
    hex: "#34d399",
    dot: "🟢",
    recommendVerify: false,
  };
}

// ─── Location description ────────────────────────────────────────────────────

export function getLocationDescription(bbox, page, naturalSize = null) {
  const parts = [];
  if (page != null && Number(page) > 0) parts.push(`Page ${page}`);

  const b = bbox || {};
  let x = b.x ?? b.left ?? null;
  let y = b.y ?? b.top ?? null;
  let w = b.w ?? b.width ?? null;
  let h = b.h ?? b.height ?? null;

  if (naturalSize && x != null && x > 1) {
    x = x / naturalSize.w;
    y = y / naturalSize.h;
    w = w ? w / naturalSize.w : null;
    h = h ? h / naturalSize.h : null;
  }

  if (x != null && y != null) {
    const cx = x + (w || 0) / 2;
    const cy = y + (h || 0) / 2;
    const vPos = cy < 0.33 ? "Top" : cy > 0.67 ? "Bottom" : "Middle";
    const hPos = cx < 0.33 ? "Left" : cx > 0.67 ? "Right" : "Center";
    const position = vPos === "Middle" && hPos === "Center" ? "Center" : `${vPos} ${hPos}`;
    parts.push(position);
  }

  return parts.length > 0 ? parts.join(", ") : "Location not specified";
}

// ─── Editing software estimation ─────────────────────────────────────────────

const SOFTWARE_CONFIDENCE_THRESHOLD = 0.55;

export function estimateEditingSource(signals = {}, metadata = {}) {
  const candidates = [];

  const pdfSignals = [
    metadata?.producer?.toLowerCase?.()?.includes("pdf"),
    metadata?.creator?.toLowerCase?.()?.includes("acrobat"),
    metadata?.creator?.toLowerCase?.()?.includes("foxit"),
    metadata?.creator?.toLowerCase?.()?.includes("pdf"),
    signals?.pdf_edit_probability > 0.5,
  ].filter(Boolean).length;
  if (pdfSignals >= 1) candidates.push({ software: "a PDF editor (e.g. Adobe Acrobat, Foxit)", confidence: 0.6 + pdfSignals * 0.1 });

  const psSignals = [
    metadata?.software?.toLowerCase?.()?.includes("photoshop"),
    metadata?.creator?.toLowerCase?.()?.includes("photoshop"),
    signals?.ela_score > 0.6,
    signals?.photoshop_probability > 0.5,
  ].filter(Boolean).length;
  if (psSignals >= 1) candidates.push({ software: "Adobe Photoshop", confidence: 0.55 + psSignals * 0.15 });

  const gimpSignals = [
    metadata?.software?.toLowerCase?.()?.includes("gimp"),
    metadata?.creator?.toLowerCase?.()?.includes("gimp"),
  ].filter(Boolean).length;
  if (gimpSignals >= 1) candidates.push({ software: "GIMP or similar open-source editor", confidence: 0.7 + gimpSignals * 0.1 });

  const canvaSignals = [
    metadata?.creator?.toLowerCase?.()?.includes("canva"),
    metadata?.producer?.toLowerCase?.()?.includes("canva"),
    signals?.canva_probability > 0.5,
  ].filter(Boolean).length;
  if (canvaSignals >= 1) candidates.push({ software: "Canva or a web-based editor", confidence: 0.7 + canvaSignals * 0.1 });

  const wordSignals = [
    metadata?.creator?.toLowerCase?.()?.includes("word"),
    metadata?.creator?.toLowerCase?.()?.includes("microsoft"),
    metadata?.producer?.toLowerCase?.()?.includes("office"),
  ].filter(Boolean).length;
  if (wordSignals >= 1) candidates.push({ software: "Microsoft Word or Office", confidence: 0.65 + wordSignals * 0.1 });

  const aiSignals = [
    signals?.ai_generated_probability > 0.7,
    signals?.gan_probability > 0.6,
  ].filter(Boolean).length;
  if (aiSignals >= 1) candidates.push({ software: "an AI image generation tool", confidence: 0.6 + aiSignals * 0.2 });

  const scannerSignals = [
    metadata?.model?.toLowerCase?.()?.includes("iphone"),
    metadata?.model?.toLowerCase?.()?.includes("android"),
    metadata?.model?.toLowerCase?.()?.includes("samsung"),
    signals?.mobile_scan_probability > 0.5,
  ].filter(Boolean).length;
  if (scannerSignals >= 1) candidates.push({ software: "a mobile scanner or phone camera app", confidence: 0.5 + scannerSignals * 0.15 });

  if (signals?.screenshot_probability > 0.5) {
    candidates.push({ software: "screenshot insertion", confidence: 0.55 + signals.screenshot_probability * 0.3 });
  }

  if (candidates.length === 0) return null;
  const best = candidates.sort((a, b) => b.confidence - a.confidence)[0];
  if (best.confidence < SOFTWARE_CONFIDENCE_THRESHOLD) return null;

  return {
    software: best.software,
    confidence: best.confidence,
    label: `Likely edited using ${best.software}`,
    confidencePct: Math.round(best.confidence * 100),
  };
}

// ─── Plain-language finding generator ────────────────────────────────────────

export function generatePlainFinding(region) {
  if (!region) return null;

  const score = Number(region.confidence_pct ?? region.confidence ?? region.score ?? 0);
  const confPct = score <= 1 ? Math.round(score * 100) : Math.round(score);
  const severity = getSeverityInfo(confPct);

  const editType = translateEditType(region.edit_type || region.manipulation || region.type);
  const bbox = region.bbox || region.bounding_box || region.coordinates || {};
  const nb = region.normalized_bbox;
  const effectiveBbox = nb || bbox;
  const locationText = getLocationDescription(effectiveBbox, region.page);

  const rawLabel = region.label || region.type || "";
  let whatHappened = editType;
  if (rawLabel && !/^(R|Region|ELA|Noise|GAN|Copy)\s*\d*/i.test(rawLabel) && rawLabel.length > 4) {
    whatHappened = translateEditType(rawLabel) || editType;
  }

  const reasons = [];
  if (region.reason) reasons.push(region.reason);
  if (region.investigation) {
    region.investigation.split("\n").map(l => l.trim()).filter(Boolean).slice(0, 2).forEach(l => reasons.push(l));
  }
  if (Array.isArray(region.evidence)) {
    region.evidence.slice(0, 2).forEach(e => reasons.push(e));
  }
  const plainReasons = reasons.slice(0, 3).map(r => translateTechTerm(r));

  const plainEnglish =
    region.plain_english_explanation ||
    region.plain_explanation ||
    (plainReasons.length > 0 ? plainReasons[0] : null) ||
    `${whatHappened} at ${locationText}.`;

  const verificationSteps = generateVerificationSteps(editType);

  return {
    id: region.id || region.region_id,
    label: region.label,
    whatHappened,
    locationText,
    page: region.page,
    bbox: effectiveBbox,
    plainEnglish,
    reasons: plainReasons,
    confidence: confPct,
    severity,
    editType,
    verificationSteps,
    detectors: region.detectors || (region.detector ? [region.detector] : ["AI Analysis"]),
    raw: region,
  };
}

export function generateVerificationSteps(editType) {
  const edit = String(editType || "").toLowerCase();
  if (edit.includes("signature")) {
    return [
      "Compare with a known genuine signature from the issuing person.",
      "Request the original physical document from the issuer.",
    ];
  }
  if (edit.includes("seal") || edit.includes("logo")) {
    return [
      "Verify the seal/logo against known authentic versions from the issuing authority.",
      "Contact the issuing organization to confirm document authenticity.",
    ];
  }
  if (edit.includes("amount") || edit.includes("price") || edit.includes("financial")) {
    return [
      "Verify the amount with the original transaction records or receipt.",
      "Request a certified copy of the original document from the issuer.",
    ];
  }
  if (edit.includes("date")) {
    return [
      "Cross-reference the date with transaction logs or official records.",
      "Contact the issuing authority to verify the original date.",
    ];
  }
  if (edit.includes("name")) {
    return [
      "Verify the name against official identity documents.",
      "Cross-reference with the issuing authority's records.",
    ];
  }
  if (edit.includes("face") || edit.includes("deepfake")) {
    return [
      "Compare with known authentic photographs of the individual.",
      "Request original ID documents for comparison.",
    ];
  }
  if (edit.includes("qr") || edit.includes("barcode")) {
    return [
      "Scan the QR/barcode and verify against the issuer's database.",
      "Compare with the original document's code.",
    ];
  }
  if (edit.includes("ai") || edit.includes("generated")) {
    return [
      "Request the original source photograph or document.",
      "Consider additional expert review for AI-generation determination.",
    ];
  }
  return [
    "Request the original document from the issuing authority.",
    "Compare with any independently verified copies.",
    "Consult a forensic document expert for physical examination.",
  ];
}

// ─── Jury verdict translator ──────────────────────────────────────────────────

const VERDICT_MAP = {
  tampered: "This document shows clear signs of manipulation.",
  forged: "This document appears to be forged.",
  manipulated: "This document has been digitally manipulated.",
  fake: "This document appears to be fraudulent.",
  authentic: "No manipulation detected — this document appears authentic.",
  genuine: "No manipulation detected — this document appears authentic.",
  real: "The AI system found no evidence of manipulation.",
  uncertain: "Analysis is inconclusive. Manual expert review is recommended.",
  inconclusive: "Analysis is inconclusive. Manual expert review is recommended.",
  suspicious: "This document contains suspicious elements requiring verification.",
  high_risk: "This document presents a HIGH risk of manipulation. Do not rely on it without verification.",
  medium_risk: "This document contains elements that require verification.",
  low_risk: "This document shows minor anomalies. Proceed with caution.",
  unknown: "Analysis is pending or incomplete.",
};

export function translateVerdict(verdict) {
  if (!verdict) return null;
  const key = String(verdict).toLowerCase().trim().replace(/[\s]+/g, "_");
  return VERDICT_MAP[key] || VERDICT_MAP[verdict.toLowerCase()] || verdict;
}

// ─── Detector name translator ─────────────────────────────────────────────────

const DETECTOR_DISPLAY_MAP = {
  ELA: "Editing Artifacts",
  Noise: "Pixel Inconsistencies",
  "Copy Move": "Copied Content",
  Copy_Move: "Copied Content",
  OCR: "Text Analysis",
  Metadata: "Document History",
  GAN: "AI Generation Detection",
  Signature: "Signature Check",
  Logo: "Logo Analysis",
  Forgery: "Forgery Detection",
  "Deep Learning": "Neural Network Analysis",
  Wavelet: "Frequency Analysis",
  Ensemble: "Combined AI Analysis",
  Face: "Facial Analysis",
  Deepfake: "Face Manipulation Detection",
};

export function translateDetectorName(name) {
  return DETECTOR_DISPLAY_MAP[name] || translateTechTerm(name);
}

// ─── View mode label translator ───────────────────────────────────────────────

export const VIEW_MODE_LABELS = {
  original: "Original Evidence",
  heatmap: "Manipulation Heatmap",
  ela: "Editing Detection Map",
  noise: "Inconsistency Map",
  copy_move: "Copied Content Regions",
  forgery_mask: "Manipulation Areas",
  segmentation_overlay: "Evidence Overlay",
  bounding_boxes: "Detected Regions",
  compare: "Before / After Comparison",
};

export function translateViewMode(mode) {
  return VIEW_MODE_LABELS[mode] || mode;
}

// ─── Region label humanizer ───────────────────────────────────────────────────

export function humanizeRegionLabel(region, index = 0) {
  const rawLabel = region?.label || "";
  if (rawLabel && !/^(R|Region|ELA|Noise|GAN|Copy)\s*\d*/i.test(rawLabel) && rawLabel.length > 4) {
    return rawLabel;
  }
  const editType = region?.edit_type || region?.manipulation || region?.type;
  if (editType) {
    const translated = EDIT_TYPE_MAP[String(editType).toLowerCase().replace(/[- ]/g, "_")];
    if (translated) return translated;
  }
  const ll = rawLabel.toLowerCase();
  if (ll.includes("signature")) return "Signature Area";
  if (ll.includes("logo")) return "Logo Region";
  if (ll.includes("seal")) return "Official Seal";
  if (ll.includes("price") || ll.includes("amount")) return "Amount Field";
  if (ll.includes("face")) return "Face Region";
  if (ll.includes("qr")) return "QR Code";
  if (ll.includes("text")) return "Text Region";
  return `Finding ${index + 1}`;
}
