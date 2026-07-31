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
  // IMAGE FORENSICS STATE
  // ==========================================

  const [
    files,
    setFiles
  ] = useState([]);


  const [
    processing,
    setProcessing
  ] = useState(false);


  const [
    results,
    setResults
  ] = useState([]);


  const [
    error,
    setError
  ] = useState("");


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
            setAnalysisType
          }

        />


        {/* ================================= */}
        {/* IMAGE FORENSICS */}
        {/* ================================= */}

        {analysisType ===
          "image" && (

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

            />


            <ImageForensics

              files={
                files
              }

              results={
                results
              }

            />

          </>

        )}


        {/* ================================= */}
        {/* SIGNATURE VERIFICATION */}
        {/* ================================= */}

        {analysisType ===
          "signature" && (

          <SignatureVerification />

        )}


        {/* ================================= */}
        {/* DOCUMENT FORENSICS */}
        {/* ================================= */}

        {analysisType ===
          "document" && (

          <DocumentForensics />

        )}

      </main>

    </div>

  );

}

export default Investigation;