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
    // ANALYSIS RESULTS
    //
    // This contains results from:
    //
    // Image:
    // results[i].analysis
    //
    // Document:
    // results[i].documentAnalysis
    // ==========================================

    const [
        results,
        setResults
    ] = useState([]);


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

        // Clear previous files
        setFiles([]);

        // Clear previous results
        setResults([]);

        // Clear previous errors
        setError("");

    };


    // ==========================================
    // GET DOCUMENT RESULT
    // ==========================================

    const documentResult =

        results.find(

            (item) =>

                item.fileType === "document" &&

                item.status === "completed"

        );


    // ==========================================
    // DOCUMENT FORENSICS
    // ==========================================

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

            />


            <DocumentForensics

                result={
                    documentResult?.documentAnalysis
                }

            />

        </>

    )}

    // ==========================================
    // GET IMAGE RESULTS
    // ==========================================

    const imageResults =

        results.filter(

            (item) =>

                item.fileType === "image" &&

                item.status === "completed"

        );


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

            <main className="mx-auto max-w-6xl px-8 py-12">


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
                {/* UPLOADER */}
                {/*================================= */ }
                {(

                    analysisType === "image" ||

                    analysisType === "document"

                ) && (

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

                )}



                {/* ================================= */}
                {/* IMAGE FORENSICS */}
                {/* ================================= */}

                {analysisType === "image" && (

                    <ImageForensics

                        files={
                            files
                        }

                        results={
                            imageResults
                        }

                    />

                )}



                {/* ================================= */}
                {/* SIGNATURE VERIFICATION */}
                {/* ================================= */}

                {analysisType === "signature" && (

                    <SignatureVerification />

                )}



                {/* ================================= */}
                {/* DOCUMENT FORENSICS */}
                {/* ================================= */}

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

                    />


                    <DocumentForensics

                      result={
                        results.find(
                          (item) =>
                            item.fileType === "document" &&
                            item.status === "completed"
                        )?.documentAnalysis
                      }

                    />

                  </>

                )}

            </main>

        </div>

    );

}


export default Investigation;