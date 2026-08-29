import { AlertTriangle, Check, CircleX, Loader2 } from "lucide-react";

const STAGES = [
  { id: "intake", label: "Evidence intake", modules: ["upload", "received"] },
  { id: "validation", label: "File validation", modules: ["validate", "prepare_image", "preprocessing"] },
  { id: "ocr", label: "OCR analysis", modules: ["ocr"] },
  { id: "image", label: "Image forensics", modules: ["deep_scan", "forensics", "ela", "noise", "copy_move"] },
  { id: "tampering", label: "Tampering analysis", modules: ["tampering", "document"] },
  { id: "signature", label: "Signature analysis", modules: ["signature"] },
  { id: "deepfake", label: "Deepfake analysis", modules: ["deepfake", "video"] },
  { id: "localization", label: "Localization", modules: ["localization"] },
  { id: "explainable", label: "Explainable analysis", modules: ["explainable", "narrative"] },
  { id: "jury", label: "AI Jury", modules: ["jury", "fusion"] },
  { id: "assessment", label: "Final assessment", modules: ["completion", "pipeline", "dashboard"] },
];

function stageStatus(stage, events, isLast) {
  const names = events.map((event) => String(event?.module || "").toLowerCase());
  const failed = stage.modules.some((module) =>
    events.some(
      (event) =>
        String(event?.module || "").toLowerCase().includes(module) &&
        event?.status === "failed"
    )
  );
  const warning = stage.modules.some((module) =>
    events.some(
      (event) =>
        String(event?.module || "").toLowerCase().includes(module) &&
        event?.status === "warning"
    )
  );
  const completed = stage.modules.some((module) =>
    events.some(
      (event) =>
        String(event?.module || "").toLowerCase().includes(module) &&
        event?.status === "completed"
    )
  );
  const running = stage.modules.some((module) =>
    names.some((name) => name.includes(module))
  );
  if (failed) return "failed";
  if (warning) return "warning";
  if (completed || (isLast && events.some((event) => event?.status === "completed" && String(event?.module || "").includes("pipeline")))) {
    return "completed";
  }
  if (running) return "running";
  return "pending";
}

function statusLabel(status) {
  return status[0].toUpperCase() + status.slice(1);
}

export function AnalysisLoader({
  active = true,
  fileCount = 1,
  progressEvents = [],
}) {
  if (!active) return null;
  const hasProgress = progressEvents.length > 0;

  return (
    <div className="forge-analysis-state" role="status">
      <div>
        <p className="forge-label">Analyzing evidence</p>
        <strong>Preparing forensic examination</strong>
        <p>
          {fileCount} file{fileCount === 1 ? "" : "s"} under examination.
          {hasProgress
            ? " Stages update as the examination reports progress."
            : " Progress detail is not available for this run."}
        </p>
      </div>
      {hasProgress ? (
        <ol>
          {STAGES.map((stage, index) => {
            const status = stageStatus(stage, progressEvents, index === STAGES.length - 1);
            return (
              <li key={stage.id} className={`forge-analysis-step forge-analysis-step-${status}`}>
                {status === "completed" ? (
                  <Check className="h-3.5 w-3.5" />
                ) : status === "running" ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : status === "warning" ? (
                  <AlertTriangle className="h-3.5 w-3.5" />
                ) : status === "failed" ? (
                  <CircleX className="h-3.5 w-3.5" />
                ) : (
                  <span className="forge-analysis-dot" />
                )}
                <span>{stage.label}</span>
                <small>{statusLabel(status)}</small>
              </li>
            );
          })}
        </ol>
      ) : (
        <div className="forge-analysis-simple">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Examination in progress</span>
        </div>
      )}
    </div>
  );
}

export default AnalysisLoader;
