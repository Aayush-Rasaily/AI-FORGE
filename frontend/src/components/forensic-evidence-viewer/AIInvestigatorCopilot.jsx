import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Bot,
  Send,
  Loader2,
  Sparkles,
  ShieldCheck,
  ChevronDown,
  Trash2,
} from "lucide-react";
import { askCopilot, ConnectivityError, formatApiError } from "../../services/api";
import { useBackend } from "../../context/BackendConnectivity";

const SUGGESTED = [
  "Why is this image suspicious?",
  "Which region is edited?",
  "Where was the amount changed?",
  "Explain detector disagreement.",
  "Show only edited areas.",
  "Summarize this case.",
  "What evidence supports the verdict?",
  "Generate a court-ready explanation.",
  "Which detector has the highest confidence?",
  "Why did OCR fail?",
  "Compare original vs suspicious region.",
];

function MessageBubble({ role, content, intent }) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[95%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
          isUser
            ? "bg-cyan-600/20 text-cyan-50 ring-1 ring-cyan-500/30"
            : "bg-[#111827] text-slate-200 ring-1 ring-[#1F2937]"
        }`}
      >
        {!isUser && intent && (
          <p className="mb-1 text-[10px] uppercase tracking-wider text-slate-500">{intent.replace(/_/g, " ")}</p>
        )}
        <p className="whitespace-pre-wrap">{content}</p>
      </div>
    </div>
  );
}

function AIInvestigatorCopilot({ evidenceId, regions = [], onCopilotAction }) {
  const { online } = useBackend();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [sessionId, setSessionId] = useState(null);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const scrollRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    setMessages([]);
    setSessionId(null);
    setError("");
  }, [evidenceId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  const applyActions = useCallback(
    (actions) => {
      if (!actions || !onCopilotAction) return;
      const regionId = actions.zoom_region_id || actions.highlight_region_id;
      const region = regions.find((r) => r.id === regionId) || regions[0];
      onCopilotAction({
        ...actions,
        region,
      });
    },
    [onCopilotAction, regions]
  );

  const send = useCallback(
    async (text) => {
      const q = (text || input).trim();
      if (!q || !evidenceId || !online || loading) return;

      setInput("");
      setShowSuggestions(false);
      setError("");
      setMessages((m) => [...m, { role: "user", content: q }]);
      setLoading(true);

      try {
        const res = await askCopilot(evidenceId, q, { sessionId });
        if (res.session_id) setSessionId(res.session_id);
        const answer = res.message || res.answer || "No response recorded.";
        setMessages((m) => [
          ...m,
          { role: "assistant", content: answer, intent: res.intent },
        ]);
        applyActions(res.actions);
      } catch (err) {
        const msg =
          err instanceof ConnectivityError
            ? "Backend offline — copilot paused."
            : formatApiError(err, "Copilot request failed");
        setError(msg);
        setMessages((m) => [...m, { role: "assistant", content: msg, intent: "error" }]);
      } finally {
        setLoading(false);
        inputRef.current?.focus();
      }
    },
    [input, evidenceId, online, loading, sessionId, applyActions]
  );

  const clearChat = () => {
    setMessages([]);
    setSessionId(null);
    setShowSuggestions(true);
    setError("");
  };

  if (!evidenceId) {
    return (
      <div className="rounded-2xl border border-dashed border-[#1F2937] bg-[#111827]/40 p-5 text-center text-xs text-slate-500">
        Complete forensic analysis to enable the AI Investigator.
      </div>
    );
  }

  return (
    <motion.aside
      initial={{ opacity: 0, x: 12 }}
      animate={{ opacity: 1, x: 0 }}
      className="flex h-full min-h-[420px] flex-col overflow-hidden rounded-2xl border border-violet-500/25 bg-[#111827]/95 shadow-xl shadow-violet-950/10"
    >
      <div className="flex items-center justify-between border-b border-[#1F2937] px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="rounded-lg bg-violet-500/15 p-1.5">
            <Bot className="h-4 w-4 text-violet-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">AI Investigator</h3>
            <p className="flex items-center gap-1 text-[10px] text-slate-500">
              <ShieldCheck className="h-3 w-3 text-emerald-500" />
              Evidence-grounded only
            </p>
          </div>
        </div>
        {messages.length > 0 && (
          <button
            type="button"
            onClick={clearChat}
            className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-800 hover:text-slate-300"
            title="Clear conversation"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-3 py-3 scrollbar-thin">
        {messages.length === 0 && (
          <div className="rounded-xl border border-[#1F2937] bg-[#0B1120]/80 p-3 text-xs text-slate-400">
            <p className="flex items-center gap-1.5 font-medium text-slate-300">
              <Sparkles className="h-3.5 w-3.5 text-violet-400" />
              Ask about this evidence
            </p>
            <p className="mt-1.5 leading-relaxed">
              Answers cite detector outputs, fusion, localization, jury, and reports only — never invented evidence.
            </p>
          </div>
        )}

        <AnimatePresence initial={false}>
          {messages.map((msg, i) => (
            <motion.div
              key={`${msg.role}-${i}`}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <MessageBubble role={msg.role} content={msg.content} intent={msg.intent} />
            </motion.div>
          ))}
        </AnimatePresence>

        {loading && (
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Loader2 className="h-3.5 w-3.5 animate-spin text-violet-400" />
            Analyzing forensic record…
          </div>
        )}
      </div>

      {showSuggestions && messages.length === 0 && (
        <div className="border-t border-[#1F2937] px-3 py-2">
          <button
            type="button"
            onClick={() => setShowSuggestions((s) => !s)}
            className="mb-1 flex w-full items-center justify-between text-[10px] uppercase tracking-wider text-slate-500"
          >
            Suggested questions
            <ChevronDown className={`h-3 w-3 transition ${showSuggestions ? "" : "rotate-180"}`} />
          </button>
          <div className="flex flex-wrap gap-1.5">
            {SUGGESTED.slice(0, 6).map((q) => (
              <button
                key={q}
                type="button"
                onClick={() => send(q)}
                disabled={!online || loading}
                className="rounded-lg border border-[#1F2937] bg-[#0B1120] px-2 py-1 text-[10px] text-slate-400 transition hover:border-violet-500/40 hover:text-violet-200 disabled:opacity-40"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {error && (
        <p className="px-3 text-[10px] text-amber-400">{error}</p>
      )}

      <form
        className="border-t border-[#1F2937] p-3"
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
      >
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={online ? "Ask the AI Investigator…" : "Backend offline"}
            disabled={!online || loading}
            className="min-w-0 flex-1 rounded-xl border border-[#1F2937] bg-[#0B1120] px-3 py-2 text-sm text-white placeholder:text-slate-600 focus:border-violet-500/50 focus:outline-none focus:ring-1 focus:ring-violet-500/30 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!online || loading || !input.trim()}
            className="inline-flex items-center justify-center rounded-xl bg-violet-600 px-3 py-2 text-white transition hover:bg-violet-500 disabled:opacity-40"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </button>
        </div>
      </form>
    </motion.aside>
  );
}

export default AIInvestigatorCopilot;
