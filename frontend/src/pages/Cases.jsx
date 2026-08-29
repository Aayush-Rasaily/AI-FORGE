import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Link } from "react-router-dom";
import {
  FolderSearch, Plus, Users, MessageSquare, CheckSquare,
  ChevronRight, Clock, AlertCircle, History, Shield, ListTodo,
  UserPlus, Gavel,
} from "lucide-react";

import AppLayout from "../components/layout/AppLayout";
import StatusBadge from "../components/ui/StatusBadge";
import InvestigationGraphViewer from "../components/cases/InvestigationGraphViewer";
import { SkeletonTable } from "../components/ui/SkeletonLoader";
import {
  listCases,
  getCaseDetail,
  createCase,
  postCaseComment,
  updateCaseStatus,
  updateCasePriority,
  assignCaseInvestigator,
  createCaseTask,
  updateCaseTaskStatus,
  listInvestigators,
  getCaseMeta,
} from "../services/api";

const TABS = [
  { id: "overview", label: "Overview", icon: FolderSearch },
  { id: "evidence", label: "Evidence", icon: ListTodo },
  { id: "timeline", label: "Timeline", icon: History },
  { id: "tasks", label: "Tasks", icon: CheckSquare },
  { id: "comments", label: "Comments", icon: MessageSquare },
  { id: "audit", label: "Audit", icon: Shield },
];

function Panel({ children, className = "" }) {
  return <div className={`forge-panel ${className}`}>{children}</div>;
}

const PRIORITY_COLORS = {
  low: "text-slate-400",
  normal: "text-cyan-400",
  high: "text-amber-400",
  critical: "text-red-400",
};

