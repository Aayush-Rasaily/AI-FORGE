import { useState } from "react";

import {
    getArtifactUrl
} from "../services/api";


function DocumentForensics({
    result
}) {


    const [
        selectedPage,
        setSelectedPage
    ] = useState(0);



    // ==========================================
    // SAFETY CHECK
    // ==========================================

    if (!result) {

        return (

            <div className="mt-8 rounded-xl border border-slate-800 bg-slate-900 p-8">

                <h3 className="text-xl font-bold text-white">

                    Document Forensics

                </h3>


                <p className="mt-3 text-slate-400">

                    No document forensic result available.

                </p>


                <p className="mt-2 text-sm text-slate-500">

                    Upload a PDF document and click
                    "Analyze Document" to begin forensic analysis.

                </p>

            </div>

        );

    }



    // ==========================================
    // DOCUMENT DATA
    // ==========================================

    const pages =

        Array.isArray(result.pages)

            ? result.pages

            : [];



    const pageCount =

        result.page_count ||

        pages.length ||

        0;



    // ==========================================
    // ACTIVE PAGE
    // ==========================================

    const activePage =

        pages[selectedPage] ||

        pages[0];



    // ==========================================
    // NO PAGES
    // ==========================================

    if (
        pages.length === 0
    ) {

        return (

            <div className="mt-8 rounded-xl border border-slate-800 bg-slate-900 p-8">

                <h3 className="text-xl font-bold text-white">

                    Document Forensics

                </h3>


                <p className="mt-3 text-slate-400">

                    Document analysis completed, but no pages
                    were returned by the backend.

                </p>

            </div>

        );

    }



    return (

        <div className="mt-10 space-y-8">


            {/* ====================================== */}
            {/* HEADER */}
            {/* ====================================== */}

            <div>

                <h2 className="text-2xl font-bold text-white">

                    Document Forensics Dashboard

                </h2>


                <p className="mt-2 text-sm text-slate-400">

                    Page-by-page forensic analysis and OCR results.

                </p>

            </div>



            {/* ====================================== */}
            {/* DOCUMENT SUMMARY */}
            {/* ====================================== */}

            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">


                <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">

                    <p className="text-sm text-slate-400">

                        Document Type

                    </p>


                    <p className="mt-2 text-xl font-bold text-white">

                        {result.document_type || "PDF"}

                    </p>

                </div>



                <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">

                    <p className="text-sm text-slate-400">

                        Total Pages

                    </p>


                    <p className="mt-2 text-xl font-bold text-white">

                        {pageCount}

                    </p>

                </div>



                <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">

                    <p className="text-sm text-slate-400">

                        Analysis Status

                    </p>


                    <p className="mt-2 text-xl font-bold text-green-400">

                        Completed

                    </p>

                </div>

            </div>



            {/* ====================================== */}
            {/* PAGE SELECTOR */}
            {/* ====================================== */}

            <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">

                <h3 className="text-lg font-semibold text-white">

                    Document Pages

                </h3>


                <div className="mt-5 flex flex-wrap gap-3">

                    {pages.map(

                        (page, index) => (

                            <button

                                key={index}

                                onClick={() =>

                                    setSelectedPage(
                                        index
                                    )

                                }

                                className={

                                    selectedPage === index

                                        ? "rounded-lg bg-blue-600 px-5 py-3 text-sm font-semibold text-white"

                                        : "rounded-lg bg-slate-800 px-5 py-3 text-sm font-semibold text-slate-300 hover:bg-slate-700"

                                }

                            >

                                Page{" "}

                                {page.page_number ||

                                    index + 1

                                }

                            </button>

                        )

                    )}

                </div>

            </div>



            {/* ====================================== */}
            {/* ACTIVE PAGE */}
            {/* ====================================== */}

            {activePage && (

                <div className="space-y-8">


                    {/* ================================== */}
                    {/* PAGE HEADER */}
                    {/* ================================== */}

                    <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">

                        <h3 className="text-xl font-bold text-white">

                            Page{" "}

                            {activePage.page_number ||

                                selectedPage + 1

                            }

                        </h3>


                        <p className="mt-2 text-sm text-slate-400">

                            Detailed forensic and OCR analysis for this page.

                        </p>

                    </div>



                  {/* ================================== */}
                  {/* PAGE IMAGE */}
                  {/* ================================== */}

                  {activePage.image && (

                      <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">

                          <h3 className="text-lg font-semibold text-white">
                              Page Image
                          </h3>

                          <div className="mt-5 overflow-hidden rounded-lg bg-black">

                            <img
                            src={getArtifactUrl(activePage.image)}
                            alt={`Page ${activePage.page_number || selectedPage + 1}`}
                            className="max-h-[700px] w-full object-contain"
                            onLoad={() => {
                                console.log(
                                    "✅ Loaded:",
                                    getArtifactUrl(activePage.image)
                                );
                            }}
                            onError={() => {
                                console.error(
                                    "❌ Failed:",
                                    getArtifactUrl(activePage.image)
                                );
                            }}
                        />

                          </div>

                      </div>

                  )}


                    {/* ================================== */}
                    {/* OCR TEXT */}
                    {/* ================================== */}

                    <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">

                        <h3 className="text-lg font-semibold text-white">

                            OCR Extracted Text

                        </h3>


                        <div className="mt-5 max-h-[500px] overflow-y-auto rounded-lg border border-slate-800 bg-slate-950 p-5">

                            <pre className="whitespace-pre-wrap text-sm leading-7 text-slate-300">

                                {activePage.ocr?.full_text ||

                                    activePage.ocr?.text ||

                                    activePage.ocr?.extracted_text ||

                                    (

                                        typeof activePage.ocr === "string"

                                            ? activePage.ocr

                                            : "No OCR text available."

                                    )

                                }

                            </pre>

                        </div>

                    </div>



                    {/* ================================== */}
                    {/* OCR DETECTIONS */}
                    {/* ================================== */}

                    {activePage.ocr?.detections &&

                        activePage.ocr.detections.length > 0 && (

                            <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">

                                <h3 className="text-lg font-semibold text-white">

                                    OCR Detections

                                </h3>


                                <div className="mt-5 space-y-3">

                                    {activePage.ocr.detections.map(

                                        (detection, index) => (

                                            <div

                                                key={index}

                                                className="rounded-lg bg-slate-950 p-4"

                                            >

                                                <p className="text-sm text-slate-300">

                                                    {detection.text}

                                                </p>


                                                <p className="mt-2 text-xs text-slate-500">

                                                    Confidence:{" "}

                                                    {typeof detection.confidence === "number"

                                                        ? (

                                                            detection.confidence *

                                                            100

                                                        ).toFixed(2) + "%"

                                                        : "N/A"

                                                    }

                                                </p>

                                            </div>

                                        )

                                    )}

                                </div>

                            </div>

                        )}



                    {/* ================================== */}
                    {/* FORENSIC RESULTS */}
                    {/* ================================== */}

                    {activePage.forensics && (

                        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">

                            <h3 className="text-lg font-semibold text-white">

                                Page Forensic Analysis

                            </h3>



                            {/* SIGNALS */}

                            {activePage.forensics.signals && (

                                <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3">


                                    <SignalCard

                                        title="ELA Score"

                                        value={

                                            activePage.forensics.signals.ela_score

                                        }

                                    />


                                    <SignalCard

                                        title="Edge Density"

                                        value={

                                            activePage.forensics.signals.edge_density

                                        }

                                    />


                                    <SignalCard

                                        title="Wavelet Score"

                                        value={

                                            activePage.forensics.signals.wavelet_score

                                        }

                                    />

                                </div>

                            )}



                            {/* ARTIFACTS */}

                            {activePage.forensics.artifacts && (

                                <div className="mt-8">

                                    <h4 className="text-md font-semibold text-white">

                                        Forensic Artifacts

                                    </h4>


                                    <div className="mt-5 grid grid-cols-1 gap-6 lg:grid-cols-3">


                                        <ForensicArtifact

                                            title="Error Level Analysis"

                                            description="Compression anomaly detection"

                                            artifact={

                                                activePage.forensics.artifacts.ela

                                            }

                                        />


                                        <ForensicArtifact

                                            title="Edge Detection"

                                            description="Structural boundary analysis"

                                            artifact={

                                                activePage.forensics.artifacts.edges

                                            }

                                        />


                                        <ForensicArtifact

                                            title="Wavelet Analysis"

                                            description="High-frequency artifact detection"

                                            artifact={

                                                activePage.forensics.artifacts.wavelet

                                            }

                                        />

                                    </div>

                                </div>

                            )}

                        </div>

                    )}

                </div>

            )}

        </div>

    );

}



