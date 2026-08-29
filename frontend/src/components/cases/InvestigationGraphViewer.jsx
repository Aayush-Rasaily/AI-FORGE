import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  GitBranch,
  Loader2,
  RefreshCw,
  FolderSearch,
  AlertTriangle,
} from "lucide-react";
import { getCaseGraph, rebuildCaseGraph } from "../../services/api";

const TYPE_COLORS = {
  case: "#38bdf8",
  evidence: "#22d3ee",
  entity: "#a78bfa",
  archive: "#f59e0b",
  hash: "#64748b",
  email: "#fbbf24",
  phone: "#34d399",
  amount: "#f87171",
  date: "#60a5fa",
  account: "#c084fc",
};

function layoutNodes(nodes, width, height) {
  const positions = {};
  const caseNodes = nodes.filter((n) => n.type === "case");
  const evidenceNodes = nodes.filter((n) => n.type === "evidence");
  const otherNodes = nodes.filter((n) => !["case", "evidence"].includes(n.type));

  const cx = width / 2;
  caseNodes.forEach((n, i) => {
    positions[n.id] = { x: cx, y: 48 + i * 20 };
  });

  const rowY = height * 0.42;
  const gap = width / Math.max(evidenceNodes.length + 1, 2);
  evidenceNodes.forEach((n, i) => {
    positions[n.id] = { x: gap * (i + 1), y: rowY };
  });

  const bottomY = height * 0.78;
  const ogap = width / Math.max(otherNodes.length + 1, 2);
  otherNodes.forEach((n, i) => {
    positions[n.id] = { x: ogap * (i + 1), y: bottomY };
  });

  nodes.forEach((n) => {
    if (!positions[n.id]) {
      positions[n.id] = { x: cx, y: height / 2 };
    }
  });

  return positions;
}

