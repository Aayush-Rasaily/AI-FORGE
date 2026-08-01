import { useState } from "react";

import AnalysisSelector
    from "../components/AnalysisSelector";

import EvidenceUploader
    from "../components/EvidenceUploader";

import ImageForensics
    from "../components/ImageForensics";

import SignatureVerification
    from "../components/SignatureVerification";

import DocumentForensics
    from "../components/DocumentForensics";

import VideoForensics
    from "../components/VideoForensics";

import UnifiedFraudDashboard
    from "../components/UnifiedFraudDashboard";


function Investigation() {

    // ==========================================
    // ANALYSIS TYPE
    // ==========================================

    const [
        analysisType,
        setAnalysisType
    ] = useState("image");


    // ==========================================
    // SELECTED FILES
    // ==========================================

    const [
        files,
        setFiles
    ] = useState([]);


    // ==========================================
    // PROCESSING STATE
    // ==========================================

    const [
        processing,
        setProcessing
    ] = useState(false);


    // ==========================================
    // IMAGE / DOCUMENT RESULTS
    // ==========================================

    const [
        results,
        setResults
    ] = useState([]);


    // ==========================================
    // SIGNATURE RESULT
    // ==========================================

    const [
        signatureResult,
        setSignatureResult
    ] = useState(null);


    // ==========================================
    // VIDEO RESULT
    // ==========================================

    const [
    videoResult,
    setVideoResult
    ] = useState(null);


    // ==========================================
    // ERROR
    // ==========================================

    const [
        error,
        setError
    ] = useState("");


    // ==========================================
    // HANDLE ANALYSIS TYPE CHANGE
    // ==========================================

    const handleAnalysisTypeChange = (type) => {

        setAnalysisType(type);

        // Clear temporary upload state
        setFiles([]);

        setProcessing(false);

        setError("");

    };


    // ==========================================
    // GET IMAGE RESULTS
    // ==========================================

    const imageResults =

        results.filter(

            (item) =>

                item.fileType === "image" &&

                item.status === "completed"

        );


    // ==========================================
    // GET DOCUMENT RESULT
    // ==========================================

    const documentResult =

        results.find(

            (item) =>

                (

                    item.fileType === "document" ||

                    item.fileType === "pdf"

                ) &&

                item.status === "completed"

        );


    // ==========================================
    // GET DOCUMENT ANALYSIS
    // ==========================================

    const documentAnalysis =

        documentResult?.documentAnalysis || null;


    return (

        <div className="min-h-screen bg-slate-950 text-white">


            {/* ================================= */}
            {/* HEADER */}
            {/* ================================= */}

            <nav className="border-b border-slate-800 px-8 py-5">

                <h1 className="text-2xl font-bold">

                    AI-FORGE

                </h1>


                <p className="text-sm text-slate-400">

                    Multimodal Fraud Investigation

                </p>

            </nav>


            {/* ================================= */}
            {/* MAIN */}
            {/* ================================= */}

            <main className="mx-auto max-w-7xl px-8 py-12">


                <h2 className="text-4xl font-bold">

                    Evidence Investigation

                </h2>


                <p className="mt-3 text-slate-400">

                    Upload digital evidence and run
                    AI-powered forensic analysis.

                </p>


                {/* ================================= */}
                {/* ANALYSIS SELECTOR */}
                {/* ================================= */}

                <AnalysisSelector

                    analysisType={

                        analysisType

                    }

                    setAnalysisType={

                        handleAnalysisTypeChange

                    }

                />


                {/* ================================= */}
                {/* IMAGE FORENSICS */}
                {/* ================================= */}

                {analysisType === "image" && (

                    <>

                        <EvidenceUploader

                            files={

                                files

                            }

                            setFiles={

                                setFiles

                            }

                            processing={

                                processing

                            }

                            setProcessing={

                                setProcessing

                            }

                            setResults={

                                setResults

                            }

                            error={

                                error

                            }

                            setError={

                                setError

                            }

                            analysisType={

                                analysisType

                            }

                        />


                        <ImageForensics

                            files={

                                files

                            }

                            results={

                                imageResults

                            }

                        />

                    </>

                )}


                {/* ================================= */}
                {/* SIGNATURE VERIFICATION */}
                {/* ================================= */}

                {analysisType === "signature" && (

                    <SignatureVerification

                        onResult={

                            setSignatureResult

                        }

                    />

                )}


                {/* ================================= */}
                {/* DOCUMENT FORENSICS */}
                {/* ================================= */}

                {analysisType === "document" && (

                    <>

                        <EvidenceUploader

                            files={

                                files

                            }

                            setFiles={

                                setFiles

                            }

                            processing={

                                processing

                            }

                            setProcessing={

                                setProcessing

                            }

                            setResults={

                                setResults

                            }

                            error={

                                error

                            }

                            setError={

                                setError

                            }

                            analysisType={

                                analysisType

                            }

                        />


                        <DocumentForensics

                            result={

                                documentAnalysis

                            }

                        />

                    </>

                )}


                {/* ================================= */}
                {/* VIDEO FORENSICS */}
                {/* ================================= */}

                {analysisType === "video" && (

                    <VideoForensics
                        onResult={setVideoResult}
                    />

                )}


                {/* ================================= */}
                {/* UNIFIED FRAUD DASHBOARD */}
                {/* ================================= */}

                {analysisType === "dashboard" && (

                    <UnifiedFraudDashboard

                        imageResults={

                            imageResults

                        }

                        documentResult={

                            documentAnalysis

                        }

                        signatureResult={

                            signatureResult

                        }

                        videoResult={

                            videoResult

                        }

                    />

                )}

            </main>

        </div>

    );

}


export default Investigation;