// ==========================================
// SIGNAL CARD
// ==========================================

function SignalCard({

    title,

    value

}) {

    return (

        <div className="rounded-lg bg-slate-950 p-5">

            <p className="text-sm text-slate-400">

                {title}

            </p>


            <p className="mt-2 text-2xl font-bold text-white">

                {value ?? "N/A"}

            </p>

        </div>

    );

}



// ==========================================
// FORENSIC ARTIFACT
// ==========================================

function ForensicArtifact({

    title,

    description,

    artifact

}) {


    const artifactUrl =

        getArtifactUrl(
            artifact
        );


    return (

        <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-950">


            <div className="p-5">

                <h4 className="font-semibold text-white">

                    {title}

                </h4>


                <p className="mt-1 text-sm text-slate-400">

                    {description}

                </p>

            </div>



            <div className="flex min-h-[220px] items-center justify-center bg-black">


                {artifactUrl ? (

                    <img

                        src={
                            artifactUrl
                        }

                        alt={
                            title
                        }

                        className="max-h-[350px] w-full object-contain"

                        onError={() => {

                            console.error(

                                `Failed to load artifact: ${artifactUrl}`

                            );

                        }}

                    />

                ) : (

                    <p className="text-sm text-slate-500">

                        Artifact unavailable

                    </p>

                )}

            </div>

        </div>

    );

}


export default DocumentForensics;