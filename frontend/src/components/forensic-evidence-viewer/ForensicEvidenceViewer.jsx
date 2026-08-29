import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AlertCircle, CheckCircle2, FileWarning, Link2, Loader2, Trash2 } from "lucide-react";

import { ErrorBoundary } from "../ErrorBoundary";
import EvidencePanel from "./EvidencePanel";
import InvestigationCanvas from "./InvestigationCanvas";
import { resolveViews } from "./forensicData";
import ComparisonNavigator from "../investigation/ComparisonNavigator";
import { buildCanonicalFindings } from "./forensicFindingSchema";
import { useBackend } from "../../context/BackendConnectivity";
import {
  deleteEvidenceReference,
  getArtifactUrl,
  getEvidenceReference,
  getLocalization,
  linkEvidenceReference,
} from "../../services/api";

function resolvePageImageUrl(path) {
  if (!path || typeof path !== "string") return "";
  const normalized = path.replaceAll("\\", "/");
  const dataMarker = normalized.toLowerCase().lastIndexOf("/data/");
  if (dataMarker >= 0) {
    return getArtifactUrl(normalized.slice(dataMarker + 1));
  }
  return getArtifactUrl(normalized);
}

function ForensicEvidenceViewer({
  evidenceId,
  analysisResult = null,
  findings = null,
  focusFindingId = null,
  mediaType = "document",
  onEvidenceChanged,
  onRegionCountChange,
  renderSection,
}) {
  const { online } = useBackend();
  const viewerMediaType = String(mediaType).toLowerCase().includes("video")
    ? "video"
    : String(mediaType).toLowerCase().includes("image")
      ? "image"
      : "document";
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [localization, setLocalization] = useState(null);
  const [selectedFindingId, setSelectedFindingId] = useState(null);
  const [findingFilter, setFindingFilter] = useState("all");
  const [referenceResponse, setReferenceResponse] = useState(null);
  const [referenceId, setReferenceId] = useState("");
  const [referenceMessage, setReferenceMessage] = useState("");
  const [referenceBusy, setReferenceBusy] = useState(false);
  const canvasRef = useRef(null);

  const regions = useMemo(
    () =>
      Array.isArray(findings)
        ? findings
        : buildCanonicalFindings({
            analysisResult,
            localization,
            evidenceId,
            mediaType: viewerMediaType,
          }),
    [analysisResult, evidenceId, findings, localization, viewerMediaType]
  );
  const views = useMemo(
    () => resolveViews(localization, analysisResult),
    [localization, analysisResult]
  );
  const viewUrls = useMemo(() => {
    const toUrl = (value) => {
      if (!value || typeof value !== "string") return "";
      const filename = value.replaceAll("\\", "/").split("/").pop();
      return value.startsWith("/api/")
        ? getArtifactUrl(value)
        : evidenceId
          ? getArtifactUrl(`/api/localization/${evidenceId}/file/${filename}`)
          : "";
    };
    return {
      overlay: toUrl(views.combined_overlay || views.combinedOverlay || views.annotated),
      mask: toUrl(views.localization_mask || views.mask_binary || views.forgery_mask),
      heatmap: toUrl(views.forensic_heatmap || views.heatmap || views.localization_heatmap),
      original: toUrl(views.original),
    };
  }, [evidenceId, views]);

  const filteredRegions = useMemo(() => {
    if (findingFilter === "all") return regions;
    return regions.filter((region) => {
      const value = `${region.severity || ""} ${region.type || ""} ${region.editType || ""} ${region.category || ""}`.toLowerCase();
      return value.includes(findingFilter);
    });
  }, [findingFilter, regions]);
  const activeRegion =
    filteredRegions.find((region) => region.findingId === selectedFindingId) ||
    filteredRegions[0] ||
    null;

  useEffect(() => {
    onRegionCountChange?.(regions.length);
  }, [regions.length, onRegionCountChange]);

  const loadLocalization = useCallback(async () => {
    if (!evidenceId || !online) return;
    setLoading(true);
    setError("");
    try {
      const response = await getLocalization(evidenceId);
      setLocalization(response || null);
    } catch (loadError) {
      setError(
        loadError?.message ||
          "Localization data is unavailable. The stored investigation remains accessible."
      );
    } finally {
      setLoading(false);
    }
  }, [evidenceId, online]);

  useEffect(() => {
    const timer = window.setTimeout(loadLocalization, 0);
    return () => window.clearTimeout(timer);
  }, [loadLocalization]);

  useEffect(() => {
    let active = true;
    getEvidenceReference(evidenceId)
      .then((response) => {
        if (active) setReferenceResponse(response);
      })
      .catch(() => {
        if (active) setReferenceResponse(null);
      });
    return () => { active = false; };
  }, [evidenceId]);

  const documentPages = useMemo(
    () =>
      analysisResult?.documentAnalysis?.pages ||
      analysisResult?.investigation?.document_analysis?.pages ||
      analysisResult?.analysis?.document_intelligence?.pages ||
      [],
    [analysisResult]
  );

  const viewerUrl = useMemo(() => {
    if (viewerMediaType === "video") {
      return evidenceId ? getArtifactUrl(`/api/localization/${evidenceId}/original`) : null;
    }
    const candidate =
      views?.annotated ||
      views?.localization_annotated ||
      views?.original ||
      analysisResult?.artifacts?.localization_annotated;
    if (candidate) return getArtifactUrl(candidate);
    return evidenceId ? `/api/evidence/${evidenceId}/artifact/original` : null;
  }, [views, analysisResult, evidenceId, viewerMediaType]);
  const viewerPages = useMemo(() => {
    const pages = documentPages
      .map((page, index) => {
        const image =
          page?.image ||
          page?.page_image ||
          page?.rendered_image ||
          page?.artifact;
        if (!image) return null;
        return {
          ...page,
          pageNumber: page?.page_number ?? page?.page ?? index + 1,
          imageUrl: resolvePageImageUrl(image),
        };
      })
      .filter(Boolean);
    if (pages.length > 0) return pages;
    return viewerUrl
      ? [{ pageNumber: 1, imageUrl: viewerUrl }]
      : [];
  }, [documentPages, viewerUrl]);
  const reference = referenceResponse?.reference || null;
  const referencePath =
    reference?.reference_url ||
    reference?.comparison?.artifact_urls?.reference_original;
  const referenceUrl = referencePath
    ? getArtifactUrl(referencePath)
    : null;
  const examinedPath =
    reference?.examined_url ||
    reference?.comparison?.artifact_urls?.examined_original;
  const examinedUrl = examinedPath
    ? getArtifactUrl(examinedPath)
    : viewerUrl;
  const differencePath =
    reference?.difference_url ||
    reference?.comparison?.artifact_urls?.difference ||
    reference?.comparison?.difference_url ||
    reference?.comparison_url;
  const differenceUrl = differencePath ? getArtifactUrl(differencePath) : null;
  const compatible =
    reference?.compatibility === true ||
    reference?.compatibility?.compatible === true ||
    reference?.comparison?.page_image_compatibility?.compatible === true ||
    String(reference?.compatibility?.status || reference?.compatibility || "")
      .toLowerCase() === "compatible";
  const framesPerSecond =
    analysisResult?.videoAnalysis?.fps ||
    analysisResult?.investigation?.video_analysis?.fps ||
    analysisResult?.analysis?.video?.fps ||
    null;

  const selectFinding = useCallback((region) => {
    setSelectedFindingId(region?.findingId || null);
    canvasRef.current?.focusFinding(region);
    document
      .getElementById("document-viewer")
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  useEffect(() => {
    if (!focusFindingId) return;
    const target = regions.find(
      (region) =>
        region.findingId === focusFindingId ||
        region.id === focusFindingId ||
        region.raw?.id === focusFindingId ||
        region.raw?.finding_id === focusFindingId
    );
    if (!target) return;
    const timer = window.setTimeout(() => selectFinding(target), 0);
    return () => window.clearTimeout(timer);
  }, [focusFindingId, regions, selectFinding]);

  async function submitReference(event) {
    event.preventDefault();
    const candidate = referenceId.trim();
    if (!candidate || candidate === evidenceId) {
      setReferenceMessage(
        candidate === evidenceId
          ? "Reference evidence must be a different evidence record."
          : "Enter an existing evidence ID."
      );
      return;
    }
    setReferenceBusy(true);
    setReferenceMessage("");
    try {
      const response = await linkEvidenceReference(evidenceId, candidate);
      if (response?.unavailable) {
        setReferenceMessage("Reference linking is unavailable; no link was created.");
      } else {
        setReferenceResponse(response);
        setReferenceId("");
        setReferenceMessage("Reference evidence linked.");
        await onEvidenceChanged?.();
      }
    } catch (linkError) {
      setReferenceMessage(linkError?.message || "Reference evidence could not be linked.");
    } finally {
      setReferenceBusy(false);
    }
  }

  async function removeReference() {
    setReferenceBusy(true);
    setReferenceMessage("");
    try {
      const response = await deleteEvidenceReference(evidenceId);
      if (response?.unavailable) {
        setReferenceMessage("Reference removal is unavailable.");
      } else {
        setReferenceResponse(null);
        setReferenceMessage("Reference link removed.");
        await onEvidenceChanged?.();
      }
    } catch (removeError) {
      setReferenceMessage(removeError?.message || "Reference link could not be removed.");
    } finally {
      setReferenceBusy(false);
    }
  }

  if (!evidenceId) return null;

  const findingsContent = (
    <div className="forge-findings-panel">
      {error && (
        <div className="forge-inline-notice forge-inline-notice-warning">
          <AlertCircle className="h-4 w-4" />
          <span>{error}</span>
        </div>
      )}
      <div className="forge-finding-filters" role="toolbar" aria-label="Filter findings">
        {["all", "critical", "high", "medium", "low", "signature", "text", "image", "metadata", "deepfake", "copy"].map((filter) => (
          <button
            key={filter}
            type="button"
            className={findingFilter === filter ? "forge-filter-active" : ""}
            onClick={() => setFindingFilter(filter)}
            aria-pressed={findingFilter === filter}
          >
            {filter === "copy" ? "Copy-Move" : filter[0].toUpperCase() + filter.slice(1)}
          </button>
        ))}
      </div>
      {loading && regions.length === 0 ? (
        <div className="forge-compact-loading">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading localized findings
        </div>
      ) : filteredRegions.length > 0 ? (
        <div className="forge-findings-list">
          {filteredRegions.map((region, index) => (
            <article
              key={region.findingId || `finding-${index}`}
              onClick={() => selectFinding(region)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") selectFinding(region);
              }}
              role="button"
              tabIndex={0}
              className={`forge-finding-button ${
                activeRegion?.findingId === region.findingId
                  ? "forge-finding-button-active"
                  : ""
              }`}
            >
              <EvidencePanel
                region={region}
                isSelected={activeRegion?.findingId === region.findingId}
              />
            </article>
          ))}
        </div>
      ) : (
        <div className="forge-empty-result">
          <CheckCircle2 className="h-5 w-5" />
          <div>
            <strong>No localized forensic finding available</strong>
            <p>
              The available analysis did not produce a reviewable region. This
              does not establish that the evidence is authentic or unmodified.
            </p>
          </div>
        </div>
      )}
    </div>
  );

  const viewerContent = (
    <div className="forge-viewer-shell">
      {!online ? (
        <div className="forge-empty-result forge-empty-result-warning">
          <FileWarning className="h-5 w-5" />
          <div>
            <strong>Viewer temporarily unavailable</strong>
            <p>Reconnect to retrieve the secured evidence artifact.</p>
          </div>
        </div>
      ) : (
        <>
        <div className="forge-review-workspace">
          <InvestigationCanvas
            key={`${evidenceId}-${viewerUrl || "pending"}`}
            ref={canvasRef}
            pages={viewerPages}
            regions={filteredRegions}
            selectedRegion={activeRegion}
            onSelectRegion={(region) => setSelectedFindingId(region?.findingId || null)}
            loading={loading}
            mediaType={viewerMediaType}
            mediaUrl={viewerUrl}
            viewUrls={viewUrls}
            framesPerSecond={framesPerSecond}
          />
          <aside className="forge-viewer-evidence-rail" aria-label="Selected evidence finding">
            {activeRegion ? (
              <>
                <span className="forge-label">
                  Finding {String(activeRegion.number || 1).padStart(2, "0")}
                </span>
                <h3>{activeRegion.title}</h3>
                <p className="forge-viewer-reference">
                  {activeRegion.page ? `Page ${activeRegion.page}` : "Page not specified"}
                  {" · "}
                  {activeRegion.location}
                </p>
                <dl>
                  <div>
                    <dt>Evidence strength</dt>
                    <dd>{activeRegion.severity || "Not recorded"}</dd>
                  </div>
                  <div>
                    <dt>Risk</dt>
                    <dd>{activeRegion.severity}</dd>
                  </div>
                </dl>
                <p>{activeRegion.whatChanged || activeRegion.explanation}</p>
                <p className="forge-viewer-detail-label">Technical reason</p>
                <p>{activeRegion.why || activeRegion.explanation}</p>
                <p className="forge-viewer-detail-label">Recommendation</p>
                <p>{activeRegion.recommendedReview?.[0] || activeRegion.recommendation || "Independent review recommended."}</p>
              </>
            ) : (
              <p>Select a finding to inspect its location and supporting explanation.</p>
            )}
          </aside>
        </div>
        <div className="forge-reference-control">
          <div>
            <span className="forge-label">Reference evidence</span>
            {reference ? (
              <p>
                Linked to{" "}
                <strong>
                  {reference.reference_evidence_id || reference.reference_id}
                </strong>.
                Reference authenticity: {reference.authenticity_status || "not independently verified"}.
              </p>
            ) : (
              <p>No reference evidence is linked. Comparison views are not shown.</p>
            )}
          </div>
          {reference ? (
            <button type="button" onClick={removeReference} disabled={referenceBusy}>
              <Trash2 className="h-3.5 w-3.5" />
              Remove link
            </button>
          ) : (
            <form onSubmit={submitReference}>
              <label className="sr-only" htmlFor="reference-evidence-id">Reference evidence ID</label>
              <input
                id="reference-evidence-id"
                value={referenceId}
                onChange={(event) => setReferenceId(event.target.value)}
                placeholder="Existing evidence ID"
                disabled={referenceBusy}
              />
              <button type="submit" disabled={referenceBusy || !referenceId.trim()}>
                <Link2 className="h-3.5 w-3.5" />
                Link
              </button>
            </form>
          )}
          {referenceMessage && <span role="status">{referenceMessage}</span>}
        </div>
        {reference && referenceUrl && (
          <ComparisonNavigator
            referenceUrl={referenceUrl}
            examinedUrl={examinedUrl}
            differenceUrl={differenceUrl}
            compatible={compatible}
            authenticityStatus={reference.authenticity_status}
            mediaType={viewerMediaType}
            currentPage={activeRegion?.page || 1}
            regions={regions}
            focusedRegion={activeRegion}
          />
        )}
        </>
      )}
    </div>
  );

  return (
    <ErrorBoundary>
      {renderSection ? (
        <>
          {renderSection("findings", findingsContent)}
          {renderSection("viewer", viewerContent)}
        </>
      ) : (
        <>
          {findingsContent}
          {viewerContent}
        </>
      )}
    </ErrorBoundary>
  );
}

export default ForensicEvidenceViewer;
