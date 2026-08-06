import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Link } from "react-router-dom";
import {
  FolderSearch, Plus, Users, MessageSquare, CheckSquare,
  ChevronRight, Clock, AlertCircle, Loader2,
} from "lucide-react";

import AppLayout from "../components/layout/AppLayout";
import GlassCard from "../components/ui/GlassCard";
import StatusBadge from "../components/ui/StatusBadge";
import { SkeletonTable } from "../components/ui/SkeletonLoader";
import { listCases, getCaseDetail, createCase, postCaseComment } from "../services/api";

function Cases() {
  const [cases, setCases] = useState([]);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [comment, setComment] = useState("");

  useEffect(() => {
    listCases()
      .then((res) => setCases(res.cases || []))
      .catch(() => setCases([]))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selected) { setDetail(null); return; }
    setDetailLoading(true);
    getCaseDetail(selected)
      .then((res) => setDetail(res.case))
      .catch(() => setDetail(null))
      .finally(() => setDetailLoading(false));
  }, [selected]);

  const handleCreate = async () => {
    if (!newTitle.trim()) return;
    const res = await createCase(newTitle.trim());
    setCases((prev) => [res.case, ...prev]);
    setSelected(res.case.id);
    setNewTitle("");
    setShowCreate(false);
  };

  const handleComment = async () => {
    if (!comment.trim() || !selected) return;
    const res = await postCaseComment(selected, comment.trim());
    setDetail((d) => ({ ...d, comments: [res.comment, ...(d?.comments || [])] }));
    setComment("");
  };

  return (
    <AppLayout title="Case Management" subtitle="Investigations, assignments & evidence folders">
      <div className="flex flex-col gap-6 xl:flex-row">
        {/* Case list */}
        <div className="w-full shrink-0 xl:w-80">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-bold text-white">Cases</h2>
            <button
              type="button"
              onClick={() => setShowCreate(true)}
              className="flex items-center gap-1.5 rounded-lg bg-cyan-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-cyan-500"
            >
              <Plus className="h-3.5 w-3.5" /> New
            </button>
          </div>

          <AnimatePresence>
            {showCreate && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="mb-4 overflow-hidden"
              >
                <GlassCard className="p-4 space-y-3">
                  <input
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                    placeholder="Case title…"
                    className="w-full rounded-lg border border-[#1F2937] bg-[#0B1120] px-3 py-2 text-sm text-white placeholder-slate-600 focus:border-cyan-500/50 focus:outline-none"
                    onKeyDown={(e) => e.key === "Enter" && handleCreate()}
                  />
                  <div className="flex gap-2">
                    <button type="button" onClick={handleCreate} className="flex-1 rounded-lg bg-cyan-600 py-2 text-xs font-medium text-white">Create</button>
                    <button type="button" onClick={() => setShowCreate(false)} className="rounded-lg border border-[#1F2937] px-3 py-2 text-xs text-slate-400">Cancel</button>
                  </div>
                </GlassCard>
              </motion.div>
            )}
          </AnimatePresence>

          {loading ? (
            <SkeletonTable rows={6} />
          ) : cases.length === 0 ? (
            <GlassCard className="p-8 text-center">
              <FolderSearch className="mx-auto h-8 w-8 text-slate-600" />
              <p className="mt-3 text-sm text-slate-500">No cases yet</p>
            </GlassCard>
          ) : (
            <div className="space-y-2">
              {cases.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => setSelected(c.id)}
                  className={`w-full rounded-xl border p-4 text-left transition ${
                    selected === c.id
                      ? "border-cyan-500/50 bg-cyan-500/5"
                      : "border-[#1F2937] bg-[#111827]/80 hover:border-slate-600"
                  }`}
                >
                  <p className="truncate text-sm font-semibold text-white">{c.title}</p>
                  <div className="mt-1 flex items-center gap-2">
                    <StatusBadge status={c.status || "open"} />
                    <span className="text-[10px] text-slate-600">{c.id}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Case detail */}
        <div className="min-w-0 flex-1">
          {!selected ? (
            <GlassCard className="flex h-64 items-center justify-center">
              <p className="text-sm text-slate-500">Select a case to view details</p>
            </GlassCard>
          ) : detailLoading ? (
            <SkeletonTable rows={8} />
          ) : detail ? (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
              <GlassCard className="p-6">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h2 className="text-xl font-bold text-white">{detail.title}</h2>
                    <p className="mt-1 text-sm text-slate-400">{detail.description || "No description"}</p>
                    <p className="mt-2 font-mono text-xs text-slate-600">{detail.id}</p>
                  </div>
                  <StatusBadge status={detail.status} />
                </div>
                <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {[
                    { icon: FolderSearch, label: "Evidence", value: detail.evidence_count || 0 },
                    { icon: Users, label: "Members", value: detail.members?.length || 0 },
                    { icon: CheckSquare, label: "Tasks", value: detail.assignments?.length || 0 },
                    { icon: MessageSquare, label: "Comments", value: detail.comments?.length || 0 },
                  ].map(({ icon: Icon, label, value }) => (
                    <div key={label} className="rounded-lg border border-[#1F2937] bg-[#0B1120]/60 p-3 text-center">
                      <Icon className="mx-auto h-4 w-4 text-cyan-400" />
                      <p className="mt-1 text-lg font-bold text-white">{value}</p>
                      <p className="text-[10px] text-slate-500">{label}</p>
                    </div>
                  ))}
                </div>
              </GlassCard>

              {/* Assignments */}
              {detail.assignments?.length > 0 && (
                <GlassCard className="p-5">
                  <h3 className="mb-3 text-sm font-semibold text-white">Assignments</h3>
                  {detail.assignments.map((a) => (
                    <div key={a.id} className="mb-2 flex items-center justify-between rounded-lg border border-[#1F2937] p-3 last:mb-0">
                      <div>
                        <p className="text-sm text-white">{a.title}</p>
                        <p className="text-xs text-slate-500">{a.assignee_name || a.assignee_id}</p>
                      </div>
                      <StatusBadge status={a.status} />
                    </div>
                  ))}
                </GlassCard>
              )}

              {/* Evidence */}
              {detail.evidence?.length > 0 && (
                <GlassCard className="p-5">
                  <h3 className="mb-3 text-sm font-semibold text-white">Evidence</h3>
                  {detail.evidence.map((e) => (
                    <Link
                      key={e.evidence_id}
                      to="/investigation"
                      className="mb-2 flex items-center gap-3 rounded-lg border border-[#1F2937] p-3 transition hover:border-cyan-500/30 last:mb-0"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm text-white">{e.filename}</p>
                        <p className="text-xs text-slate-500">{e.media_type} · {e.evidence_id}</p>
                      </div>
                      <ChevronRight className="h-4 w-4 text-slate-600" />
                    </Link>
                  ))}
                </GlassCard>
              )}

              {/* Comments */}
              <GlassCard className="p-5">
                <h3 className="mb-3 text-sm font-semibold text-white">Comments</h3>
                <div className="mb-3 flex gap-2">
                  <input
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    placeholder="Add a comment…"
                    className="flex-1 rounded-lg border border-[#1F2937] bg-[#0B1120] px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none"
                    onKeyDown={(e) => e.key === "Enter" && handleComment()}
                  />
                  <button type="button" onClick={handleComment} className="rounded-lg bg-cyan-600 px-4 py-2 text-xs font-medium text-white">Post</button>
                </div>
                {detail.comments?.map((c) => (
                  <div key={c.id} className="mb-3 border-b border-[#1F2937] pb-3 last:mb-0 last:border-0">
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                      <span className="font-medium text-slate-300">{c.author_name}</span>
                      <Clock className="h-3 w-3" />
                      {c.created_at ? new Date(c.created_at).toLocaleString() : ""}
                    </div>
                    <p className="mt-1 text-sm text-slate-300">{c.body}</p>
                  </div>
                ))}
              </GlassCard>
            </motion.div>
          ) : (
            <GlassCard className="flex h-32 items-center justify-center">
              <AlertCircle className="mr-2 h-4 w-4 text-red-400" />
              <p className="text-sm text-slate-500">Failed to load case</p>
            </GlassCard>
          )}
        </div>
      </div>
    </AppLayout>
  );
}

export default Cases;
