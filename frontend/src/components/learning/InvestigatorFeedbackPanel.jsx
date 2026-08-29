import { useState } from "react";
import { motion } from "framer-motion";
import { Check, X, Loader2, ThumbsUp } from "lucide-react";
import { submitDetectorFeedback } from "../../services/api";

function InvestigatorFeedbackPanel({
  evidenceId,
  predictedVerdict,
  predictedRisk,
  onSubmitted,
}) {
  const [submitting, setSubmitting] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const handleFeedback = async (correct) => {
    if (!evidenceId || submitting) return;
    setSubmitting(correct ? "correct" : "wrong");
    setError("");
    setMessage("");
    try {
      const res = await submitDetectorFeedback({
        evidence_id: evidenceId,
        correct,
        predicted_verdict: predictedVerdict,
        predicted_risk: predictedRisk,
      });
      setMessage(
        res.message ||
          "Feedback recorded. Detector fusion weights updated — models were not retrained."
      );
      onSubmitted?.(res);
    } catch (err) {
      setError(err.message || "Failed to submit feedback");
    } finally {
      setSubmitting(null);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-4 backdrop-blur-xl"
    >
      <div className="mb-3 flex items-center gap-2">
        <ThumbsUp className="h-4 w-4 text-cyan-400" />
        <h3 className="text-sm font-semibold text-white">Investigator Feedback</h3>
      </div>
      <p className="mb-3 text-xs text-slate-500">
        Rate this analysis to improve detector reliability weighting. Models are never retrained automatically.
      </p>

      <div className="flex gap-2">
        <button
          type="button"
          disabled={!!submitting}
          onClick={() => handleFeedback(true)}
          className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-2.5 text-sm font-medium text-emerald-400 transition hover:bg-emerald-500/20 disabled:opacity-50"
        >
          {submitting === "correct" ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Check className="h-4 w-4" />
          )}
          Correct
        </button>
        <button
          type="button"
          disabled={!!submitting}
          onClick={() => handleFeedback(false)}
          className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2.5 text-sm font-medium text-red-400 transition hover:bg-red-500/20 disabled:opacity-50"
        >
          {submitting === "wrong" ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <X className="h-4 w-4" />
          )}
          Wrong
        </button>
      </div>

      {message && (
        <p className="mt-3 text-xs text-emerald-400">{message}</p>
      )}
      {error && (
        <p className="mt-3 text-xs text-red-400">{error}</p>
      )}
    </motion.div>
  );
}

export default InvestigatorFeedbackPanel;
