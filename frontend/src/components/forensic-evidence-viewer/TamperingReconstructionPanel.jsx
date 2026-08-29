import { motion } from "framer-motion";
import { GitBranch, Clock, AlertTriangle, Fingerprint, History, CheckCircle2 } from "lucide-react";

export default function TamperingReconstructionPanel({ reconstruction, originalUrl, overlayUrl }) {
  if (!reconstruction) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <Fingerprint className="h-12 w-12 text-slate-700" />
        <p className="mt-4 text-sm text-slate-500">Reconstruction data is not available for this evidence.</p>
      </div>
    );
  }

  const { fraud_story, human_findings, timeline, suspicious_objects, risk_explanation } = reconstruction;
  const isSuspicious = fraud_story?.includes("likely edited") || fraud_story?.includes("High Risk");

  return (
    <div className="space-y-6">
      {/* Overview and Story */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-6 backdrop-blur-xl"
      >
        <div className="mb-4 flex items-center gap-2 border-b border-[#1F2937] pb-4">
          <Fingerprint className={`h-6 w-6 ${isSuspicious ? 'text-amber-400' : 'text-cyan-400'}`} />
          <h3 className="text-xl font-semibold text-white">Fraud Story</h3>
        </div>
        <p className="text-sm leading-relaxed text-slate-300">
          {fraud_story}
        </p>
      </motion.div>

      {/* Visual Comparison */}
      {(originalUrl || overlayUrl) && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-6 backdrop-blur-xl"
        >
          <div className="mb-4 flex items-center gap-2 border-b border-[#1F2937] pb-4">
            <GitBranch className="h-5 w-5 text-cyan-400" />
            <h3 className="text-lg font-semibold text-white">Visual Evidence Map</h3>
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {originalUrl && (
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Original Document</p>
                <div className="relative aspect-[3/4] w-full overflow-hidden rounded-xl border border-[#1F2937] bg-[#0B1120]">
                  <img src={originalUrl} alt="Original" className="h-full w-full object-contain" />
                </div>
              </div>
            )}
            {overlayUrl && (
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-amber-500/80">Tampered Regions Map</p>
                <div className="relative aspect-[3/4] w-full overflow-hidden rounded-xl border border-amber-500/20 bg-[#0B1120]">
                  <img src={overlayUrl} alt="Map" className="h-full w-full object-contain" />
                </div>
              </div>
            )}
          </div>
        </motion.div>
      )}

      {/* Grid: Details */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        {/* Risk & Inventory */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="space-y-6"
        >
          <div className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-6 backdrop-blur-xl">
            <h4 className="mb-4 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-400">
              <AlertTriangle className={`h-4 w-4 ${isSuspicious ? 'text-amber-400' : 'text-cyan-400'}`} />
              Risk Explanation
            </h4>
            <div className="space-y-2">
              {risk_explanation?.split('\n').map((line, i) => (
                <p key={i} className={`text-sm ${i === 0 ? 'font-medium text-slate-200 mb-3' : 'text-slate-400'}`}>
                  {line}
                </p>
              ))}
            </div>
          </div>

          {suspicious_objects && suspicious_objects.length > 0 && (
            <div className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-6 backdrop-blur-xl">
              <h4 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-400">
                Suspicious Object Inventory
              </h4>
              <ul className="space-y-2">
                {suspicious_objects.map((obj, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm text-slate-300">
                    <div className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                    {obj}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </motion.div>

        {/* Timeline */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-6 backdrop-blur-xl"
        >
          <h4 className="mb-6 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-400">
            <History className="h-4 w-4 text-cyan-400" />
            Evidence Timeline
          </h4>
          <div className="relative border-l border-[#1F2937] pl-4 space-y-6">
            {timeline?.map((step, i) => (
              <div key={i} className="relative">
                <div className={`absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full border-2 border-[#111827] ${
                  step.stage.includes('Creation') || step.stage.includes('Analysis') || step.stage.includes('Upload') 
                  ? 'bg-cyan-500' : 'bg-amber-500'
                }`} />
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">{step.stage}</p>
                <p className="text-sm text-slate-300">{step.description}</p>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
      
      {/* Human Findings List */}
      {human_findings && human_findings.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-6 backdrop-blur-xl"
        >
          <h4 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-400">
            Forensic Findings
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {human_findings.map((f, i) => (
              <div key={i} className="flex items-start gap-3 rounded-xl border border-[#1F2937] bg-[#0B1120]/40 p-4">
                {isSuspicious ? (
                  <AlertTriangle className="h-5 w-5 shrink-0 text-amber-500" />
                ) : (
                  <CheckCircle2 className="h-5 w-5 shrink-0 text-cyan-500" />
                )}
                <p className="text-sm text-slate-300">{f}</p>
              </div>
            ))}
          </div>
        </motion.div>
      )}

    </div>
  );
}
