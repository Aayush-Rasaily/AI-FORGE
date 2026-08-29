import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  ChevronLeft,
  ChevronRight,
  ImageOff,
  RotateCcw,
  ZoomIn,
  ZoomOut,
} from "lucide-react";

function pageOf(region) {
  const page = Number(region?.page ?? region?.page_number ?? 1);
  return Number.isFinite(page) && page > 0 ? page : 1;
}

function rawBox(region) {
  const value = region?.bbox || region?.normalized_bbox || region?.bounding_box;
  if (Array.isArray(value) && Array.isArray(value[0])) {
    const xs = value.map((point) => Number(point?.[0]) || 0);
    const ys = value.map((point) => Number(point?.[1]) || 0);
    const x = Math.min(...xs);
    const y = Math.min(...ys);
    return {
      x,
      y,
      width: Math.max(...xs) - x,
      height: Math.max(...ys) - y,
    };
  }
  if (Array.isArray(value) && value.length >= 4) {
    const [x, y, third, fourth] = value.map(Number);
    const format = String(region?.bbox_format || region?.coordinate_format || "").toLowerCase();
    if (format.includes("xyxy")) {
      return { x, y, width: third - x, height: fourth - y };
    }
    return { x, y, width: third, height: fourth };
  }
  if (value && typeof value === "object") {
    if (value.x2 != null && value.y2 != null) {
      return {
        x: Number(value.x ?? value.x1) || 0,
        y: Number(value.y ?? value.y1) || 0,
        width: Number(value.x2) - Number(value.x ?? value.x1),
        height: Number(value.y2) - Number(value.y ?? value.y1),
      };
    }
    return {
      x: Number(value.x ?? value.left) || 0,
      y: Number(value.y ?? value.top) || 0,
      width: Number(value.width ?? value.w) || 0,
      height: Number(value.height ?? value.h) || 0,
    };
  }
  return null;
}

function relatedBoxesOf(region, width, height) {
  const extras = region?.relatedBboxes || [];
  const comparison = region?.originalComparison?.pairedRegions;
  const boxes = extras.length
    ? extras
    : [comparison?.regionA, comparison?.regionB].filter(Boolean);
  return boxes
    .map((box) => boxOf({ bbox: box }, width, height))
    .filter((box) => box && box.width > 0 && box.height > 0);
}

function boxOf(region, width, height) {
  const box = rawBox(region);
  if (!box) return null;
  const normalized =
    region?.bbox?.coordinateSpace === "normalized" ||
    Math.max(
      Math.abs(box.x),
      Math.abs(box.y),
      Math.abs(box.width),
      Math.abs(box.height)
    ) <= 1;
  const x = normalized ? box.x * width : box.x;
  const y = normalized ? box.y * height : box.y;
  const boxWidth = normalized ? box.width * width : box.width;
  const boxHeight = normalized ? box.height * height : box.height;
  const left = Math.max(0, Math.min(width, x));
  const top = Math.max(0, Math.min(height, y));
  const right = Math.max(0, Math.min(width, x + boxWidth));
  const bottom = Math.max(0, Math.min(height, y + boxHeight));
  return {
    x: left,
    y: top,
    width: Math.max(0, right - left),
    height: Math.max(0, bottom - top),
  };
}

function severityClass(region) {
  const severity = String(region?.severity || "").toLowerCase();
  if (severity.includes("critical") || severity.includes("high")) return "high";
  if (severity.includes("medium")) return "medium";
  return "low";
}

function sameFinding(left, right) {
  if (!left || !right) return false;
  return (
    left === right ||
    (left.findingId && left.findingId === right.findingId) ||
    (left.id && left.id === right.id)
  );
}

