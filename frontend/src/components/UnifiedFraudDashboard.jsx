function UnifiedFraudDashboard({

    imageResults = [],

    documentResult = null,

    signatureResult = null,

    videoResult = null

}) {

    return (

        <div className="mt-10 space-y-8">

            {/* ================================= */}
            {/* HEADER */}
            {/* ================================= */}

            <div>

                <h2 className="text-3xl font-bold">

                    Unified Fraud Risk Dashboard

                </h2>

                <p className="mt-2 text-slate-400">

                    Consolidated forensic analysis
                    across all evidence pipelines.

                </p>

            </div>


            {/* ================================= */}
            {/* ANALYSIS STATUS */}
            {/* ================================= */}

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">


                {/* IMAGE */}

                <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">

                    <p className="text-sm text-slate-400">

                        Image Forensics

                    </p>

                    <p className="mt-3 text-xl font-bold">

                        {imageResults.length > 0

                            ? "Analysis Available"

                            : "No Analysis"

                        }

                    </p>

                </div>


                {/* DOCUMENT */}

                <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">

                    <p className="text-sm text-slate-400">

                        Document Forensics

                    </p>

                    <p className="mt-3 text-xl font-bold">

                        {documentResult

                            ? "Analysis Available"

                            : "No Analysis"

                        }

                    </p>

                </div>


                {/* SIGNATURE */}

                <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">

                    <p className="text-sm text-slate-400">

                        Signature Verification

                    </p>

                    <p className="mt-3 text-xl font-bold">

                        {signatureResult

                            ? signatureResult.verdict

                            : "No Analysis"

                        }

                    </p>

                </div>


                {/* VIDEO */}

                <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">

                    <p className="text-sm text-slate-400">

                        Video Analytics

                    </p>

                    <p className="mt-3 text-xl font-bold">

                        {videoResult

                            ? "Analysis Available"

                            : "No Analysis"

                        }

                    </p>

                </div>

            </div>


            {/* ================================= */}
            {/* SIGNATURE RESULT */}
            {/* ================================= */}

            {signatureResult && (

                <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">

                    <h3 className="text-xl font-bold">

                        Signature Verification

                    </h3>


                    <div className="mt-6 grid gap-6 md:grid-cols-3">


                        <div>

                            <p className="text-sm text-slate-400">

                                Verdict

                            </p>

                            <p className="mt-2 text-2xl font-bold">

                                {signatureResult.verdict}

                            </p>

                        </div>


                        <div>

                            <p className="text-sm text-slate-400">

                                Similarity

                            </p>

                            <p className="mt-2 text-2xl font-bold">

                                {(

                                    signatureResult.similarity *

                                    100

                                ).toFixed(2)}%

                            </p>

                        </div>


                        <div>

                            <p className="text-sm text-slate-400">

                                Confidence

                            </p>

                            <p className="mt-2 text-2xl font-bold">

                                {(

                                    signatureResult.confidence *

                                    100

                                ).toFixed(2)}%

                            </p>

                        </div>

                    </div>

                </div>

            )}


            {/* ================================= */}
            {/* VIDEO RESULT */}
            {/* ================================= */}

            {videoResult && (

                <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">

                    <h3 className="text-xl font-bold">

                        Video Analytics

                    </h3>


                    <div className="mt-6 grid gap-6 md:grid-cols-3">


                        <div>

                            <p className="text-sm text-slate-400">

                                Frames Analyzed

                            </p>

                            <p className="mt-2 text-2xl font-bold">

                                {videoResult.summary
                                    ?.frames_analyzed ?? 0}

                            </p>

                        </div>


                        <div>

                            <p className="text-sm text-slate-400">

                                Average Brightness

                            </p>

                            <p className="mt-2 text-2xl font-bold">

                                {videoResult.summary
                                    ?.average_brightness ?? 0}

                            </p>

                        </div>


                        <div>

                            <p className="text-sm text-slate-400">

                                Average Blur Score

                            </p>

                            <p className="mt-2 text-2xl font-bold">

                                {videoResult.summary
                                    ?.average_blur_score ?? 0}

                            </p>

                        </div>

                    </div>

                </div>

            )}


            {/* ================================= */}
            {/* IMAGE RESULTS */}
            {/* ================================= */}

            {imageResults.length > 0 && (

                <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">

                    <h3 className="text-xl font-bold">

                        Image Forensics

                    </h3>


                    <div className="mt-6 space-y-4">

                        {imageResults.map(

                            (item, index) => (

                                <div

                                    key={index}

                                    className="rounded-lg border border-slate-700 bg-slate-950 p-5"

                                >

                                    <p className="font-semibold">

                                        {item.filename}

                                    </p>


                                    <p className="mt-2 text-slate-400">

                                        Verdict:{" "}

                                        {item.analysis
                                            ?.verdict || "N/A"}

                                    </p>


                                    <p className="mt-1 text-slate-400">

                                        Forensic Score:{" "}

                                        {item.analysis
                                            ?.forensic_score ?? "N/A"}

                                    </p>

                                </div>

                            )

                        )}

                    </div>

                </div>

            )}


            {/* ================================= */}
            {/* DOCUMENT RESULTS */}
            {/* ================================= */}

            {documentResult && (

                <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">

                    <h3 className="text-xl font-bold">

                        Document Forensics

                    </h3>


                    <div className="mt-6">

                        <p className="text-slate-400">

                            Document Type:

                        </p>

                        <p className="mt-1 font-semibold">

                            {documentResult.document_type
                                || "PDF"}

                        </p>


                        <p className="mt-4 text-slate-400">

                            Pages Analyzed:

                        </p>

                        <p className="mt-1 font-semibold">

                            {documentResult.page_count
                                || 0}

                        </p>

                    </div>

                </div>

            )}


        </div>

    );

}


export default UnifiedFraudDashboard;