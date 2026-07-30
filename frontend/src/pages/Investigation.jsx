import { useState } from "react";

import {
  uploadEvidence,
  analyzeImage,
  getArtifactUrl,
} from "../services/api";



function Investigation() {

  const [files, setFiles] = useState([]);

  const [processing, setProcessing] =
    useState(false);

  const [results, setResults] =
    useState([]);

  const [error, setError] =
    useState("");


  // -----------------------------
  // Select Files
  // -----------------------------

  const handleFileChange = (event) => {

    const selectedFiles =
      Array.from(
        event.target.files
      );


    setFiles(
      selectedFiles
    );

    setResults([]);

    setError("");

  };


  // -----------------------------
  // Upload + Analyze
  // -----------------------------

  const handleAnalyze = async () => {

    if (files.length === 0) {

      setError(
        "Please select at least one image."
      );

      return;

    }


    setProcessing(true);

    setError("");

    setResults([]);


    try {

      const analysisResults = [];


      for (
        const file of files
      ) {

        // -------------------------
        // Step 1: Upload
        // -------------------------

        const uploadResult =
          await uploadEvidence(
            file
          );


        // -------------------------
        // Step 2: Check file type
        // -------------------------

        if (
          uploadResult.file_type !==
          "image"
        ) {

          analysisResults.push({

            filename:
              file.name,

            status:
              "unsupported",

            message:
              "Forensic image analysis is currently available only for images."

          });

          continue;

        }


        // -------------------------
        // Step 3: Analyze
        // -------------------------

        const analysisResult =
          await analyzeImage(
            uploadResult.evidence_id
          );


        analysisResults.push({

          filename:
            file.name,

          evidenceId:
            uploadResult.evidence_id,

          status:
            "completed",

          analysis:
            analysisResult.analysis

        });

      }


      setResults(
        analysisResults
      );


    } catch (error) {

      console.error(
        error
      );


      setError(
        error.message ||
        "Analysis failed."
      );


    } finally {

      setProcessing(
        false
      );

    }

  };


  return (

    <div className="min-h-screen bg-slate-950 text-white">


      {/* ========================= */}
      {/* HEADER */}
      {/* ========================= */}

      <nav className="border-b border-slate-800 px-8 py-5">

        <h1 className="text-2xl font-bold">
          AI-FORGE
        </h1>

        <p className="text-sm text-slate-400">
          Multimodal Fraud Investigation
        </p>

      </nav>


      {/* ========================= */}
      {/* MAIN */}
      {/* ========================= */}

      <main className="mx-auto max-w-6xl px-8 py-12">


        <h2 className="text-4xl font-bold">

          Evidence Investigation

        </h2>


        <p className="mt-3 text-slate-400">

          Upload digital evidence and run
          AI-powered forensic analysis.

        </p>


        {/* ========================= */}
        {/* UPLOAD */}
        {/* ========================= */}

        <div className="mt-10 rounded-xl border-2 border-dashed border-slate-700 bg-slate-900 p-12 text-center">


          <h3 className="text-xl font-semibold">

            Upload Evidence

          </h3>


          <p className="mt-3 text-sm text-slate-400">

            Currently supported:
            JPG, JPEG, PNG, WEBP

          </p>


          <label className="mt-6 inline-block cursor-pointer rounded-lg bg-blue-600 px-6 py-3 font-semibold transition hover:bg-blue-500">

            Select Images


            <input

              type="file"

              multiple

              accept="image/*"

              onChange={
                handleFileChange
              }

              className="hidden"

            />

          </label>

        </div>


        {/* ========================= */}
        {/* SELECTED FILES */}
        {/* ========================= */}

        {files.length > 0 && (

          <div className="mt-8">


            <h3 className="text-xl font-bold">

              Selected Evidence

            </h3>


            <div className="mt-4 space-y-3">


              {files.map(
                (file, index) => (

                  <div

                    key={index}

                    className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900 p-4"

                  >


                    <div>

                      <p className="font-medium">

                        {file.name}

                      </p>


                      <p className="text-sm text-slate-400">

                        {(
                          file.size /
                          1024 /
                          1024
                        ).toFixed(2)}

                        {" "}MB

                      </p>

                    </div>


                    <span className="text-sm text-green-400">

                      Ready

                    </span>


                  </div>

                )
              )}

            </div>


            {/* ========================= */}
            {/* ANALYZE BUTTON */}
            {/* ========================= */}

            <button

              onClick={
                handleAnalyze
              }

              disabled={
                processing
              }

              className="mt-8 rounded-lg bg-green-600 px-8 py-3 font-semibold transition hover:bg-green-500 disabled:cursor-not-allowed disabled:opacity-50"

            >

              {processing

                ? "Analyzing Evidence..."

                : "Analyze Evidence"

              }

            </button>


          </div>

        )}


        {/* ========================= */}
        {/* ERROR */}
        {/* ========================= */}

        {error && (

          <div className="mt-8 rounded-lg border border-red-800 bg-red-950 p-5 text-red-300">

            🔴 {error}

          </div>

        )}


        {/* ========================= */}
        {/* RESULTS */}
        {/* ========================= */}

        {results.length > 0 && (

          <div className="mt-12">


            <h2 className="text-3xl font-bold">

              Forensic Analysis Report

            </h2>


            <div className="mt-6 space-y-8">


              {results.map(
                (result, index) => (

                  <div

                    key={index}

                    className="rounded-xl border border-slate-800 bg-slate-900 p-8"

                  >


                    {/* File Name */}

                    <div className="flex items-center justify-between">

                      <h3 className="text-xl font-bold">

                        {result.filename}

                      </h3>


                      {result.status ===
                        "completed" && (

                        <span className="rounded-full bg-green-900 px-4 py-2 text-sm text-green-300">

                          Analysis Complete

                        </span>

                      )}

                    </div>


                    {result.status ===
                      "completed" && (

                      

  <>

    {/* ========================= */}
    {/* ORIGINAL EVIDENCE */}
    {/* ========================= */}

    <div className="mt-8">

      <h3 className="text-xl font-bold">
        Original Evidence
      </h3>

      <div className="mt-4 overflow-hidden rounded-xl border border-slate-800 bg-black">

        <img
          src={URL.createObjectURL(
            files.find(
              (file) =>
                file.name === result.filename
            )
          )}

          alt="Original Evidence"

          className="max-h-[500px] w-full object-contain"

        />

      </div>

    </div>


    {/* ========================= */}
    {/* VERDICT */}
    {/* ========================= */}

    <div className="mt-8">

      <p className="text-sm text-slate-400">
        Forensic Assessment
      </p>

      <p className="mt-2 text-3xl font-bold">
        {result.analysis.verdict}
      </p>

    </div>


                        {/* Score */}

                        <div className="mt-8">


                          <p className="text-sm text-slate-400">

                            Forensic Anomaly Score

                          </p>


                          <div className="mt-3 h-4 w-full overflow-hidden rounded-full bg-slate-800">


                            <div

                              className="h-full bg-blue-500"

                              style={{
                                width: `${Math.min(
                                  result.analysis.forensic_score * 100,
                                  100
                                )}%`
                              }}

                            />


                          </div>


                          <p className="mt-2 text-right text-sm text-slate-400">

                            {(
                              result.analysis.forensic_score *
                              100
                            ).toFixed(1)}%

                          </p>

                        </div>


                        {/* Signals */}

                        <div className="mt-8 grid gap-4 md:grid-cols-4">


                          <div className="rounded-lg bg-slate-800 p-5">


                            <p className="text-sm text-slate-400">

                              ELA Score

                            </p>


                            <p className="mt-2 text-2xl font-bold">

                              {(
                                result.analysis.signals.ela_score *
                                100
                              ).toFixed(1)}%

                            </p>

                          </div>


                          <div className="rounded-lg bg-slate-800 p-5">


                            <p className="text-sm text-slate-400">

                              Edge Density

                            </p>


                            <p className="mt-2 text-2xl font-bold">

                              {(
                                result.analysis.signals.edge_density *
                                100
                              ).toFixed(1)}%

                            </p>

                          </div>


                          <div className="rounded-lg bg-slate-800 p-5">


                            <p className="text-sm text-slate-400">

                              Wavelet Score

                            </p>


                            <p className="mt-2 text-2xl font-bold">

                              {(
                                result.analysis.signals.wavelet_score *
                                100
                              ).toFixed(1)}%

                            </p>

                          </div>


                          <div className="rounded-lg bg-slate-800 p-5">


                            <p className="text-sm text-slate-400">

                              Copy-Move

                            </p>


                            <p className="mt-2 text-2xl font-bold">

                              {result.analysis.signals.copy_move_detected

                                ? "Detected"

                                : "Not Detected"

                              }

                            </p>

                          </div>


                        </div>


{/* VISUAL FORENSIC EVIDENCE */}
{/* =============================== */}

<div className="mt-12">

  <h3 className="text-2xl font-bold">
    Visual Forensic Evidence
  </h3>

  <p className="mt-2 text-sm text-slate-400">
    Forensic visualizations generated
    during evidence analysis.
  </p>


  <div className="mt-6 grid gap-6 md:grid-cols-3">


    {/* ========================= */}
    {/* ELA */}
    {/* ========================= */}

    <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-950">

      <div className="border-b border-slate-800 p-5">

        <h4 className="font-semibold">
          Error Level Analysis
        </h4>

        <p className="mt-1 text-xs text-slate-500">
          Compression anomaly detection
        </p>

      </div>


      <div className="flex h-72 items-center justify-center bg-black">

        <img

          src={getArtifactUrl(
            result.analysis.artifacts.ela
          )}

          alt="ELA Forensic Analysis"

          className="h-full w-full object-contain"

        />

      </div>

    </div>


    {/* ========================= */}
    {/* EDGE */}
    {/* ========================= */}

    <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-950">

      <div className="border-b border-slate-800 p-5">

        <h4 className="font-semibold">
          Edge Detection
        </h4>

        <p className="mt-1 text-xs text-slate-500">
          Structural boundary analysis
        </p>

      </div>


      <div className="flex h-72 items-center justify-center bg-black">

        <img

          src={getArtifactUrl(
            result.analysis.artifacts.edges
          )}

          alt="Edge Forensic Analysis"

          className="h-full w-full object-contain"

        />

      </div>

    </div>


    {/* ========================= */}
    {/* WAVELET */}
    {/* ========================= */}

    <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-950">

      <div className="border-b border-slate-800 p-5">

        <h4 className="font-semibold">
          Wavelet Analysis
        </h4>

        <p className="mt-1 text-xs text-slate-500">
          High-frequency artifact detection
        </p>

      </div>


      <div className="flex h-72 items-center justify-center bg-black">

        <img

          src={getArtifactUrl(
            result.analysis.artifacts.wavelet
          )}

          alt="Wavelet Forensic Analysis"

          className="h-full w-full object-contain"

        />

      </div>

    </div>


  </div>

</div>

                      </>

                    )}


                    {result.status ===
                      "unsupported" && (

                      <p className="mt-6 text-yellow-400">

                        ⚠️ {result.message}

                      </p>

                    )}

                  </div>

                )
              )}

            </div>

          </div>

        )}

      </main>

    </div>

  );

}


export default Investigation;