import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Shield,
  Link2,
  FileCheck,
  Clock,
  User,
  Hash,
  CheckCircle,
  XCircle,
  Lock,
} from "lucide-react";
import {
  getChainOfCustody,
  verifyChainOfCustody,
  getEvidenceHashes,
  getSealedReports,
} from "../../services/api";

function HashBlock({ label, value }) {
  if (!value) return null;
  return (
    <div className="rounded-lg border border-[#1F2937] bg-[#0B1120]/80 p-3">
      <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
        <Hash className="h-3 w-3" />
        {label}
      </div>
      <p className="mt-1 break-all font-mono text-[10px] text-cyan-400">{value}</p>
    </div>
  );
}

function ChainOfCustodyPanel({ evidenceId }) {
  const [custody, setCustody] = useState(null);
  const [hashes, setHashes] = useState(null);
  const [verification, setVerification] = useState(null);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!evidenceId) return;

    async function load() {
      setLoading(true);
      setError("");
      try {
        const [custodyRes, hashRes, verifyRes, reportsRes] = await Promise.allSettled([
          getChainOfCustody(evidenceId),
          getEvidenceHashes(evidenceId),
          verifyChainOfCustody(evidenceId),
          getSealedReports(evidenceId),
        ]);

        if (custodyRes.status === "fulfilled") setCustody(custodyRes.value);
        if (hashRes.status === "fulfilled") setHashes(hashRes.value);
        if (verifyRes.status === "fulfilled") setVerification(verifyRes.value);
        if (reportsRes.status === "fulfilled") setReports(reportsRes.value?.snapshots || []);
      } catch (err) {
        setError(err.message || "Failed to load custody record");
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [evidenceId]);

  if (!evidenceId) {
    return (
      <div className="rounded-2xl border border-[#1F2937] bg-[#111827]/60 p-6 text-center">
        <Shield className="mx-auto h-8 w-8 text-slate-600" />
        <p className="mt-3 text-sm text-slate-500">Select evidence to view chain of custody</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-6 text-center">
        <p className="text-sm text-slate-400">Loading forensic integrity record…</p>
      </div>
    );
  }

  const chain = custody?.chain || [];
  const evidence = custody?.evidence;
  const integrity = verification?.integrity || {};
  const sha256Match = verification?.sha256_match ?? integrity.sha256_match;
  const sha512Match = verification?.sha512_match ?? integrity.sha512_match;
  const evidenceUntouched = verification?.evidence_untouched ?? integrity.evidence_untouched;
  const isValid = verification?.valid;
  const showInvalid = verification && isValid === false && (verification.events > 0 || sha256Match === false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      {/* Integrity Status */}
      <div className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-5 backdrop-blur-xl">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-cyan-400" />
            <h3 className="text-sm font-semibold text-white">Forensic Integrity</h3>
          </div>
          {verification && (
            <span
              className={`flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${
                showInvalid
                  ? "bg-red-500/10 text-red-400"
                  : "bg-emerald-500/10 text-emerald-400"
              }`}
            >
              {showInvalid ? (
                <XCircle className="h-3 w-3" />
              ) : (
                <CheckCircle className="h-3 w-3" />
              )}
              {showInvalid ? "Chain Invalid" : "Integrity Verified"}
            </span>
          )}
        </div>

        {verification && !showInvalid && (
          <div className="mt-3 space-y-1 text-xs text-emerald-400">
            {sha256Match !== false && (
              <p className="flex items-center gap-1.5">
                <CheckCircle className="h-3 w-3" /> SHA256 Match
              </p>
            )}
            {sha512Match !== false && (
              <p className="flex items-center gap-1.5">
                <CheckCircle className="h-3 w-3" /> SHA512 Match
              </p>
            )}
            {evidenceUntouched !== false && (
              <p className="flex items-center gap-1.5">
                <CheckCircle className="h-3 w-3" /> Evidence Untouched
              </p>
            )}
          </div>
        )}

        {error && <p className="mt-2 text-xs text-red-400">{error}</p>}

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <HashBlock label="SHA-256" value={hashes?.sha256 || evidence?.sha256} />
          <HashBlock label="SHA-512" value={hashes?.sha512 || evidence?.sha512} />
        </div>

        {evidence?.intake_timestamp && (
          <div className="mt-3 flex items-center gap-2 text-xs text-slate-500">
            <Clock className="h-3 w-3" />
            Intake: {new Date(evidence.intake_timestamp).toLocaleString()}
            {evidence.intake_user_name && (
              <>
                <User className="ml-2 h-3 w-3" />
                {evidence.intake_user_name}
              </>
            )}
          </div>
        )}
      </div>

      {/* Chain of Custody Timeline */}
      <div className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-5 backdrop-blur-xl">
        <div className="mb-4 flex items-center gap-2">
          <Link2 className="h-4 w-4 text-blue-400" />
          <h3 className="text-sm font-semibold text-white">Chain of Custody</h3>
          <span className="text-xs text-slate-500">({chain.length} events)</span>
        </div>

        {chain.length === 0 ? (
          <p className="text-xs text-slate-500">No custody events recorded yet.</p>
        ) : (
          <div className="relative space-y-0">
            <div className="absolute left-[11px] top-2 bottom-2 w-px bg-gradient-to-b from-blue-500/50 to-transparent" />
            {chain.map((event, i) => (
              <div key={event.id} className="relative flex gap-3 pb-4 last:pb-0">
                <div className="relative z-10 mt-1 h-6 w-6 shrink-0 rounded-full border border-blue-500/40 bg-blue-500/10" />
                <div className="min-w-0 flex-1 rounded-lg border border-[#1F2937] bg-[#0B1120]/60 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-semibold text-blue-400">
                      {event.event_type}
                    </span>
                    <span className="text-[10px] text-slate-600">
                      {event.event_timestamp
                        ? new Date(event.event_timestamp).toLocaleString()
                        : ""}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-slate-300">{event.action_description}</p>
                  <div className="mt-1 flex items-center gap-2 text-[10px] text-slate-500">
                    <User className="h-3 w-3" />
                    {event.actor_name || event.actor_id}
                  </div>
                  {event.event_hash && (
                    <p className="mt-1 truncate font-mono text-[9px] text-slate-600">
                      hash: {event.event_hash}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Immutable Reports */}
      {reports.length > 0 && (
        <div className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-5 backdrop-blur-xl">
          <div className="mb-3 flex items-center gap-2">
            <Lock className="h-4 w-4 text-amber-400" />
            <h3 className="text-sm font-semibold text-white">Immutable Reports</h3>
          </div>
          {reports.map((r) => (
            <div
              key={r.snapshot_id}
              className="mb-2 rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 last:mb-0"
            >
              <div className="flex items-center gap-2">
                <FileCheck className="h-3.5 w-3.5 text-amber-400" />
                <span className="text-xs font-medium text-white">{r.snapshot_id}</span>
              </div>
              <p className="mt-1 font-mono text-[10px] text-slate-500">
                SHA-256: {r.content_sha256?.slice(0, 32)}…
              </p>
              <p className="text-[10px] text-slate-500">
                Sealed {r.sealed_at ? new Date(r.sealed_at).toLocaleString() : ""} by{" "}
                {r.sealed_by_name || "System"}
              </p>
            </div>
          ))}
        </div>
      )}
    </motion.div>
  );
}

export default ChainOfCustodyPanel;
