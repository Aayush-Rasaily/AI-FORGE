import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Eye,
  FileText,
  Database,
  Video,
  Sparkles,
  ScanFace,
  PenLine,
  Scale,
  Loader2,
  AlertCircle,
} from "lucide-react";

import { runJuryAnalysis } from "../../services/api";
import JuryDashboard from "./JuryDashboard";

const AGENT_ICONS = {
  vision: Eye,
  metadata: Database,
  ocr: FileText,
  video: Video,
  gan: Sparkles,
  deepfake: ScanFace,
  signature: PenLine,
};

function AIJuryPanel({
  imageResults = [],
  documentResult,
  signatureResult,
  videoResult,
}) {
  const [juryResult, setJuryResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const primaryImage = imageResults[0];
  const hasEvidence =
    imageResults.length > 0 ||
    documentResult ||
    signatureResult ||
    videoResult;

  useEffect(() => {
    const hasAnalysis =
      primaryImage?.analysis ||
      primaryImage?.tampering ||
      documentResult ||
      signatureResult ||
      videoResult;

    if (!hasAnalysis) {
      setJuryResult(null);
      return;
    }

    let cancelled = false;

    async function fetchJury() {
      setLoading(true);
      setError("");
      try {
        const result = await runJuryAnalysis({
          evidenceId: primaryImage?.evidenceId,
          filename: primaryImage?.filename,
          analysis: primaryImage?.analysis,
          tampering: primaryImage?.tampering,
          documentAnalysis: documentResult,
          videoAnalysis: videoResult,
          signatureResult,
        });
        if (!cancelled) setJuryResult(result);
      } catch (err) {
        if (!cancelled) {
          setError(err.message || "Failed to run AI Jury analysis.");
          setJuryResult(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchJury();
    return () => {
      cancelled = true;
    };
  }, [primaryImage, documentResult, signatureResult, videoResult]);

  if (!hasEvidence) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="rounded-2xl border border-[#1F2937] bg-[#111827]/60 p-12 text-center"
      >
        <Scale className="mx-auto h-12 w-12 text-slate-600" />
        <h3 className="mt-4 text-xl font-bold text-white">AI Jury System</h3>
        <p className="mt-2 text-sm text-slate-500">
          Analyze evidence first. Seven independent agents will vote separately
          and produce a weighted majority verdict with minority opinions.
        </p>
      </motion.div>
    );
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center rounded-2xl border border-[#1F2937] bg-[#111827]/60 p-16">
        <Loader2 className="h-10 w-10 animate-spin text-purple-400" />
        <p className="mt-4 text-sm text-slate-400">
          Deliberating — Vision · Metadata · OCR · Video · GAN · Deepfake · Signature...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-8 text-center">
        <AlertCircle className="mx-auto h-8 w-8 text-red-400" />
        <p className="mt-3 text-sm text-red-300">{error}</p>
      </div>
    );
  }

  if (!juryResult) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="rounded-2xl border border-amber-500/20 bg-amber-500/5 p-12 text-center"
      >
        <AlertCircle className="mx-auto h-12 w-12 text-amber-400" />
        <h3 className="mt-4 text-xl font-bold text-white">Forensic Data Required</h3>
        <p className="mt-2 text-sm text-slate-400">
          Run image, document, video, or signature analysis first, then return here.
        </p>
      </motion.div>
    );
  }

  return <JuryDashboard juryResult={juryResult} agentIcons={AGENT_ICONS} />;
}

export default AIJuryPanel;
