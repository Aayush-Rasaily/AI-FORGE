import { useState } from "react";
import { Upload, ScanSearch, AlertCircle } from "lucide-react";

import AppLayout from "../components/layout/AppLayout";
import GlassCard from "../components/ui/GlassCard";
import StatusBadge from "../components/ui/StatusBadge";
import ProgressBar from "../components/ui/ProgressBar";

import {
    uploadEvidence,
    analyzeCopyMove,
    getCopyMoveArtifactUrl
} from "../services/api";


function CopyMoveDetection() {

    const [file, setFile] = useState(null);

    const [evidenceId, setEvidenceId] = useState("");

    const [result, setResult] = useState(null);

    const [loading, setLoading] = useState(false);

    const [error, setError] = useState("");

    const [artifactUrl, setArtifactUrl] = useState("");


    // ==========================================
    // SELECT FILE
    // ==========================================

    function handleFileChange(event) {

        const selectedFile =
            event.target.files[0];

        if (!selectedFile) {
            return;
        }

        setFile(selectedFile);

        setResult(null);

        setEvidenceId("");

        setArtifactUrl("");

        setError("");
    }


    // ==========================================
    // ANALYZE IMAGE
    // ==========================================

    async function handleAnalyze() {

        if (!file) {

            setError(
                "Please select an image first."
            );

            return;
        }


        try {

            setLoading(true);

            setError("");

            setResult(null);

            setArtifactUrl("");


            // ==================================
            // STEP 1: UPLOAD EVIDENCE
            // ==================================

            const uploadResult =
                await uploadEvidence(file);


            const id =
                uploadResult.evidence_id;


            setEvidenceId(id);


            console.log(
                "Evidence ID:",
                id
            );


            // ==================================
            // STEP 2: RUN COPY-MOVE ANALYSIS
            // ==================================

            const analysisResult =
                await analyzeCopyMove(id);


            console.log(
                "Copy-Move Analysis Result:",
                analysisResult
            );


            setResult(
                analysisResult.analysis
            );


            // ==================================
            // STEP 3: GENERATE ARTIFACT URL
            // ==================================

            const generatedArtifactUrl =
                getCopyMoveArtifactUrl(id);


            console.log(
                "Copy-Move Artifact URL:",
                generatedArtifactUrl
            );


            setArtifactUrl(
                generatedArtifactUrl
            );


        } catch (error) {

            console.error(
                "Copy-Move Analysis Error:",
                error
            );


            setError(

                error?.response?.data?.detail

                ||

                error.message

                ||

                "Analysis failed"

            );


        } finally {

            setLoading(false);

        }

    }


    // ==========================================
    // RENDER
    // ==========================================

    return (

        <AppLayout
            title="Copy-Move Detection"
            subtitle="Detect duplicated or copied regions within images"
        >

            {/* ================================= */}
            {/* PAGE HEADER                       */}
            {/* ================================= */}

            <div className="mb-8">

                <h2 className="text-3xl font-bold tracking-tight text-white md:text-4xl">

                    Copy-Move Detection

                </h2>

                <p className="mt-3 text-slate-400">

                    Detect duplicated or copied regions
                    within an image using ORB feature
                    matching and RANSAC analysis.

                </p>

            </div>


            {/* ================================= */}
            {/* UPLOAD CARD                       */}
            {/* ================================= */}

            <GlassCard gradient="cyan" className="mb-8">

                <div className="flex items-center gap-3 mb-4">

                    <div className="rounded-lg bg-cyan-500/10 p-2.5">

                        <Upload className="h-5 w-5 text-cyan-400" />

                    </div>

                    <div>

                        <h3 className="text-xl font-semibold text-white">

                            Upload Evidence

                        </h3>

                        <p className="text-sm text-slate-400">

                            Upload an image to analyze for copy-move manipulation.

                        </p>

                    </div>

                </div>


                <div className="upload-zone rounded-xl p-8 text-center">

                    <ScanSearch className="mx-auto h-10 w-10 text-slate-500" />

                    <p className="mt-4 text-sm text-slate-400">

                        Select an image file to begin analysis

                    </p>


                    <label className="mt-4 inline-flex cursor-pointer items-center gap-2 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 px-6 py-2.5 text-sm font-semibold text-white shadow-lg shadow-cyan-500/20 transition hover:from-cyan-500 hover:to-blue-500">

                        Choose File

                        <input
                            type="file"
                            accept="image/*"
                            onChange={handleFileChange}
                            className="hidden"
                        />

                    </label>

                </div>


                {file && (

                    <p className="mt-4 text-sm text-cyan-400">

                        Selected: {file.name}

                    </p>

                )}


                <button

                    onClick={handleAnalyze}

                    disabled={loading || !file}

                    className="mt-6 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 px-6 py-3 font-semibold text-white shadow-lg shadow-cyan-500/20 transition hover:from-cyan-500 hover:to-blue-500 disabled:cursor-not-allowed disabled:opacity-50"

                >

                    {loading ? "Analyzing..." : "Analyze Image"}

                </button>


                {loading && (

                    <div className="mt-4">

                        <ProgressBar
                            value={65}
                            label="Running ORB + RANSAC analysis..."
                            color="cyan"
                        />

                    </div>

                )}


                {error && (

                    <div className="mt-4 flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-red-400">

                        <AlertCircle className="h-4 w-4 shrink-0" />

                        {error}

                    </div>

                )}

            </GlassCard>


            {/* ================================= */}
            {/* ANALYSIS RESULT                   */}
            {/* ================================= */}

            {result && (

                <GlassCard gradient="blue">

                    <h3 className="text-2xl font-bold text-white">

                        Analysis Result

                    </h3>


                    {/* ================================= */}
                    {/* VERDICT                           */}
                    {/* ================================= */}

                    <div className="mt-6 flex items-center gap-4">

                        <div>

                            <p className="text-sm text-slate-400">

                                Verdict

                            </p>

                            <p
                                className={`mt-1 text-3xl font-bold ${
                                    result.copy_move_detected
                                        ? "text-red-400"
                                        : "text-emerald-400"
                                }`}
                            >

                                {result.verdict}

                            </p>

                        </div>


                        <StatusBadge status={result.verdict} />

                    </div>


                    {/* ================================= */}
                    {/* METRICS                           */}
                    {/* ================================= */}

                    <div className="mt-8 grid gap-4 sm:grid-cols-3">

                        <div className="rounded-lg bg-slate-800/50 p-5">

                            <p className="text-sm text-slate-400">

                                Copy-Move Score

                            </p>

                            <p className="mt-2 text-2xl font-bold text-white">

                                {result.score}

                            </p>

                            <ProgressBar
                                value={result.score}
                                max={100}
                                color={result.score > 50 ? "red" : "green"}
                                showPercent={false}
                                className="mt-3"
                            />

                        </div>


                        <div className="rounded-lg bg-slate-800/50 p-5">

                            <p className="text-sm text-slate-400">

                                Matched Points

                            </p>

                            <p className="mt-2 text-2xl font-bold text-white">

                                {result.matched_points}

                            </p>

                        </div>


                        <div className="rounded-lg bg-slate-800/50 p-5">

                            <p className="text-sm text-slate-400">

                                RANSAC Inliers

                            </p>

                            <p className="mt-2 text-2xl font-bold text-white">

                                {result.inliers}

                            </p>

                        </div>

                    </div>


                    {/* ================================= */}
                    {/* EVIDENCE ID                       */}
                    {/* ================================= */}

                    {evidenceId && (

                        <div className="mt-8">

                            <p className="text-sm text-slate-400">

                                Evidence ID

                            </p>

                            <p className="mt-2 break-all rounded-lg bg-slate-800/50 p-3 font-mono text-sm text-slate-300">

                                {evidenceId}

                            </p>

                        </div>

                    )}


                    {/* ================================= */}
                    {/* COPY-MOVE VISUALIZATION           */}
                    {/* ================================= */}

                    <div className="mt-10">

                        <h3 className="text-xl font-semibold text-white">

                            Copy-Move Forensic Visualization

                        </h3>

                        <p className="mt-2 text-sm text-slate-400">

                            Highlighted regions indicate feature matches
                            identified by the copy-move detection algorithm.

                        </p>


                        {artifactUrl ? (

                            <div className="mt-6 overflow-hidden rounded-xl border border-slate-700/50 bg-black/50">

                                <img
                                    src={artifactUrl}
                                    alt="Copy-Move Detection Visualization"
                                    className="max-h-[600px] w-full object-contain"
                                    onLoad={() => {
                                        console.log(
                                            "Copy-Move artifact loaded successfully"
                                        );
                                    }}
                                    onError={(event) => {
                                        console.error(
                                            "Failed to load Copy-Move artifact:",
                                            artifactUrl
                                        );
                                        event.currentTarget.style.display = "none";
                                        setError(
                                            `Unable to load visualization. URL: ${artifactUrl}`
                                        );
                                    }}
                                />

                            </div>

                        ) : (

                            <p className="mt-6 text-sm text-slate-500">

                                Visualization unavailable

                            </p>

                        )}

                    </div>

                </GlassCard>

            )}

        </AppLayout>

    );

}


export default CopyMoveDetection;
