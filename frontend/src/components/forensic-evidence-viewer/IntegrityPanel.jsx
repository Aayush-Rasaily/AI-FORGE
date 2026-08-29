import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Shield, ShieldAlert, CheckCircle2, Clock, Download, FileJson, AlertTriangle } from "lucide-react";
import { useBackend } from "../../context/BackendConnectivity";

function IntegrityPanel({ evidenceId }) {
  const { online } = useBackend();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!evidenceId) return;
    let isMounted = true;
    const fetchIntegrity = async () => {
      try {
        const res = await fetch(`/api/forensics/evidence/${evidenceId}/custody/verify`);
        if (!res.ok) throw new Error("Failed to verify integrity");
        const json = await res.json();
        if (isMounted) {
          setData(json);
          setLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message);
          setLoading(false);
        }
      }
    };
    fetchIntegrity();
    return () => { isMounted = false; };
  }, [evidenceId]);

  if (!evidenceId) return null;

  const isIntact = data?.status === "intact";
  const statusColor = isIntact ? "text-emerald-400" : "text-red-400";
  const StatusIcon = isIntact ? CheckCircle2 : ShieldAlert;

  return (
    <div className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-5">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className={`h-5 w-5 ${isIntact ? "text-emerald-400" : "text-slate-400"}`} />
          <h3 className="text-sm font-semibold text-white">Chain of Custody & Integrity</h3>
        </div>
        <button
          onClick={() => window.open(`/api/forensics/evidence/${evidenceId}/audit/export`, "_blank")}
          className="flex items-center gap-1.5 rounded-lg border border-[#1F2937] bg-[#0B1120] px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:bg-slate-800"
        >
          <Download className="h-3.5 w-3.5" />
          Export Audit Log
        </button>
      </div>

      {loading ? (
        <div className="animate-pulse space-y-3">
          <div className="h-4 w-3/4 rounded bg-[#1F2937]"></div>
          <div className="h-4 w-1/2 rounded bg-[#1F2937]"></div>
        </div>
      ) : error ? (
        <div className="flex items-center gap-2 text-sm text-red-400">
          <AlertTriangle className="h-4 w-4" />
          <p>Failed to verify integrity: {error}</p>
        </div>
      ) : (
        <div className="space-y-4">
          <div className={`rounded-xl border ${isIntact ? "border-emerald-500/30 bg-emerald-500/5" : "border-red-500/30 bg-red-500/5"} p-4`}>
            <div className="flex items-start gap-3">
              <StatusIcon className={`mt-0.5 h-5 w-5 ${statusColor}`} />
              <div>
                <h4 className={`text-sm font-medium ${statusColor}`}>
                  {isIntact ? "Integrity Verified" : "Evidence Integrity Compromised"}
                </h4>
                <p className="mt-1 text-xs text-slate-400">
                  {isIntact 
                    ? "The evidence remains unchanged since submission. Cryptographic hashes match the original intake records."
                    : "The evidence appears to have been modified after it was originally uploaded. The current file hash does not match the intake hash."}
                </p>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-[#1F2937] bg-[#0B1120]/50 p-3">
            <h5 className="mb-2 text-xs font-medium text-slate-500 uppercase tracking-wider">Cryptographic Identity</h5>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              <div>
                <p className="text-[10px] text-slate-500">Original Intake Hash (SHA-256)</p>
                <p className="font-mono text-xs text-slate-300 truncate" title={data?.original_hashes?.sha256}>
                  {data?.original_hashes?.sha256 || "—"}
                </p>
              </div>
              <div>
                <p className="text-[10px] text-slate-500">Current Computed Hash</p>
                <p className="font-mono text-xs text-slate-300 truncate" title={data?.current_hashes?.sha256}>
                  {data?.current_hashes?.sha256 || "—"}
                </p>
              </div>
            </div>
          </div>

          {data?.chain && data.chain.length > 0 && (
            <div className="mt-4">
              <h5 className="mb-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Custody Timeline</h5>
              <div className="space-y-3">
                {data.chain.slice(0, 5).map((log, idx) => (
                  <div key={idx} className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-[#1F2937]">
                        <Clock className="h-3 w-3 text-slate-400" />
                      </div>
                      {idx !== Math.min(data.chain.length, 5) - 1 && (
                        <div className="my-1 h-full w-px bg-[#1F2937]"></div>
                      )}
                    </div>
                    <div className="pb-3">
                      <p className="text-xs font-medium text-slate-200">{log.action}</p>
                      <div className="mt-0.5 flex items-center gap-2 text-[10px] text-slate-500">
                        <span>{new Date(log.timestamp).toLocaleString()}</span>
                        <span>&middot;</span>
                        <span>{log.user_name || "System"}</span>
                      </div>
                    </div>
                  </div>
                ))}
                {data.chain.length > 5 && (
                  <p className="text-xs text-slate-500 ml-9">...and {data.chain.length - 5} more events. Export audit log for full history.</p>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default IntegrityPanel;
