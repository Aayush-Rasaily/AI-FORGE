import { useState } from "react";
import { useNavigate } from "react-router-dom";

import {
    uploadEvidence,
    analyzeCopyMove,
    getCopyMoveArtifactUrl
} from "../services/api";


function CopyMoveDetection() {

    const navigate = useNavigate();

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

        <div className="min-h-screen bg-slate-950 text-white">


            {/* ================================= */}
            {/* NAVBAR */}
            {/* ================================= */}

            <nav className="border-b border-slate-800 px-8 py-5">

                <div className="flex items-center justify-between">

                    <div>

                        <h1 className="text-2xl font-bold">

                            AI-FORGE

                        </h1>


                        <p className="text-sm text-slate-400">

                            Copy-Move Forgery Detection

                        </p>

                    </div>


                    <button

                        onClick={() =>
                            navigate("/")
                        }

                        className="text-sm text-slate-400 hover:text-white"

                    >

                        ← Dashboard

                    </button>

                </div>

            </nav>


            {/* ================================= */}
            {/* MAIN */}
            {/* ================================= */}

            <main className="mx-auto max-w-5xl px-8 py-12">


                <h2 className="text-4xl font-bold">

                    Copy-Move Detection

                </h2>


                <p className="mt-3 text-slate-400">

                    Detect duplicated or copied regions
                    within an image using ORB feature
                    matching and RANSAC analysis.

                </p>


                {/* ================================= */}
                {/* UPLOAD CARD */}
                {/* ================================= */}

                <div className="mt-10 rounded-xl border border-slate-800 bg-slate-900 p-8">


                    <h3 className="text-xl font-semibold">

                        Upload Evidence

                    </h3>


                    <p className="mt-2 text-sm text-slate-400">

                        Upload an image to analyze
                        for potential copy-move manipulation.

                    </p>


                    <input

                        type="file"

                        accept="image/*"

                        onChange={
                            handleFileChange
                        }

                        className="mt-6 block w-full text-sm text-slate-400"

                    />


                    {file && (

                        <p className="mt-4 text-sm text-blue-400">

                            Selected:

                            {" "}

                            {file.name}

                        </p>

                    )}


                    <button

                        onClick={
                            handleAnalyze
                        }

                        disabled={
                            loading ||
                            !file
                        }

                        className="mt-6 rounded-lg bg-blue-600 px-6 py-3 font-semibold transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"

                    >

                        {loading

                            ? "Analyzing..."

                            : "Analyze Image"

                        }

                    </button>


                    {error && (

                        <p className="mt-4 text-red-400">

                            {error}

                        </p>

                    )}

                </div>


                {/* ================================= */}
                {/* ANALYSIS RESULT */}
                {/* ================================= */}

                {result && (

                    <div className="mt-10 rounded-xl border border-slate-800 bg-slate-900 p-8">


                        <h3 className="text-2xl font-bold">

                            Analysis Result

                        </h3>


                        {/* ================================= */}
                        {/* VERDICT */}
                        {/* ================================= */}

                        <div className="mt-6">

                            <p className="text-sm text-slate-400">

                                Verdict

                            </p>


                            <p

                                className={`mt-2 text-3xl font-bold ${
                                    result.copy_move_detected
                                        ? "text-red-400"
                                        : "text-green-400"
                                }`}

                            >

                                {result.verdict}

                            </p>

                        </div>


                        {/* ================================= */}
                        {/* METRICS */}
                        {/* ================================= */}

                        <div className="mt-8 grid gap-6 md:grid-cols-3">


                            <div className="rounded-lg bg-slate-800 p-5">

                                <p className="text-sm text-slate-400">

                                    Copy-Move Score

                                </p>

                                <p className="mt-2 text-2xl font-bold">

                                    {result.score}

                                </p>

                            </div>


                            <div className="rounded-lg bg-slate-800 p-5">

                                <p className="text-sm text-slate-400">

                                    Matched Points

                                </p>

                                <p className="mt-2 text-2xl font-bold">

                                    {result.matched_points}

                                </p>

                            </div>


                            <div className="rounded-lg bg-slate-800 p-5">

                                <p className="text-sm text-slate-400">

                                    RANSAC Inliers

                                </p>

                                <p className="mt-2 text-2xl font-bold">

                                    {result.inliers}

                                </p>

                            </div>

                        </div>


                        {/* ================================= */}
                        {/* EVIDENCE ID */}
                        {/* ================================= */}

                        {evidenceId && (

                            <div className="mt-8">

                                <p className="text-sm text-slate-400">

                                    Evidence ID

                                </p>


                                <p className="mt-2 break-all font-mono text-sm text-slate-300">

                                    {evidenceId}

                                </p>

                            </div>

                        )}


                        {/* ================================= */}
                        {/* COPY-MOVE VISUALIZATION */}
                        {/* ================================= */}

                        <div className="mt-10">


                            <h3 className="text-xl font-semibold">

                                Copy-Move Forensic Visualization

                            </h3>


                            <p className="mt-2 text-sm text-slate-400">

                                Highlighted regions indicate
                                feature matches identified by
                                the copy-move detection algorithm.

                            </p>


                            {artifactUrl ? (

                                <div className="mt-6 overflow-hidden rounded-xl border border-slate-700 bg-black">


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


                                            event.currentTarget.style.display =
                                                "none";


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


                    </div>

                )}

            </main>

        </div>

    );

}


export default CopyMoveDetection;

