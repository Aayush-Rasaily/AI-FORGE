import { motion } from "framer-motion";
import {
  Database,
  MapPin,
  Clock,
  Camera,
  Wrench,
  Image,
  Hash,
  Eye,
  FileSearch,
  AlertTriangle,
} from "lucide-react";

import RiskGauge from "./RiskGauge";

const MODULE_ICONS = {
  gps: MapPin,
  timezone: Clock,
  camera_fingerprint: Camera,
  editing_software: Wrench,
  thumbnail: Image,
  hash: Hash,
  hidden: Eye,
  content: FileSearch,
};

const TYPE_STYLES = {
  fake_metadata: "border-red-500/30 bg-red-500/10 text-red-300",
  edited_metadata: "border-orange-500/30 bg-orange-500/10 text-orange-300",
  removed_metadata: "border-yellow-500/30 bg-yellow-500/10 text-yellow-300",
};

const TYPE_LABELS = {
  fake_metadata: "Fake Metadata",
  edited_metadata: "Edited Metadata",
  removed_metadata: "Removed Metadata",
};

function ModuleCard({ name, result, delay = 0 }) {
  const Icon = MODULE_ICONS[name] || Database;
  const score = Math.round(Number(result?.score || 0) * 100);
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="rounded-lg border border-[#1F2937] bg-[#0B1120] p-3"
    >
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 text-amber-400" />
        <span className="text-xs font-medium capitalize text-slate-400">
          {name.replace(/_/g, " ")}
        </span>
        <span className={`ml-auto font-mono text-sm ${score >= 50 ? "text-red-400" : "text-emerald-400"}`}>
          {score}%
        </span>
      </div>
      {result?.verdict && (
        <p className="mt-2 text-[11px] leading-relaxed text-slate-500 line-clamp-2">
          {result.verdict}
        </p>
      )}
    </motion.div>
  );
}

function MetadataForensicsPanel({ metadataForensics = {} }) {
  if (!metadataForensics || Object.keys(metadataForensics).length === 0) return null;

  const report = metadataForensics.forensic_report || {};
  const modules = metadataForensics.modules || {};
  const issues = metadataForensics.issues || report.top_issues || [];
  const classified = metadataForensics.classified || report.classified_issues || {};
  const riskPct = Math.round(
    Number(metadataForensics.metadata_risk_pct ?? (metadataForensics.metadata_risk_score || 0) * 100)
  );

  const moduleEntries = Object.entries(modules).filter(([k]) => k !== "exif");

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="overflow-hidden rounded-2xl border border-amber-500/20 bg-gradient-to-br from-amber-500/5 via-[#111827] to-orange-500/5"
    >
      <div className="border-b border-amber-500/10 px-6 py-4">
        <div className="flex items-center gap-2">
          <Database className="h-5 w-5 text-amber-400" />
          <h4 className="text-lg font-semibold text-white">Metadata Forensics</h4>
        </div>
        <p className="mt-1 text-xs text-slate-500">
          EXIF · GPS · Timezone · Camera Fingerprint · Thumbnail · Hash · Hidden Metadata
        </p>
      </div>

      <div className="grid gap-6 p-6 lg:grid-cols-2">
        <div className="flex flex-col items-center justify-center rounded-xl border border-amber-500/10 bg-[#0B1120]/60 p-6">
          <RiskGauge score={riskPct} size={180} label="Metadata Risk" />
          <div className="mt-4 text-center">
            <p className="text-xs uppercase tracking-widest text-amber-400">Verdict</p>
            <p className="mt-1 text-lg font-bold text-white">{report.verdict || "ANALYZED"}</p>
            <p className="mt-2 text-sm text-slate-400">{report.summary}</p>
          </div>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-2">
            {["fake_metadata", "edited_metadata", "removed_metadata"].map((type) => (
              <div
                key={type}
                className={`rounded-lg border px-3 py-2 text-center ${TYPE_STYLES[type]}`}
              >
                <p className="text-lg font-bold">{(classified[type] || []).length}</p>
                <p className="text-[10px] uppercase">{TYPE_LABELS[type]}</p>
              </div>
            ))}
          </div>

          {report.exif_summary && (
            <div className="rounded-lg border border-[#1F2937] bg-[#0B1120] p-4 text-xs text-slate-400">
              <p><span className="text-slate-500">Camera:</span> {report.exif_summary.camera || "—"}</p>
              <p className="mt-1"><span className="text-slate-500">Software:</span> {report.exif_summary.software || "—"}</p>
              <p className="mt-1"><span className="text-slate-500">Captured:</span> {report.exif_summary.datetime_original || "—"}</p>
              {report.exif_summary.gps?.latitude != null && (
                <p className="mt-1">
                  <span className="text-slate-500">GPS:</span>{" "}
                  {report.exif_summary.gps.latitude}, {report.exif_summary.gps.longitude}
                </p>
              )}
            </div>
          )}

          {report.recommendation && (
            <p className="text-sm leading-relaxed text-slate-300">{report.recommendation}</p>
          )}
        </div>
      </div>

      {moduleEntries.length > 0 && (
        <div className="border-t border-amber-500/10 px-6 py-5">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
            Analysis Modules
          </p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {moduleEntries.map(([name, result], i) => (
              <ModuleCard key={name} name={name} result={result} delay={i * 0.05} />
            ))}
          </div>
        </div>
      )}

      {issues.length > 0 && (
        <div className="border-t border-amber-500/10 px-6 py-5">
          <div className="mb-3 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-400" />
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Forensic Findings ({issues.length})
            </p>
          </div>
          <div className="max-h-64 space-y-2 overflow-y-auto">
            {issues.slice(0, 12).map((issue, idx) => (
              <div
                key={idx}
                className={`rounded-lg border px-4 py-3 ${TYPE_STYLES[issue.type] || TYPE_STYLES.edited_metadata}`}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[10px] font-bold uppercase">
                    {TYPE_LABELS[issue.type] || issue.type}
                  </span>
                  <span className="text-[10px] opacity-70">{issue.severity}</span>
                  <span className="ml-auto font-mono text-[10px]">
                    {Math.round((issue.score || 0) * 100)}%
                  </span>
                </div>
                <p className="mt-1 text-xs leading-relaxed opacity-90">{issue.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}

export default MetadataForensicsPanel;
