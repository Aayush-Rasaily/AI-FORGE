import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

import AppLayout from "../components/layout/AppLayout";
import AnalysisSelector from "../components/AnalysisSelector";
import EvidenceUploader from "../components/EvidenceUploader";
import ImageForensics from "../components/ImageForensics";
import SignatureVerification from "../components/SignatureVerification";
import DocumentForensics from "../components/DocumentForensics";
import VideoForensics from "../components/VideoForensics";
import UnifiedFraudDashboard from "../components/UnifiedFraudDashboard";
import EvidenceTimeline from "../components/investigation/EvidenceTimeline";
import ChainOfCustodyPanel from "../components/investigation/ChainOfCustodyPanel";
import ExportReportPanel from "../components/investigation/ExportReportPanel";
import AIJuryPanel from "../components/investigation/AIJuryPanel";
import HeatmapViewer from "../components/investigation/HeatmapViewer";
import DeepFakeForensics from "../components/investigation/DeepFakeForensics";

function Investigation() {
  const [analysisType, setAnalysisType] = useState("image");
  const [files, setFiles] = useState([]);
  const [processing, setProcessing] = useState(false);
  const [results, setResults] = useState([]);
  const [selectedEvidenceId, setSelectedEvidenceId] = useState(null);
  const [signatureResult, setSignatureResult] = useState(null);
  const [videoResult, setVideoResult] = useState(null);
  const [error, setError] = useState("");
  const [sidePanelOpen, setSidePanelOpen] = useState(true);

  const handleAnalysisTypeChange = (type) => {
    setAnalysisType(type);
    setFiles([]);
    setProcessing(false);
    setError("");
  };

  const imageResults = results.filter(
    (item) => item.fileType === "image" && item.status === "completed"
  );

  const documentResult = results.find(
    (item) =>
      (item.fileType === "document" || item.fileType === "pdf") &&
      item.status === "completed"
  );

  const documentAnalysis = documentResult?.documentAnalysis || null;

  useEffect(() => {
    const latest = results.find((r) => r.evidenceId && r.status === "completed");
    if (latest?.evidenceId && !selectedEvidenceId) {
      setSelectedEvidenceId(latest.evidenceId);
    }
  }, [results, selectedEvidenceId]);

  return (
    <AppLayout
      title="Investigation Workspace"
      subtitle="Multimodal evidence analysis & AI jury synthesis"
    >
      {/* Workspace Header */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6"
      >
        <h2 className="text-2xl font-bold text-white md:text-3xl">
          Investigation Workspace
        </h2>
        <p className="mt-2 text-sm text-slate-400">
          Upload evidence, run forensic pipelines, and synthesize AI jury verdicts.
        </p>
      </motion.div>

      {/* Workspace Layout: Side Panel + Main */}
      <div className="flex flex-col gap-6 xl:flex-row">
        {/* Evidence Explorer / Timeline Side Panel */}
        <AnimatePresence>
          {sidePanelOpen && (
            <motion.aside
              initial={{ opacity: 0, x: -20, width: 0 }}
              animate={{ opacity: 1, x: 0, width: "auto" }}
              exit={{ opacity: 0, x: -20, width: 0 }}
              className="w-full shrink-0 xl:w-72"
            >
              <EvidenceTimeline
                results={results}
                selectedEvidenceId={selectedEvidenceId}
                onSelect={setSelectedEvidenceId}
              />
              <div className="mt-4">
                <ChainOfCustodyPanel evidenceId={selectedEvidenceId} />
              </div>
              <div className="mt-4">
                <ExportReportPanel
                  evidenceId={selectedEvidenceId}
                  juryData={results.find((r) => r.evidenceId === selectedEvidenceId)?.jury}
                  reportsPending={
                    results.find((r) => r.evidenceId === selectedEvidenceId)?.reportsPending ?? true
                  }
                />
              </div>
            </motion.aside>
          )}
        </AnimatePresence>

        {/* Main Content */}
        <div className="min-w-0 flex-1">
          <AnalysisSelector
            analysisType={analysisType}
            setAnalysisType={handleAnalysisTypeChange}
          />

          <AnimatePresence mode="wait">
            <motion.div
              key={analysisType}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.25 }}
            >
              {analysisType === "image" && (
                <>
                  <EvidenceUploader
                    files={files}
                    setFiles={setFiles}
                    processing={processing}
                    setProcessing={setProcessing}
                    setResults={setResults}
                    error={error}
                    setError={setError}
                    analysisType={analysisType}
                  />
                  <ImageForensics files={files} results={imageResults} />
                </>
              )}

              {analysisType === "signature" && (
                <SignatureVerification onResult={setSignatureResult} />
              )}

              {analysisType === "document" && (
                <>
                  <EvidenceUploader
                    files={files}
                    setFiles={setFiles}
                    processing={processing}
                    setProcessing={setProcessing}
                    setResults={setResults}
                    error={error}
                    setError={setError}
                    analysisType={analysisType}
                  />
                  <DocumentForensics result={documentAnalysis} />
                </>
              )}

              {analysisType === "video" && (
                <VideoForensics onResult={setVideoResult} />
              )}

              {analysisType === "dashboard" && (
                <UnifiedFraudDashboard
                  imageResults={imageResults}
                  documentResult={documentAnalysis}
                  signatureResult={signatureResult}
                  videoResult={videoResult}
                />
              )}

              {analysisType === "jury" && (
                <AIJuryPanel
                  imageResults={imageResults}
                  documentResult={documentAnalysis}
                  signatureResult={signatureResult}
                  videoResult={videoResult}
                />
              )}

              {analysisType === "heatmap" && (
                <>
                  {imageResults.length === 0 && (
                    <EvidenceUploader
                      files={files}
                      setFiles={setFiles}
                      processing={processing}
                      setProcessing={setProcessing}
                      setResults={setResults}
                      error={error}
                      setError={setError}
                      analysisType="image"
                    />
                  )}
                  <HeatmapViewer
                    evidenceId={imageResults[0]?.evidenceId}
                    filename={imageResults[0]?.filename}
                  />
                </>
              )}

              {analysisType === "deepfake" && (
                <DeepFakeForensics imageResults={imageResults} />
              )}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </AppLayout>
  );
}

export default Investigation;
