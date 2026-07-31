import { useState } from "react";
import { useNavigate } from "react-router-dom";

import {
    uploadEvidence,
    analyzeCopyMove,
    getCopyMoveArtifactUrl
} from "../services/api";

function CopyMoveDetection() {

    const navigate = useNavigate();


    const [file, setFile] =
        useState(null);


    const [evidenceId, setEvidenceId] =
        useState("");


    const [result, setResult] =
        useState(null);


    const [loading, setLoading] =
        useState(false);


    const [error, setError] =
        useState("");
    
    const [artifactUrl, setArtifactUrl] = useState("");


    // --------------------------------
    // Select File
    // --------------------------------

    function handleFileChange(event) {

        const selectedFile =
            event.target.files[0];


        if (!selectedFile) {
            return;
        }


        setFile(
            selectedFile
        );


        setResult(null);

        setError("");

    }


    // --------------------------------
    // Analyze
    // --------------------------------

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


            // --------------------------
            // Upload
            // --------------------------

            const uploadResult =
                await uploadEvidence(
                    file
                );


            const id =
                uploadResult.evidence_id;


            setEvidenceId(
                id
            );


            // --------------------------
            // Copy-Move Analysis
            // --------------------------

            const analysisResult =
                await analyzeCopyMove(
                    id
                );


            setResult(
                analysisResult.analysis
            );


            // Generate artifact URL
            const artifactUrl =
                getCopyMoveArtifactUrl(
                    id
                );


            setArtifactUrl(
                artifactUrl
            );


        } catch (error) {

            setError(
                error.message ||
                "Analysis failed"
            );


        } finally {

            setLoading(false);

        }

    }


    return (

        <div className="min-h-screen bg-slate-950 text-white">


            {/* ================================ */}
            {/* Navbar */}
            {/* ================================ */}

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


            {/* ================================ */}
            {/* Main */}
            {/* ================================ */}

            <main className="mx-auto max-w-5xl px-8 py-12">


                <h2 className="text-4xl font-bold">

                    Copy-Move Detection

                </h2>


                <p className="mt-3 text-slate-400">

                    Detect duplicated or copied regions
                    within an image using ORB feature
                    matching and RANSAC analysis.

                </p>


                {/* ================================ */}
                {/* Upload Card */}
                {/* ================================ */}

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


                {/* ================================ */}
                {/* Result */}
                {/* ================================ */}
                {artifactUrl && (

    <div className="mt-10">

        <h3 className="text-xl font-semibold">

            Forensic Visualization

        </h3>

        <p className="mt-2 text-sm text-slate-400">

            Highlighted regions represent
            areas associated with detected
            feature matches.

        </p>


        <div className="mt-6 overflow-hidden rounded-xl border border-slate-700">

            <img

                src={artifactUrl}

                alt="Copy-Move Detection Result"

                className="w-full"

            />

        </div>

    </div>

)}
                
                {result && (

                    <div className="mt-10 rounded-xl border border-slate-800 bg-slate-900 p-8">


                        <h3 className="text-2xl font-bold">

                            Analysis Result

                        </h3>


                        {/* Verdict */}

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


                        {/* Metrics */}

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


                        {/* Evidence ID */}

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
                        
                        {/* ================================ */}
                        {/* Forensic Visualization */}
                        {/* ================================ */}

                        {artifactUrl && (

                            <div className="mt-10">

                                <h3 className="text-xl font-semibold">

                                    Copy-Move Forensic Visualization

                                </h3>


                                <p className="mt-2 text-sm text-slate-400">

                                    Highlighted regions indicate
                                    feature matches identified by
                                    the copy-move detection algorithm.

                                </p>


                                <div className="mt-6 overflow-hidden rounded-xl border border-slate-700 bg-slate-950">

                                    <img

                                        src={artifactUrl}

                                        alt="Copy-Move Detection Visualization"

                                        className="w-full object-contain"

                                    />

                                </div>

                            </div>

                        )}

                    </div>

                )}
                

            </main>

        </div>

    );

}


export default CopyMoveDetection;