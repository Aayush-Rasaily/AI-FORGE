import { useState } from "react";
import { motion } from "framer-motion";
import { MessageSquare, Send, Loader2 } from "lucide-react";
import { askInvestigatorCopilot } from "../../services/api";

function InvestigatorCopilot({ evidenceId }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const ask = async (e) => {
    e?.preventDefault?.();
    if (!question.trim() || loading) return;
    setLoading(true);
    setError("");
    try {
      const res = await askInvestigatorCopilot(question.trim(), evidenceId);
      setAnswer(res.answer || "");
      setSources(res.sources || []);
    } catch (err) {
      setError(err.message || "Copilot unavailable");
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-5 backdrop-blur-xl"
    >
      <div className="mb-3 flex items-center gap-2">
        <MessageSquare className="h-4 w-4 text-violet-400" />
        <h3 className="text-sm font-semibold text-white">Investigator Copilot</h3>
      </div>
      <p className="mb-3 text-xs text-slate-500">
        Ask why evidence is forged, which metadata matters, or whether we have seen similar cases.
      </p>

      <form onSubmit={ask} className="flex gap-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Why is this forged?"
          className="min-w-0 flex-1 rounded-xl border border-[#1F2937] bg-[#0B1120] px-3 py-2 text-xs text-slate-200 outline-none ring-cyan-500/30 placeholder:text-slate-600 focus:ring-2"
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="inline-flex items-center gap-1.5 rounded-xl bg-violet-600/80 px-3 py-2 text-xs font-medium text-white hover:bg-violet-500 disabled:opacity-50"
        >
          {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
          Ask
        </button>
      </form>

      {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
      {answer && (
        <div className="mt-3 rounded-xl border border-violet-500/20 bg-violet-500/5 p-3">
          <p className="text-xs leading-relaxed text-slate-300">{answer}</p>
          {sources.length > 0 && (
            <p className="mt-2 text-[10px] text-slate-500">
              Sources: {sources.map((s) => s.evidence_id).filter(Boolean).join(", ")}
            </p>
          )}
        </div>
      )}
    </motion.div>
  );
}

export default InvestigatorCopilot;