function InvestigationGraphViewer({ caseId, onSelectEvidence, focusEvidenceId }) {
  const [graph, setGraph] = useState(null);
  const [loading, setLoading] = useState(true);
  const [rebuilding, setRebuilding] = useState(false);
  const [error, setError] = useState("");
  const [selectedNode, setSelectedNode] = useState(null);

  const load = useCallback(async () => {
    if (!caseId) return;
    setLoading(true);
    setError("");
    try {
      const res = await getCaseGraph(caseId, focusEvidenceId);
      setGraph(res.graph || res);
    } catch (err) {
      setError(err.message || "Failed to load investigation graph");
      setGraph(null);
    } finally {
      setLoading(false);
    }
  }, [caseId, focusEvidenceId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleRebuild = async () => {
    setRebuilding(true);
    try {
      const res = await rebuildCaseGraph(caseId);
      setGraph(res.graph || res);
    } catch (err) {
      setError(err.message || "Rebuild failed");
    } finally {
      setRebuilding(false);
    }
  };

  const nodes = graph?.nodes || [];
  const edges = graph?.edges || [];
  const findings = graph?.findings || [];
  const chains = graph?.chains || [];

  const W = 720;
  const H = 340;
  const positions = useMemo(
    () => layoutNodes(nodes, W, H),
    [nodes]
  );

  const handleNodeClick = (node) => {
    setSelectedNode(node);
    if (node.evidence_id && onSelectEvidence) {
      onSelectEvidence(node.evidence_id);
    }
  };

  if (!caseId) {
    return (
      <div className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-8 text-center text-sm text-slate-500">
        Select a case to view the investigation graph
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-5 backdrop-blur-xl"
    >
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <GitBranch className="h-5 w-5 text-cyan-400" />
            <h3 className="text-lg font-semibold text-white">Investigation Graph</h3>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Evidence relationships · {nodes.length} nodes · {edges.length} edges
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={load}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-lg border border-[#1F2937] px-3 py-1.5 text-xs text-slate-300 hover:border-cyan-500/30"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <button
            type="button"
            onClick={handleRebuild}
            disabled={rebuilding}
            className="rounded-lg bg-cyan-600/20 px-3 py-1.5 text-xs font-medium text-cyan-400 hover:bg-cyan-600/30 disabled:opacity-50"
          >
            {rebuilding ? "Rebuilding…" : "Rebuild Graph"}
          </button>
        </div>
      </div>

      {error && <p className="mb-3 text-xs text-red-400">{error}</p>}

      {loading && !graph ? (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-cyan-400" />
        </div>
      ) : nodes.length === 0 ? (
        <div className="flex h-48 flex-col items-center justify-center text-center">
          <FolderSearch className="h-8 w-8 text-slate-600" />
          <p className="mt-2 text-sm text-slate-500">Link multiple evidence items to build the graph</p>
        </div>
      ) : (
        <>
          <div className="overflow-x-auto rounded-xl border border-[#1F2937] bg-[#0B1120]/60">
            <svg viewBox={`0 0 ${W} ${H}`} className="w-full min-w-[600px]" style={{ height: 280 }}>
              {edges.map((e, i) => {
                const s = positions[e.source];
                const t = positions[e.target];
                if (!s || !t) return null;
                const midX = (s.x + t.x) / 2;
                const midY = (s.y + t.y) / 2;
                return (
                  <g key={`${e.source}-${e.target}-${i}`}>
                    <line
                      x1={s.x}
                      y1={s.y}
                      x2={t.x}
                      y2={t.y}
                      stroke="#334155"
                      strokeWidth={1.5}
                      strokeOpacity={0.8}
                    />
                    <text
                      x={midX}
                      y={midY - 4}
                      textAnchor="middle"
                      fill="#64748b"
                      fontSize={8}
                    >
                      {String(e.relation || "").replace(/_/g, " ")}
                    </text>
                  </g>
                );
              })}
              {nodes.map((n) => {
                const pos = positions[n.id];
                if (!pos) return null;
                const color = TYPE_COLORS[n.entity_type] || TYPE_COLORS[n.type] || "#94a3b8";
                const isEvidence = n.type === "evidence";
                const r = n.type === "case" ? 22 : isEvidence ? 18 : 14;
                const selected = selectedNode?.id === n.id;
                const glyph = isEvidence
                  ? String(n.media_type || "e")[0].toUpperCase()
                  : n.type === "case"
                    ? "C"
                    : n.entity_type === "email" ? "@"
                    : n.entity_type === "phone" ? "📞"
                    : n.entity_type === "amount" ? "$"
                    : n.entity_type === "date" ? "📅"
                    : n.entity_type === "account" ? "💳"
                    : "•";
                return (
                  <g
                    key={n.id}
                    style={{ cursor: isEvidence ? "pointer" : "default" }}
                    onClick={() => handleNodeClick(n)}
                  >
                    <circle
                      cx={pos.x}
                      cy={pos.y}
                      r={r}
                      fill={selected ? `${color}44` : "#111827"}
                      stroke={color}
                      strokeWidth={selected ? 2.5 : 1.5}
                    />
                    <text
                      x={pos.x}
                      y={pos.y + 4}
                      textAnchor="middle"
                      fill={color}
                      fontSize={isEvidence ? 10 : 12}
                      fontWeight="bold"
                    >
                      {glyph}
                    </text>
                    <text
                      x={pos.x}
                      y={pos.y + r + 12}
                      textAnchor="middle"
                      fill="#e2e8f0"
                      fontSize={9}
                    >
                      {(n.label || n.id).slice(0, 18)}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>

          {selectedNode?.evidence_id && (
            <div className="mt-3 flex items-center justify-between rounded-lg border border-cyan-500/20 bg-cyan-500/5 px-3 py-2">
              <span className="text-xs text-slate-300">
                Selected: <strong>{selectedNode.label}</strong> ({selectedNode.media_type})
              </span>
              <Link
                to={`/investigation?case=${caseId}&evidence=${selectedNode.evidence_id}`}
                className="text-xs font-medium text-cyan-400 hover:text-cyan-300"
              >
                Open in workspace →
              </Link>
            </div>
          )}

          {findings.length > 0 && (
            <div className="mt-4">
              <h4 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-400">
                <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
                Correlation Findings
              </h4>
              <div className="space-y-1.5">
                {findings.slice(0, 6).map((f, i) => (
                  <div
                    key={i}
                    className="rounded-lg border border-[#1F2937] bg-[#0B1120]/40 px-3 py-2 text-xs text-slate-400"
                  >
                    <span className="font-medium text-amber-400">{f.type?.replace(/_/g, " ")}</span>
                    {" — "}
                    {f.detail}
                  </div>
                ))}
              </div>
            </div>
          )}

          {chains.length > 0 && (
            <div className="mt-4">
              <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                Evidence Chains
              </h4>
              {chains.slice(0, 4).map((c, i) => (
                <p key={i} className="mb-1 text-xs text-slate-500">
                  {(c.steps || [])
                    .map((s) => (typeof s === "object" ? s.label || s.evidence_id : s))
                    .join(" → ")}
                </p>
              ))}
            </div>
          )}
        </>
      )}
    </motion.div>
  );
}

export default InvestigationGraphViewer;