const InvestigationCanvas = forwardRef(function InvestigationCanvas(
  {
    pages = [],
    regions = [],
    selectedRegion,
    onSelectRegion,
    loading,
    mediaType = "document",
    mediaUrl = null,
    viewUrls = {},
    framesPerSecond = null,
  },
  ref
) {
  const preparedPages = useMemo(
    () =>
      pages.map((page, index) => ({
        ...page,
        pageNumber: Number(page.pageNumber ?? page.page_number ?? index + 1),
      })),
    [pages]
  );
  const initialPage = pageOf(selectedRegion);
  const [pageNumber, setPageNumber] = useState(initialPage);
  const [zoom, setZoom] = useState(1);
  const [natural, setNatural] = useState({ width: 1, height: 1 });
  const [imageError, setImageError] = useState(false);
  const [loadedPage, setLoadedPage] = useState(null);
  const [pulseKey, setPulseKey] = useState(0);
  const [videoTime, setVideoTime] = useState(0);
  const [displayMode, setDisplayMode] = useState("overlay");
  const viewportRef = useRef(null);
  const documentRef = useRef(null);
  const videoRef = useRef(null);
  const pendingFocusRef = useRef(null);

  const availablePageNumbers = preparedPages.map((page) => page.pageNumber);
  const safePageNumber = availablePageNumbers.includes(pageNumber)
    ? pageNumber
    : availablePageNumbers[0] || 1;
  const activePage =
    preparedPages.find((page) => page.pageNumber === safePageNumber) ||
    preparedPages[0] ||
    null;
  const pageRegions = regions.filter((region) => pageOf(region) === safePageNumber);
  const selectedIndex = selectedRegion
    ? regions.findIndex(
        (region) =>
          sameFinding(region, selectedRegion)
      )
    : -1;
  const videoHasTemporalAlignment =
    selectedRegion?.timestamp != null ||
    (selectedRegion?.frame != null && Number(framesPerSecond) > 0);
  const selectedVideoTime = selectedRegion?.timestamp != null
    ? Number(selectedRegion.timestamp)
    : selectedRegion?.frame != null && Number(framesPerSecond) > 0
      ? Number(selectedRegion.frame) / Number(framesPerSecond)
      : null;
  const videoAtSelectedFinding =
    Number.isFinite(selectedVideoTime) &&
    Math.abs(videoTime - selectedVideoTime) <= 0.5;

  const scrollToRegion = useCallback(
    (region, smooth = true, dimensions = natural) => {
      const viewport = viewportRef.current;
      const documentNode = documentRef.current;
      const box = boxOf(region, dimensions.width, dimensions.height);
      if (!viewport || !documentNode || !box) return;
      const scaleX = documentNode.offsetWidth / dimensions.width;
      const scaleY = documentNode.offsetHeight / dimensions.height;
      const left =
        (box.x + box.width / 2) * scaleX - viewport.clientWidth / 2;
      const top =
        (box.y + box.height / 2) * scaleY - viewport.clientHeight / 2;
      viewport.scrollTo({
        left: Math.max(0, left),
        top: Math.max(0, top),
        behavior: smooth ? "smooth" : "auto",
      });
    },
    [natural]
  );

  const focusFinding = useCallback(
    (region) => {
      if (!region) return;
      const targetPage = pageOf(region);
      const box = rawBox(region);
      setPageNumber(targetPage);
      setImageError(false);
      if (targetPage !== safePageNumber) setLoadedPage(null);
      setZoom(box ? 2 : 1);
      setPulseKey((value) => value + 1);
      onSelectRegion?.(region);
      pendingFocusRef.current = region;
      if (mediaType === "video" && videoRef.current) {
        const directTimestamp = Number(region.timestamp);
        const derivedTimestamp =
          region.frame != null && Number(framesPerSecond) > 0
            ? Number(region.frame) / Number(framesPerSecond)
            : null;
        const target = Number.isFinite(directTimestamp) ? directTimestamp : derivedTimestamp;
        if (Number.isFinite(target)) videoRef.current.currentTime = Math.max(0, target);
      }
      if (targetPage === safePageNumber) {
        window.setTimeout(() => scrollToRegion(region), 120);
      }
    },
    [framesPerSecond, mediaType, onSelectRegion, safePageNumber, scrollToRegion]
  );

  useImperativeHandle(ref, () => ({ focusFinding }), [focusFinding]);

  useEffect(() => {
    if (!selectedRegion) return;
    const targetPage = pageOf(selectedRegion);
    if (mediaType !== "video" && targetPage !== safePageNumber) {
      setPageNumber(targetPage);
      setLoadedPage(null);
    }
    if (mediaType === "video" && videoRef.current) {
      const timestamp = Number(selectedRegion.timestamp);
      const fromFrame =
        selectedRegion.frame != null && Number(framesPerSecond) > 0
          ? Number(selectedRegion.frame) / Number(framesPerSecond)
          : null;
      const target = Number.isFinite(timestamp) ? timestamp : fromFrame;
      if (Number.isFinite(target)) videoRef.current.currentTime = Math.max(0, target);
    }
  }, [framesPerSecond, mediaType, safePageNumber, selectedRegion]);

  function moveFinding(direction) {
    if (regions.length === 0) return;
    const nextIndex =
      selectedIndex < 0
        ? 0
        : (selectedIndex + direction + regions.length) % regions.length;
    focusFinding(regions[nextIndex]);
  }

  function movePage(direction) {
    const currentIndex = availablePageNumbers.indexOf(safePageNumber);
    const next = availablePageNumbers[currentIndex + direction];
    if (next == null) return;
    setPageNumber(next);
    setZoom(1);
    setImageError(false);
    setLoadedPage(null);
    viewportRef.current?.scrollTo({ top: 0, left: 0, behavior: "auto" });
  }

  function reset() {
    setZoom(1);
    setImageError(false);
    viewportRef.current?.scrollTo({ top: 0, left: 0, behavior: "auto" });
  }

  const activeBox = selectedRegion
    ? boxOf(selectedRegion, natural.width, natural.height)
    : null;
  const tooltipStyle = activeBox
    ? {
        left: `${Math.min(50, Math.max(2, (activeBox.x / natural.width) * 100))}%`,
        top: `${Math.min(
          72,
          Math.max(2, ((activeBox.y + activeBox.height) / natural.height) * 100 + 1)
        )}%`,
      }
    : null;
  const selectedImageUrl =
    safePageNumber === 1
      ? viewUrls[displayMode] || activePage?.imageUrl
      : activePage?.imageUrl;

  return (
    <div className="forge-canvas">
      <div className="forge-canvas-toolbar" aria-label="Evidence review controls">
        {mediaType !== "video" && <div className="forge-canvas-control-group">
          <button
            type="button"
            onClick={() => movePage(-1)}
            disabled={availablePageNumbers.indexOf(safePageNumber) <= 0}
            aria-label="Previous page"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span>
            Page {safePageNumber} of {Math.max(1, preparedPages.length)}
          </span>
          <button
            type="button"
            onClick={() => movePage(1)}
            disabled={
              availablePageNumbers.indexOf(safePageNumber) >=
              availablePageNumbers.length - 1
            }
            aria-label="Next page"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>}

        <div className="forge-canvas-control-group">
          <button
            type="button"
            onClick={() => setZoom((value) => Math.max(0.6, value - 0.2))}
            aria-label="Zoom out"
          >
            <ZoomOut className="h-4 w-4" />
          </button>
          <span>{Math.round(zoom * 100)}%</span>
          <button
            type="button"
            onClick={() => setZoom((value) => Math.min(3, value + 0.2))}
            aria-label="Zoom in"
          >
            <ZoomIn className="h-4 w-4" />
          </button>
          <button type="button" onClick={reset} aria-label="Reset document view">
            <RotateCcw className="h-4 w-4" />
            <span>Reset</span>
          </button>
          <button type="button" onClick={() => setZoom(1)} aria-label="Fit evidence to view">
            <span>Fit</span>
          </button>
        </div>

        <div className="forge-canvas-control-group forge-canvas-findings-nav">
          <button
            type="button"
            disabled={regions.length === 0}
            onClick={() => moveFinding(-1)}
            aria-label="Previous finding"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span>
            Finding {selectedIndex >= 0 ? selectedIndex + 1 : 0} of {regions.length}
          </span>
          <button
            type="button"
            disabled={regions.length === 0}
            onClick={() => moveFinding(1)}
            aria-label="Next finding"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>

        <div className="forge-canvas-control-group" aria-label="Evidence layers">
          {[
            ["overlay", "Overlay"],
            ["mask", "Mask"],
            ["heatmap", "Heatmap"],
          ].map(([mode, label]) => (
            <button
              key={mode}
              type="button"
              className={displayMode === mode ? "forge-canvas-control-active" : ""}
              onClick={() => setDisplayMode(mode)}
              disabled={!viewUrls[mode]}
              aria-pressed={displayMode === mode}
              aria-label={`Toggle ${label.toLowerCase()}`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div ref={viewportRef} className="forge-canvas-viewport">
        {loading && !(mediaType === "video" ? mediaUrl : selectedImageUrl) ? (
          <div className="forge-canvas-message">Retrieving secured evidence…</div>
        ) : !(mediaType === "video" ? mediaUrl : selectedImageUrl) || imageError ? (
          <div className="forge-canvas-message">
            <ImageOff className="h-6 w-6" />
            <strong>Evidence page unavailable</strong>
            <span>The investigation findings remain available for review.</span>
          </div>
        ) : mediaType === "video" ? (
          <div
            ref={documentRef}
            className="forge-canvas-document forge-video-document"
            style={{ width: `${zoom * 100}%` }}
          >
            <video
              ref={videoRef}
              src={mediaUrl}
              controls
              preload="metadata"
              onLoadedMetadata={(event) => {
                const dimensions = {
                  width: event.currentTarget.videoWidth || 1,
                  height: event.currentTarget.videoHeight || 1,
                };
                setNatural(dimensions);
                setLoadedPage(1);
                setImageError(false);
              }}
              onError={() => setImageError(true)}
              onTimeUpdate={(event) =>
                setVideoTime(event.currentTarget.currentTime)
              }
            >
              Your browser does not support evidence video playback.
            </video>
            {selectedRegion && !videoHasTemporalAlignment && (
              <span className="forge-video-alignment-note">
                Frame alignment unavailable; region overlay withheld.
              </span>
            )}
            {loadedPage === 1 &&
              videoHasTemporalAlignment &&
              videoAtSelectedFinding && (
              <svg
                viewBox={`0 0 ${natural.width} ${natural.height}`}
                aria-label="Evidence annotations for video"
                className="forge-video-overlay"
              >
                {regions
                  .filter((region) => sameFinding(selectedRegion, region))
                  .map((region, index) => {
                  const box = boxOf(region, natural.width, natural.height);
                  if (!box || box.width <= 0 || box.height <= 0) return null;
                  const active = sameFinding(selectedRegion, region);
                  return (
                    <g
                      key={`${region.findingId || index}-${active ? pulseKey : "idle"}`}
                      role="button"
                      tabIndex="0"
                      className={`forge-region-group forge-region-${severityClass(region)}`}
                      onClick={() => focusFinding(region)}
                    >
                      <title>{region.title}</title>
                      <rect
                        x={box.x}
                        y={box.y}
                        width={box.width}
                        height={box.height}
                        className={active ? "forge-region-active" : "forge-region"}
                      />
                      <text x={box.x + 5} y={box.y + 16}>{region.number || index + 1}</text>
                    </g>
                  );
                })}
              </svg>
            )}
          </div>
        ) : (
          <div
            ref={documentRef}
            className="forge-canvas-document"
            style={{ width: `${zoom * 100}%` }}
          >
            <img
              src={selectedImageUrl}
              alt={`Evidence page ${safePageNumber}`}
              draggable={false}
              onLoad={(event) => {
                const dimensions = {
                  width: event.currentTarget.naturalWidth || activePage.width || 1,
                  height: event.currentTarget.naturalHeight || activePage.height || 1,
                };
                setNatural(dimensions);
                setImageError(false);
                setLoadedPage(safePageNumber);
                if (pendingFocusRef.current) {
                  const region = pendingFocusRef.current;
                  pendingFocusRef.current = null;
                  window.requestAnimationFrame(() =>
                    scrollToRegion(region, false, dimensions)
                  );
                }
              }}
              onError={() => setImageError(true)}
            />
            {loadedPage === safePageNumber && (
              <svg
                viewBox={`0 0 ${natural.width} ${natural.height}`}
                aria-label={`Evidence annotations for page ${safePageNumber}`}
              >
                {pageRegions.map((region, index) => {
                  const box = boxOf(region, natural.width, natural.height);
                  if (!box || box.width <= 0 || box.height <= 0) return null;
                  const active =
                    sameFinding(selectedRegion, region);
                  return (
                    <g
                      key={`${region?.id || index}-${active ? pulseKey : "idle"}`}
                      role="button"
                      tabIndex="0"
                      className={`forge-region-group forge-region-${severityClass(region)}`}
                      onClick={() => focusFinding(region)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          focusFinding(region);
                        }
                      }}
                    >
                      <title>
                        {region.title}. Evidence strength: {region.severity || "not recorded"}
                      </title>
                      <rect
                        x={box.x}
                        y={box.y}
                        width={box.width}
                        height={box.height}
                        className={active ? "forge-region-active" : "forge-region"}
                      />
                      {active &&
                        relatedBoxesOf(region, natural.width, natural.height).map((extra, extraIndex) => (
                          <rect
                            key={`pair-${extraIndex}`}
                            x={extra.x}
                            y={extra.y}
                            width={extra.width}
                            height={extra.height}
                            className="forge-region-active"
                          />
                        ))}
                      <text x={box.x + 5} y={box.y + 16}>
                        {region.number || index + 1}
                      </text>
                    </g>
                  );
                })}
              </svg>
            )}
            {loadedPage === safePageNumber &&
              activeBox &&
              tooltipStyle &&
              pageOf(selectedRegion) === safePageNumber && (
              <button
                type="button"
                className="forge-region-tooltip"
                style={tooltipStyle}
                onClick={() => onSelectRegion?.(selectedRegion)}
              >
                <strong>{selectedRegion.title}</strong>
                <span>
                  Evidence strength: {selectedRegion.severity || "Not recorded"}
                </span>
                <p>{selectedRegion.explanation}</p>
              </button>
              )}
          </div>
        )}
      </div>
    </div>
  );
});

export default InvestigationCanvas;