function Cases() {
  const [cases, setCases] = useState([]);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newOrganization, setNewOrganization] = useState("");
  const [newDepartment, setNewDepartment] = useState("");
  const [newPriority, setNewPriority] = useState("normal");
  const [comment, setComment] = useState("");
  const [tab, setTab] = useState("overview");
  const [meta, setMeta] = useState({ statuses: [], priorities: [] });
  const [investigators, setInvestigators] = useState([]);
  const [assignId, setAssignId] = useState("");
  const [taskTitle, setTaskTitle] = useState("");
  const [taskAssignee, setTaskAssignee] = useState("");

  useEffect(() => {
    listCases()
      .then((res) => setCases(res.cases || []))
      .catch(() => setCases([]))
      .finally(() => setLoading(false));
    getCaseMeta().then((r) => setMeta(r)).catch(() => {});
    listInvestigators().then((r) => setInvestigators(r.investigators || [])).catch(() => {});
  }, []);

  const reloadDetail = useCallback(() => {
    if (!selected) return;
    setDetailLoading(true);
    getCaseDetail(selected)
      .then((res) => setDetail(res.case))
      .catch(() => setDetail(null))
      .finally(() => setDetailLoading(false));
  }, [selected]);

  useEffect(() => {
    if (!selected) return undefined;
    const timer = window.setTimeout(reloadDetail, 0);
    return () => window.clearTimeout(timer);
  }, [selected, reloadDetail]);

  const handleCreate = async () => {
    if (!newTitle.trim()) return;
    const res = await createCase(newTitle.trim(), newDescription.trim(), { 
      priority: newPriority,
      organization: newOrganization.trim(),
      department: newDepartment.trim()
    });
    setCases((prev) => [res.case, ...prev]);
    setSelected(res.case.id);
    setNewTitle("");
    setNewDescription("");
    setNewOrganization("");
    setNewDepartment("");
    setShowCreate(false);
  };

  const handleExport = () => {
    if (!selected) return;
    window.open(`/api/cases/${selected}/export`, '_blank');
  };

  const handleComment = async () => {
    if (!comment.trim() || !selected) return;
    await postCaseComment(selected, comment.trim());
    setComment("");
    reloadDetail();
  };

  const handleStatus = async (status) => {
    if (!selected) return;
    await updateCaseStatus(selected, status);
    reloadDetail();
    listCases().then((res) => setCases(res.cases || []));
  };

  const handlePriority = async (priority) => {
    if (!selected) return;
    await updateCasePriority(selected, priority);
    reloadDetail();
  };

  const handleAssign = async () => {
    if (!selected || !assignId) return;
    const inv = investigators.find((i) => i.id === assignId);
    await assignCaseInvestigator(selected, assignId, { name: inv?.name, role: "lead" });
    setAssignId("");
    reloadDetail();
  };

  const handleCreateTask = async () => {
    if (!selected || !taskTitle.trim() || !taskAssignee) return;
    const inv = investigators.find((i) => i.id === taskAssignee);
    await createCaseTask(selected, {
      title: taskTitle.trim(),
      assignee_id: taskAssignee,
      assignee_name: inv?.name,
      priority: "normal",
    });
    setTaskTitle("");
    setTaskAssignee("");
    reloadDetail();
  };

  const handleTaskStatus = async (assignmentId, status) => {
    await updateCaseTaskStatus(assignmentId, status);
    reloadDetail();
  };

  return (
    <AppLayout title="Evidence" subtitle="Case records and investigation files">
      <div className="flex flex-col gap-6 xl:flex-row">
        <div className="w-full shrink-0 xl:w-80">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-bold text-white">Cases</h2>
            <button
              type="button"
              onClick={() => setShowCreate(true)}
              className="forge-primary-action"
            >
              <Plus className="h-3.5 w-3.5" /> New Case
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
                <Panel className="space-y-3 p-4">
                  <input
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                    placeholder="Investigation title"
                    className="forge-input"
                    onKeyDown={(e) => e.key === "Enter" && handleCreate()}
                  />
                  <textarea
                    value={newDescription}
                    onChange={(e) => setNewDescription(e.target.value)}
                    placeholder="Case description…"
                    rows={2}
                    className="forge-input"
                  />
                  <div className="grid grid-cols-2 gap-2">
                    <input
                      value={newOrganization}
                      onChange={(e) => setNewOrganization(e.target.value)}
                      placeholder="Organization…"
                      className="forge-input"
                    />
                    <input
                      value={newDepartment}
                      onChange={(e) => setNewDepartment(e.target.value)}
                      placeholder="Department…"
                      className="forge-input"
                    />
                  </div>
                  <select
                    value={newPriority}
                    onChange={(e) => setNewPriority(e.target.value)}
                    className="forge-input"
                  >
                    {(meta.priorities || ["low", "normal", "high", "critical"]).map((p) => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                  <div className="flex gap-2">
                    <button type="button" onClick={handleCreate} className="forge-primary-action flex-1">Create</button>
                    <button type="button" onClick={() => setShowCreate(false)} className="forge-icon-button">Cancel</button>
                  </div>
                </Panel>
              </motion.div>
            )}
          </AnimatePresence>

          {loading ? (
            <SkeletonTable rows={6} />
          ) : cases.length === 0 ? (
            <Panel className="p-8 text-center">
              <FolderSearch className="mx-auto h-8 w-8 text-slate-600" />
              <p className="mt-3 text-sm text-slate-500">No cases yet — create one to begin</p>
            </Panel>
          ) : (
            <div className="space-y-2">
              {cases.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => { setSelected(c.id); setTab("overview"); }}
                  className={`w-full rounded-md border p-4 text-left transition ${
                    selected === c.id
                      ? "border-[color:var(--forge-accent-border)] bg-[color:var(--forge-accent-subtle)]"
                      : "border-[color:var(--forge-border)] bg-[color:var(--forge-surface)] hover:border-[color:var(--forge-border-strong)]"
                  }`}
                >
                  <p className="truncate text-sm font-semibold text-white">{c.title}</p>
                  <div className="mt-1 flex flex-wrap items-center gap-2">
                    <StatusBadge status={c.status || "open"} />
                    <span className={`text-[10px] uppercase ${PRIORITY_COLORS[c.priority] || "text-slate-500"}`}>
                      {c.priority || "normal"}
                    </span>
                    <span className="text-[10px] text-slate-600">{c.evidence_count || 0} files</span>
                  </div>
                  <p className="mt-1 font-mono text-[10px] text-slate-600">{c.id}</p>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="min-w-0 flex-1">
          {!selected ? (
            <Panel className="flex h-64 items-center justify-center">
              <p className="text-sm text-slate-500">Select a case to manage investigation</p>
            </Panel>
          ) : detailLoading && !detail ? (
            <SkeletonTable rows={8} />
          ) : detail ? (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
              <Panel className="p-6">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <h2 className="text-xl font-bold text-white">{detail.title}</h2>
                    <p className="mt-1 text-sm text-slate-400">{detail.description || "No description"}</p>
                    { (detail.organization || detail.department) && (
                      <p className="mt-1 text-xs text-slate-400">
                        {detail.organization} {detail.organization && detail.department ? "·" : ""} {detail.department}
                      </p>
                    )}
                    <p className="mt-2 font-mono text-xs text-slate-600">{detail.id}</p>
                    <p className="mt-1 text-xs text-slate-500">
                      Owner: {detail.owner?.name || detail.lead_investigator_name || "—"}
                      {" · "}
                      Created {detail.created_at ? new Date(detail.created_at).toLocaleDateString() : "—"}
                    </p>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <div className="flex flex-wrap gap-2">
                      <StatusBadge status={detail.status} />
                      <StatusBadge status={detail.priority} label={detail.priority} />
                      {detail.verdict && (
                        <StatusBadge status={detail.verdict} label={`Verdict: ${detail.verdict}`} />
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={handleExport}
                      className="flex items-center gap-1.5 rounded-lg border border-[#1F2937] bg-[#111827] px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-[#1F2937]"
                    >
                      Export Bundle
                    </button>
                  </div>
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  <select
                    value={detail.status}
                    onChange={(e) => handleStatus(e.target.value)}
                    className="rounded-lg border border-[#1F2937] bg-[#0B1120] px-3 py-1.5 text-xs text-white"
                  >
                    {(meta.statuses || ["open", "investigating", "pending", "closed", "court_submitted"]).map((s) => (
                      <option key={s} value={s}>{s.replace(/_/g, " ")}</option>
                    ))}
                  </select>
                  <select
                    value={detail.priority}
                    onChange={(e) => handlePriority(e.target.value)}
                    className="rounded-lg border border-[#1F2937] bg-[#0B1120] px-3 py-1.5 text-xs text-white"
                  >
                    {(meta.priorities || ["low", "normal", "high", "critical"]).map((p) => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                  <div className="flex gap-1">
                    <select
                      value={assignId}
                      onChange={(e) => setAssignId(e.target.value)}
                      className="rounded-lg border border-[#1F2937] bg-[#0B1120] px-2 py-1.5 text-xs text-white"
                    >
                      <option value="">Assign investigator…</option>
                      {investigators.map((i) => (
                        <option key={i.id} value={i.id}>{i.name}</option>
                      ))}
                    </select>
                    <button
                      type="button"
                      onClick={handleAssign}
                      disabled={!assignId}
                      className="flex items-center gap-1 rounded-lg bg-violet-600/20 px-2 py-1.5 text-xs text-violet-300 disabled:opacity-50"
                    >
                      <UserPlus className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>

                <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {[
                    { icon: FolderSearch, label: "Evidence", value: detail.evidence_count || 0 },
                    { icon: Users, label: "Investigators", value: (detail.members?.length || 0) + 1 },
                    { icon: CheckSquare, label: "Tasks", value: detail.assignments?.length || 0 },
                    { icon: Gavel, label: "Verdict", value: detail.verdict || "—" },
                  ].map(({ icon: Icon, label, value }) => (
                    <div key={label} className="rounded-lg border border-[#1F2937] bg-[#0B1120]/60 p-3 text-center">
                      <Icon className="mx-auto h-4 w-4 text-cyan-400" />
                      <p className="mt-1 text-lg font-bold text-white">{value}</p>
                      <p className="text-[10px] text-slate-500">{label}</p>
                    </div>
                  ))}
                </div>
              </Panel>

              <div className="flex flex-wrap gap-1 border-b border-[#1F2937] pb-1">
                {TABS.map(({ id, label, icon: Icon }) => (
                  <button
                    key={id}
                    type="button"
                    onClick={() => setTab(id)}
                    className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                      tab === id
                        ? "bg-cyan-500/10 text-cyan-400"
                        : "text-slate-500 hover:text-slate-300"
                    }`}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {label}
                  </button>
                ))}
              </div>

              {tab === "overview" && (
                <InvestigationGraphViewer caseId={selected} />
              )}

              {tab === "evidence" && (
                <Panel className="p-5">
                  <div className="mb-3 flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-white">Evidence List</h3>
                    <Link
                      to={`/investigation?case=${selected}`}
                      className="text-xs text-cyan-400 hover:text-cyan-300"
                    >
                      Upload evidence →
                    </Link>
                  </div>
                  {detail.evidence?.length === 0 ? (
                    <p className="text-sm text-slate-500">No evidence linked yet</p>
                  ) : (
                    detail.evidence.map((e) => (
                      <Link
                        key={e.evidence_id}
                        to={`/investigation?case=${selected}&evidence=${e.evidence_id}`}
                        className="mb-2 flex items-center gap-3 rounded-lg border border-[#1F2937] p-3 transition hover:border-cyan-500/30 last:mb-0"
                      >
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm text-white">{e.filename}</p>
                          <p className="text-xs text-slate-500">
                            {e.media_type} · {e.evidence_id}
                            {e.risk_score != null && ` · Risk ${e.risk_score}`}
                          </p>
                        </div>
                        {e.verdict && <StatusBadge status={e.verdict} />}
                        <ChevronRight className="h-4 w-4 text-slate-600" />
                      </Link>
                    ))
                  )}
                </Panel>
              )}

              {tab === "timeline" && (
                <Panel className="p-5">
                  <h3 className="mb-3 text-sm font-semibold text-white">Investigation Timeline</h3>
                  <p className="mb-4 text-xs text-slate-500">Append-only history — events are never deleted</p>
                  {(detail.timeline || []).length === 0 ? (
                    <p className="text-sm text-slate-500">No timeline events yet</p>
                  ) : (
                    <div className="space-y-3">
                      {detail.timeline.map((ev) => (
                        <div key={ev.id} className="border-l-2 border-cyan-500/40 pl-4">
                          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                            <Clock className="h-3 w-3" />
                            {ev.created_at ? new Date(ev.created_at).toLocaleString() : ""}
                            <span className="rounded bg-[#1F2937] px-1.5 py-0.5 text-[10px] uppercase">
                              {ev.event_type?.replace(/_/g, " ")}
                            </span>
                          </div>
                          <p className="mt-1 text-sm text-slate-200">{ev.summary}</p>
                          <p className="text-xs text-slate-500">{ev.actor_name || ev.actor_id}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </Panel>
              )}

              {tab === "tasks" && (
                <Panel className="p-5">
                  <h3 className="mb-3 text-sm font-semibold text-white">Tasks</h3>
                  <div className="mb-4 flex flex-wrap gap-2">
                    <input
                      value={taskTitle}
                      onChange={(e) => setTaskTitle(e.target.value)}
                      placeholder="Task title…"
                      className="min-w-0 flex-1 rounded-lg border border-[#1F2937] bg-[#0B1120] px-3 py-2 text-sm text-white"
                    />
                    <select
                      value={taskAssignee}
                      onChange={(e) => setTaskAssignee(e.target.value)}
                      className="rounded-lg border border-[#1F2937] bg-[#0B1120] px-3 py-2 text-sm text-white"
                    >
                      <option value="">Assignee…</option>
                      {investigators.map((i) => (
                        <option key={i.id} value={i.id}>{i.name}</option>
                      ))}
                    </select>
                    <button
                      type="button"
                      onClick={handleCreateTask}
                      className="forge-primary-action"
                    >
                      Add Task
                    </button>
                  </div>
                  {(detail.assignments || []).map((a) => (
                    <div key={a.id} className="mb-2 flex items-center justify-between rounded-lg border border-[#1F2937] p-3 last:mb-0">
                      <div>
                        <p className="text-sm text-white">{a.title}</p>
                        <p className="text-xs text-slate-500">{a.assignee_name || a.assignee_id} · {a.priority}</p>
                      </div>
                      <select
                        value={a.status}
                        onChange={(e) => handleTaskStatus(a.id, e.target.value)}
                        className="rounded border border-[#1F2937] bg-[#0B1120] px-2 py-1 text-xs text-white"
                      >
                        {["pending", "in_progress", "completed", "cancelled"].map((s) => (
                          <option key={s} value={s}>{s}</option>
                        ))}
                      </select>
                    </div>
                  ))}
                </Panel>
              )}

              {tab === "comments" && (
                <Panel className="p-5">
                  <h3 className="mb-3 text-sm font-semibold text-white">Comments</h3>
                  <div className="mb-3 flex gap-2">
                    <input
                      value={comment}
                      onChange={(e) => setComment(e.target.value)}
                      placeholder="Add a comment…"
                      className="forge-input flex-1"
                      onKeyDown={(e) => e.key === "Enter" && handleComment()}
                    />
                    <button type="button" onClick={handleComment} className="forge-primary-action">Post</button>
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
                </Panel>
              )}

              {tab === "audit" && (
                <Panel className="p-5">
                  <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">
                    <Shield className="h-4 w-4 text-emerald-400" />
                    Audit Log
                  </h3>
                  <p className="mb-4 text-xs text-slate-500">
                    Immutable forensic audit trail — all case operations are recorded
                  </p>
                  {(detail.audit_log || []).length === 0 ? (
                    <p className="text-sm text-slate-500">No audit entries</p>
                  ) : (
                    <div className="max-h-96 overflow-y-auto">
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="border-b border-[#1F2937] text-slate-500">
                            <th className="py-2 pr-2">Time</th>
                            <th className="py-2 pr-2">Action</th>
                            <th className="py-2 pr-2">Actor</th>
                            <th className="py-2">Details</th>
                          </tr>
                        </thead>
                        <tbody>
                          {detail.audit_log.map((ev) => (
                            <tr key={ev.id} className="border-b border-[#1F2937]/50">
                              <td className="py-2 pr-2 text-slate-500 whitespace-nowrap">
                                {ev.timestamp ? new Date(ev.timestamp).toLocaleString() : ""}
                              </td>
                              <td className="py-2 pr-2 font-mono text-cyan-400/80">{ev.action}</td>
                              <td className="py-2 pr-2 text-slate-400">{ev.user_name}</td>
                              <td className="py-2 text-slate-300">
                                {ev.details?.summary || ev.resource_id || "—"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </Panel>
              )}
            </motion.div>
          ) : (
            <Panel className="flex h-32 items-center justify-center">
              <AlertCircle className="mr-2 h-4 w-4 text-red-400" />
              <p className="text-sm text-slate-500">Failed to load case</p>
            </Panel>
          )}
        </div>
      </div>
    </AppLayout>
  );
}

export default Cases;
