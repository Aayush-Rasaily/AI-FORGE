import ArtifactCard from "./ArtifactCard";

import {
    getArtifactUrl
} from "../services/api";


function ImageForensics({
    results = []
}) {

    // ==========================================
    // EMPTY STATE
    // ==========================================

    if (
        !results ||
        results.length === 0
    ) {

        return (

            <div className="mt-10 rounded-xl glass-card p-8 text-center">

                <h2 className="text-xl font-semibold text-slate-200">
                    Forensic Analysis Report
                </h2>

                <p className="mt-3 text-slate-400">
                    No forensic analysis results available.
                </p>

            </div>

        );

    }


    return (

        <div className="mt-10 space-y-10">

            {/* ==========================================
                TITLE
            ========================================== */}

            <div>

                <h2 className="text-2xl font-bold text-white">
                    Forensic Analysis Report
                </h2>

                <p className="mt-2 text-slate-400">
                    Detailed forensic analysis of uploaded evidence.
                </p>

            </div>


            {/* ==========================================
                LOOP THROUGH RESULTS
            ========================================== */}

            {results.map(
                (item, index) => {

                    const filename =
                        item.filename ||
                        `Evidence ${index + 1}`;


                    const evidenceId =
                        item.evidenceId ||
                        item.evidence_id ||
                        "";


                    const analysis =
                        item.analysis ||
                        {};


                    const signals =
                        analysis.signals ||
                        {};


                    const artifacts =
                        analysis.artifacts ||
                        {};


                    const verdict =
                        analysis.verdict ||
                        "Unknown";


                    const forensicScore =
                        Number(
                            analysis.forensic_score || 0
                        );


                    // ==========================================
                    // GET ARTIFACT PATHS FROM BACKEND
                    // ==========================================

                    const elaPath =
                        artifacts.ela ||
                        "";


                    const edgesPath =
                        artifacts.edges ||
                        "";


                    const waveletPath =
                        artifacts.wavelet ||
                        "";


                    const copyMovePath =
                        artifacts.copy_move ||
                        "";


                    // ==========================================
                    // CONVERT PATHS TO FULL BACKEND URL
                    // ==========================================

                    const elaUrl =
                        elaPath
                            ? getArtifactUrl(
                                elaPath
                            )
                            : "";


                    const edgesUrl =
                        edgesPath
                            ? getArtifactUrl(
                                edgesPath
                            )
                            : "";


                    const waveletUrl =
                        waveletPath
                            ? getArtifactUrl(
                                waveletPath
                            )
                            : "";


                    const copyMoveUrl =
                        copyMovePath
                            ? getArtifactUrl(
                                copyMovePath
                            )
                            : "";


                    // ==========================================
                    // DEBUG
                    // ==========================================

                    console.log(
                        "Forensic Analysis Result:",
                        {
                            filename,
                            evidenceId,
                            analysis,
                            artifacts
                        }
                    );


                    console.log(
                        "Artifact URLs:",
                        {
                            elaUrl,
                            edgesUrl,
                            waveletUrl,
                            copyMoveUrl
                        }
                    );


                    return (

                        <div
                            key={
                                evidenceId ||
                                index
                            }

                            className="rounded-2xl border border-slate-800 bg-slate-950 p-6 shadow-xl"
                        >

                            {/* ==========================================
                                HEADER
                            ========================================== */}

                            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">

                                <div>

                                    <h3 className="text-xl font-bold text-white">
                                        {filename}
                                    </h3>


                                    {evidenceId && (

                                        <p className="mt-1 text-sm text-slate-500">

                                            Evidence ID:
                                            {" "}
                                            {evidenceId}

                                        </p>

                                    )}

                                </div>


                                {/* VERDICT */}

                                <div
                                    className={`
                                        rounded-lg px-4 py-2 text-sm font-semibold
                                        ${
                                            verdict === "Authentic"
                                                ? "bg-green-950 text-green-400"
                                                : verdict === "Suspicious"
                                                ? "bg-yellow-950 text-yellow-400"
                                                : "bg-red-950 text-red-400"
                                        }
                                    `}
                                >

                                    {verdict}

                                </div>

                            </div>


                            {/* ==========================================
                                FORENSIC SCORE
                            ========================================== */}

                            <div className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-5">

                                <div className="flex items-center justify-between">

                                    <span className="font-medium text-slate-300">
                                        Overall Forensic Score
                                    </span>


                                    <span className="text-2xl font-bold text-white">

                                        {forensicScore.toFixed(4)}

                                    </span>

                                </div>


                                <div className="mt-4 h-3 w-full overflow-hidden rounded-full bg-slate-800">

                                    <div

                                        className="h-full rounded-full bg-blue-500 transition-all"

                                        style={{
                                            width: `${Math.min(
                                                forensicScore * 100,
                                                100
                                            )}%`
                                        }}

                                    />

                                </div>

                            </div>


                            {/* ==========================================
                                FORENSIC SIGNALS
                            ========================================== */}

                            <div className="mt-8">

                                <h4 className="text-lg font-semibold text-white">
                                    Forensic Signals
                                </h4>


                                <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">

                                    {/* ELA */}

                                    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">

                                        <p className="text-sm text-slate-400">
                                            ELA Score
                                        </p>


                                        <p className="mt-2 text-2xl font-bold text-white">

                                            {Number(
                                                signals.ela_score || 0
                                            ).toFixed(4)}

                                        </p>

                                    </div>


                                    {/* EDGE */}

                                    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">

                                        <p className="text-sm text-slate-400">
                                            Edge Density
                                        </p>


                                        <p className="mt-2 text-2xl font-bold text-white">

                                            {Number(
                                                signals.edge_density || 0
                                            ).toFixed(4)}

                                        </p>

                                    </div>


                                    {/* WAVELET */}

                                    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">

                                        <p className="text-sm text-slate-400">
                                            Wavelet Score
                                        </p>


                                        <p className="mt-2 text-2xl font-bold text-white">

                                            {Number(
                                                signals.wavelet_score || 0
                                            ).toFixed(4)}

                                        </p>

                                    </div>


                                    {/* COPY MOVE */}

                                    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">

                                        <p className="text-sm text-slate-400">
                                            Copy-Move Score
                                        </p>


                                        <p className="mt-2 text-2xl font-bold text-white">

                                            {Number(
                                                signals.copy_move_score || 0
                                            ).toFixed(4)}

                                        </p>

                                    </div>

                                </div>

                            </div>


                            {/* ==========================================
                                COPY MOVE DETAILS
                            ========================================== */}

                            <div className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-5">

                                <h4 className="font-semibold text-white">
                                    Copy-Move Detection
                                </h4>


                                <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">

                                    <div>

                                        <p className="text-sm text-slate-400">
                                            Detection Status
                                        </p>


                                        <p
                                            className={
                                                signals.copy_move_detected
                                                    ? "mt-1 font-semibold text-red-400"
                                                    : "mt-1 font-semibold text-green-400"
                                            }
                                        >

                                            {
                                                signals.copy_move_detected
                                                    ? "Potential Duplicate Region Detected"
                                                    : "No Duplicate Region Detected"
                                            }

                                        </p>

                                    </div>


                                    <div>

                                        <p className="text-sm text-slate-400">
                                            Matched Points
                                        </p>


                                        <p className="mt-1 font-semibold text-white">

                                            {
                                                signals.matched_points || 0
                                            }

                                        </p>

                                    </div>


                                    <div>

                                        <p className="text-sm text-slate-400">
                                            RANSAC Inliers
                                        </p>


                                        <p className="mt-1 font-semibold text-white">

                                            {
                                                signals.ransac_inliers || 0
                                            }

                                        </p>

                                    </div>

                                </div>

                            </div>


                            {/* ==========================================
                                FORENSIC VISUALIZATIONS
                            ========================================== */}

                            <div className="mt-8">

                                <h4 className="text-lg font-semibold text-white">
                                    Forensic Visualizations
                                </h4>


                                <p className="mt-2 text-sm text-slate-400">
                                    Visual forensic artifacts generated during analysis.
                                </p>


                                <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">


                                    {/* ELA */}

                                    <ArtifactCard

                                        title="Error Level Analysis"

                                        description="Compression anomaly detection"

                                        artifactUrl={
                                            elaUrl
                                        }

                                    />


                                    {/* EDGES */}

                                    <ArtifactCard

                                        title="Edge Detection"

                                        description="Structural boundary analysis"

                                        artifactUrl={
                                            edgesUrl
                                        }

                                    />


                                    {/* WAVELET */}

                                    <ArtifactCard

                                        title="Wavelet Analysis"

                                        description="High-frequency artifact detection"

                                        artifactUrl={
                                            waveletUrl
                                        }

                                    />


                                    {/* COPY MOVE */}

                                    <ArtifactCard

                                        title="Copy-Move Detection"

                                        description="Duplicate region detection"

                                        artifactUrl={
                                            copyMoveUrl
                                        }

                                    />

                                </div>

                            </div>

                        </div>

                    );

                }
            )}

        </div>

    );

}


export default ImageForensics;