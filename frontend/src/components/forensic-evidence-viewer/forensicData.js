/**
 * Safe accessors for forensic viewer data — never throws on missing analysis payloads.
 */

export function asArray(value) {
  return Array.isArray(value) ? value : [];
}

export function asObject(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function firstNonEmptyArray(...candidates) {
  for (const candidate of candidates) {
    if (Array.isArray(candidate) && candidate.length > 0) {
      return candidate;
    }
  }
  for (const candidate of candidates) {
    if (Array.isArray(candidate)) {
      return candidate;
    }
  }
  return [];
}

export function resolveRegions(loc, analysisResult) {
  const analysis = asObject(analysisResult?.analysis);
  const localization = asObject(analysis?.localization);
  const evidence = asObject(analysisResult?.evidence);

  return firstNonEmptyArray(
    loc?.regions,
    analysisResult?.jury?.forensic_dossier?.findings,
    analysisResult?.forensic_dossier?.findings,
    analysisResult?.localization?.regions,
    localization?.regions,
    analysis?.regions,
    evidence?.regions,
    analysisResult?.regions,
    loc?.detected_regions
  );
}

export function resolveViews(loc, analysisResult) {
  const analysis = asObject(analysisResult?.analysis);
  const candidates = [
    loc?.views,
    loc?.overlay_files,
    loc?.files,
    analysisResult?.localization?.views,
    analysis?.localization?.views,
  ];
  for (const candidate of candidates) {
    const obj = asObject(candidate);
    if (Object.keys(obj).length > 0) {
      return obj;
    }
  }
  return {};
}

export function resolveLocalization(loc, analysisResult) {
  if (loc && typeof loc === "object" && Object.keys(loc).length > 0) {
    return asObject(loc);
  }
  const analysis = asObject(analysisResult?.analysis);
  const fromAnalysis = asObject(analysisResult?.localization);
  if (Object.keys(fromAnalysis).length > 0) return fromAnalysis;
  return asObject(analysis?.localization);
}

export function resolveHeatmapUrl(views, evidenceId) {
  const path =
    views?.heatmap ||
    views?.localization_heatmap ||
    views?.attention ||
    null;
  return path || (evidenceId ? `/api/localization/${evidenceId}/file/localization_heatmap.png` : null);
}

export function resolveTimeline(loc, videoResult) {
  const intervals = loc?.video_timeline?.suspicious_intervals;
  if (Array.isArray(intervals) && intervals.length > 0) {
    return intervals;
  }
  return asArray(videoResult?.frames);
}

export function resolveFindings(analysisResult, loc) {
  const analysis = asObject(analysisResult?.analysis);
  return firstNonEmptyArray(
    loc?.findings,
    analysisResult?.jury?.forensic_dossier?.findings,
    analysisResult?.forensic_dossier?.findings,
    analysis?.findings,
    analysisResult?.findings,
    analysis?.risk_fusion?.findings
  );
}

export function resolveExplanations(analysisResult, loc, dashboard) {
  const analysis = asObject(analysisResult?.analysis);
  return {
    detailed:
      loc?.detailed_investigation ||
      loc?.explanation ||
      dashboard?.explanation ||
      analysis?.detailed_investigation ||
      analysis?.explanation ||
      null,
    explainability: asArray(
      analysis?.risk_fusion?.explainability ||
        analysis?.explainability ||
        loc?.explainability
    ),
  };
}

export function resolveMetrics(loc, analysisResult) {
  const panel = asObject(loc?.investigation_panel);
  const analysis = asObject(analysisResult?.analysis);
  return {
    confidence:
      panel?.detector_confidence ??
      analysis?.confidence ??
      analysisResult?.confidence ??
      null,
    forgeryProbability: panel?.forgery_probability ?? null,
    riskScore:
      analysis?.risk_score ??
      analysisResult?.risk?.score ??
      panel?.forgery_probability ??
      null,
    verdict: panel?.verdict ?? analysis?.verdict ?? null,
  };
}

export function normalizeVideoIntervals(timeline) {
  return asArray(timeline)
    .filter((f) => f && (f.timestamp != null || f.risk != null || f.score != null))
    .map((f) => ({
      timestamp: f.timestamp ?? 0,
      frame_number: f.frame_number,
      score: f.risk ?? f.score ?? 0.5,
      reason: f.reason || "Suspicious keyframe forensic signals",
    }));
}
