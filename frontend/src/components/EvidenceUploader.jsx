import {
  uploadEvidence,
  analyzeImage
} from "../services/api";


function EvidenceUploader({

  files,
  setFiles,

  processing,
  setProcessing,

  setResults,

  error,
  setError

}) {


  // ==========================================
  // FILE SELECTION
  // ==========================================

  const handleFileChange = (event) => {

    const selectedFiles =
      Array.from(
        event.target.files || []
      );


    // No files selected
    if (
      selectedFiles.length === 0
    ) {

      return;

    }


    setFiles(
      selectedFiles
    );


    setResults(
      []
    );


    setError(
      ""
    );

  };


  // ==========================================
  // IMAGE ANALYSIS
  // ==========================================

  const handleAnalyze = async () => {

    // ----------------------------------------
    // Validate files
    // ----------------------------------------

    if (
      !files ||
      files.length === 0
    ) {

      setError(
        "Please select at least one image."
      );

      return;

    }


    // ----------------------------------------
    // Start Processing
    // ----------------------------------------

    setProcessing(
      true
    );


    setError(
      ""
    );


    setResults(
      []
    );


    try {

      const analysisResults = [];


      // ======================================
      // Process Each File
      // ======================================

      for (
        const file of files
      ) {


        try {

          // ----------------------------------
          // Upload Evidence
          // ----------------------------------

          const uploadResult =
            await uploadEvidence(
              file
            );


          // ----------------------------------
          // Get Evidence ID
          // ----------------------------------

          const evidenceId =
            uploadResult.evidence_id;


          // ----------------------------------
          // Validate Evidence ID
          // ----------------------------------

          if (!evidenceId) {

            throw new Error(
              "Backend did not return an evidence ID."
            );

          }


          // ----------------------------------
          // Check File Type
          // ----------------------------------

          if (
            uploadResult.file_type !==
            "image"
          ) {

            analysisResults.push({

              filename:
                file.name,

              evidenceId:
                evidenceId,

              status:
                "unsupported",

              message:
                "Forensic image analysis is currently available only for images."

            });


            continue;

          }


          // ----------------------------------
          // Run Unified Image Analysis
          //
          // This runs:
          //
          // ELA
          // Edge Detection
          // Wavelet Analysis
          // Copy-Move Detection
          // ----------------------------------

          const analysisResult =
            await analyzeImage(
              evidenceId
            );


          // ----------------------------------
          // Save Successful Result
          // ----------------------------------

          analysisResults.push({

            filename:
              file.name,

            evidenceId:
              evidenceId,

            status:
              "completed",

            analysis:
              analysisResult.analysis

          });


        } catch (fileError) {

          // ----------------------------------
          // Handle Individual File Error
          // ----------------------------------

          console.error(

            `Analysis failed for ${file.name}:`,

            fileError

          );


          analysisResults.push({

            filename:
              file.name,

            status:
              "failed",

            message:
              fileError.message ||
              "Analysis failed for this image."

          });

        }

      }


      // ======================================
      // Update Results
      // ======================================

      setResults(
        analysisResults
      );


      // ======================================
      // Check if All Failed
      // ======================================

      const failedResults =
        analysisResults.filter(

          (item) =>
            item.status ===
            "failed"

        );


      if (

        failedResults.length ===
        analysisResults.length

      ) {

        setError(
          "Image analysis failed for all selected files."
        );

      }


    } catch (error) {

      // ======================================
      // Global Error
      // ======================================

      console.error(
        "Image analysis error:",
        error
      );


      setError(

        error.message ||

        "Analysis failed."

      );


    } finally {

      // ======================================
      // Stop Processing
      // ======================================

      setProcessing(
        false
      );

    }

  };


  // ==========================================
  // COMPONENT UI
  // ==========================================

  return (

    <>

      {/* ================================= */}
      {/* UPLOAD SECTION */}
      {/* ================================= */}

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

            accept="image/jpeg,image/jpg,image/png,image/webp"

            onChange={
              handleFileChange
            }

            className="hidden"

          />


        </label>


      </div>


      {/* ================================= */}
      {/* SELECTED FILES */}
      {/* ================================= */}

      {files &&
        files.length > 0 && (

          <div className="mt-8">


            <h3 className="text-xl font-bold">

              Selected Evidence

            </h3>


            <div className="mt-4 space-y-3">


              {files.map(

                (file, index) => (

                  <div

                    key={`${file.name}-${index}`}

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


            {/* ================================= */}
            {/* ANALYZE BUTTON */}
            {/* ================================= */}


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


      {/* ================================= */}
      {/* ERROR */}
      {/* ================================= */}


      {error && (

        <div className="mt-8 rounded-lg border border-red-800 bg-red-950 p-5 text-red-300">


          🔴 {error}


        </div>

      )}


    </>

  );

}


export default EvidenceUploader;