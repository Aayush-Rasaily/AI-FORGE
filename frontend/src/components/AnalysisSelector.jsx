/**
 * AnalysisSelector.jsx — Forge Investigation Type Selector
 *
 * Compact horizontal tab strip replacing the 8-card grid.
 *
 * Labels use investigator-facing language only.
 * No technical algorithm descriptions in the primary UI.
 * Tabs that are internal analysis capabilities (jury, heatmap, dashboard)
 * are kept available but positioned after the primary investigation modes.
 */

import {
  Microscope,
  Image,
  FileText,
  PenTool,
  Video,
  ScanFace,
  Scale,
  Layers,
  LayoutDashboard,
} from "lucide-react";

const PRIMARY_TABS = [
  { id: "investigate", label: "Comprehensive",  Icon: Microscope },
  { id: "image",       label: "Image",           Icon: Image     },
  { id: "document",    label: "Document",         Icon: FileText  },
  { id: "signature",   label: "Signature",        Icon: PenTool   },
  { id: "video",       label: "Video",            Icon: Video     },
  { id: "deepfake",    label: "Deepfake",         Icon: ScanFace  },
];

const SECONDARY_TABS = [
  { id: "jury",      label: "Jury",      Icon: Scale          },
  { id: "heatmap",   label: "Heatmap",   Icon: Layers         },
  { id: "dashboard", label: "Dashboard", Icon: LayoutDashboard},
];

function AnalysisSelector({ analysisType, setAnalysisType }) {
  const allTabs = [...PRIMARY_TABS, ...SECONDARY_TABS];

  return (
    <div className="forge-panel">
      {/* Tab strip */}
      <div className="forge-tabs" role="tablist" aria-label="Investigation type">
        {PRIMARY_TABS.map(({ id, label, Icon }) => (
          <button
            key={id}
            type="button"
            role="tab"
            id={`analysis-tab-${id}`}
            aria-selected={analysisType === id}
            onClick={() => setAnalysisType(id)}
            className={`forge-tab ${analysisType === id ? "forge-tab-active" : ""}`}
          >
            <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            {label}
          </button>
        ))}

        {/* Separator before secondary tabs */}
        <div
          className="mx-1 my-2 w-px self-stretch"
          style={{ background: "var(--forge-border)" }}
          aria-hidden="true"
        />

        {SECONDARY_TABS.map(({ id, label, Icon }) => (
          <button
            key={id}
            type="button"
            role="tab"
            id={`analysis-tab-${id}`}
            aria-selected={analysisType === id}
            onClick={() => setAnalysisType(id)}
            className={`forge-tab ${analysisType === id ? "forge-tab-active" : ""}`}
            title={`${label} — internal analysis tool`}
          >
            <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}

export default AnalysisSelector;