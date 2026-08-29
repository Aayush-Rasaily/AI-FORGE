import { useEffect, useState } from "react";
import { FolderSearch, Plus, Loader2, AlertCircle } from "lucide-react";
import { listCases, createCase } from "../../services/api";

function CaseSelector({ value, onChange, className = "" }) {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [error, setError] = useState("");

  const load = () => {
    setLoading(true);
    listCases(100)
      .then((res) => setCases(res.cases || []))
      .catch(() => setCases([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const handleCreate = async () => {
    if (!newTitle.trim()) return;
    setCreating(true);
    setError("");
    try {
      const res = await createCase(newTitle.trim());
      const created = res.case;
      setCases((prev) => [created, ...prev]);
      onChange?.(created.id);
      setNewTitle("");
    } catch (err) {
      setError(err.message || "Failed to create case");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className={`space-y-2 ${className}`}>
      <label className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-slate-500">
        <FolderSearch className="h-3.5 w-3.5" />
        Active Case <span className="text-red-400">*</span>
      </label>
      <div className="flex gap-2">
        <select
          value={value || ""}
          onChange={(e) => onChange?.(e.target.value || null)}
          disabled={loading}
          className="min-w-0 flex-1 rounded-lg border border-[#1F2937] bg-[#0B1120] px-3 py-2 text-sm text-white focus:border-cyan-500/50 focus:outline-none"
        >
          <option value="">Select a case…</option>
          {cases.map((c) => (
            <option key={c.id} value={c.id}>
              {c.title} ({c.id}) — {c.status}
            </option>
          ))}
        </select>
        {loading && <Loader2 className="h-5 w-5 animate-spin self-center text-cyan-400" />}
      </div>
      <div className="flex gap-2">
        <input
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          placeholder="New case title…"
          className="min-w-0 flex-1 rounded-lg border border-[#1F2937] bg-[#0B1120] px-3 py-1.5 text-xs text-white placeholder-slate-600 focus:outline-none"
          onKeyDown={(e) => e.key === "Enter" && handleCreate()}
        />
        <button
          type="button"
          onClick={handleCreate}
          disabled={creating || !newTitle.trim()}
          className="flex items-center gap-1 rounded-lg bg-cyan-600/20 px-3 py-1.5 text-xs font-medium text-cyan-400 hover:bg-cyan-600/30 disabled:opacity-50"
        >
          <Plus className="h-3.5 w-3.5" />
          New
        </button>
      </div>
      {!value && (
        <p className="flex items-center gap-1 text-[11px] text-amber-400">
          <AlertCircle className="h-3 w-3" />
          Every upload must belong to a case
        </p>
      )}
      {error && <p className="text-[11px] text-red-400">{error}</p>}
    </div>
  );
}

export default CaseSelector;
