import {
  uploadEvidence,
  analyzeImage,
  analyzeDocument
} from "../services/api";


function EvidenceUploader({

  analysisType,

  files,
  setFiles,

  processing,
  setProcessing,

  setResults,

  error,
  setError

}) {


  // ==========================================
  // FILE CONFIGURATION
  // ==========================================

  const isDocument =
    analysisType === "document";


  const acceptedTypes = isDocument

    ? ".pdf,.doc,.docx"

    : ".jpg,.jpeg,.png,.webp";


  const supportedText = isDocument

    ? "Supported: PDF, DOC, DOCX"

    : "Supported: JPG, JPEG, PNG, WEBP";


  // ==========================================
  // FILE SELECTION
  // ==========================================

  const handleFileChange = (event) => {

    const selectedFiles = Array.from(
      event.target.files || []
    );


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
  // ANALYZE EVIDENCE
  // ==========================================

  const handleAnalyze = async () => {

    if (
      !files ||
      files.length === 0
    ) {

      setError(

        isDocument

          ? "Please select at least one document."

          : "Please select at least one image."

      );

      return;

    }


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
      // PROCESS EACH FILE
      // ======================================

      for (
        const file of files
      ) {


        try {

          console.log(
            `[UPLOAD] Uploading: ${file.name}`
          );


          // ----------------------------------
          // UPLOAD
          // ----------------------------------

          const uploadResult =
            await uploadEvidence(
              file
            );


          console.log(
            "[UPLOAD RESULT]",
            uploadResult
          );


          // ----------------------------------
          // EVIDENCE ID
          // ----------------------------------

          const evidenceId =
            uploadResult.evidence_id;


          if (!evidenceId) {

            throw new Error(
              "Backend did not return an evidence ID."
            );

          }


          // ----------------------------------
          // FILE TYPE
          // ----------------------------------

          const fileType =
            uploadResult.file_type;


          console.log(
            `[ANALYSIS] ${file.name} -> ${fileType}`
          );


          // ==================================
          // IMAGE FORENSICS
          // ==================================

          if (
            analysisType === "image"
          ) {


            if (
              fileType !== "image"
            ) {

              throw new Error(

                "Please upload a valid image file for Image Forensics."

              );

            }


            console.log(

              `[IMAGE] Starting analysis for ${evidenceId}`

            );


            const analysisResult =
              await analyzeImage(
                evidenceId
              );


            console.log(

              "[IMAGE ANALYSIS RESULT]",

              analysisResult

            );


            analysisResults.push({

              filename:
                file.name,

              evidenceId:
                evidenceId,

              fileType:
                "image",

              status:
                "completed",

              analysis:
                analysisResult.analysis

            });


            continue;

          }


          // ==================================
          // DOCUMENT FORENSICS
          // ==================================

          if (
            analysisType === "document"
          ) {


            if (

              fileType !== "document" &&

              fileType !== "pdf"

            ) {

              throw new Error(

                "Please upload a PDF, DOC, or DOCX file for Document Forensics."

              );

            }


            console.log(

              `[DOCUMENT] Starting analysis for ${evidenceId}`

            );


            const documentResult =
              await analyzeDocument(
                evidenceId
              );


            console.log(

              "[DOCUMENT ANALYSIS RESULT]",

              documentResult

            );


            // --------------------------------
            // IMPORTANT
            // Store complete document analysis
            // --------------------------------

            analysisResults.push({

              filename:
                file.name,

              evidenceId:
                evidenceId,

              fileType:
                "document",

              status:
                "completed",

              documentAnalysis:
                documentResult.analysis

            });


            continue;

          }


          // ==================================
          // UNKNOWN ANALYSIS TYPE
          // ==================================

          throw new Error(

            "Unknown analysis type."

          );


        } catch (fileError) {


          console.error(

            `Analysis failed for ${file.name}:`,

            fileError

          );


          analysisResults.push({

            filename:
              file.name,

            evidenceId:
              null,

            fileType:
              analysisType,

            status:
              "failed",

            message:

              fileError?.message ||

              "Analysis failed for this file."

          });

        }

      }


      // ======================================
      // SAVE RESULTS
      // ======================================

      console.log(

        "[FINAL ANALYSIS RESULTS]",

        analysisResults

      );


      setResults(

        analysisResults

      );


      // ======================================
      // CHECK ALL FAILED
      // ======================================

      const failedResults =

        analysisResults.filter(

          (item) =>

            item.status ===

            "failed"

        );


      if (

        failedResults.length > 0 &&

        failedResults.length ===

        analysisResults.length

      ) {

        setError(

          isDocument

            ? "Document analysis failed for all selected files."

            : "Image analysis failed for all selected files."

        );

      }


    } catch (error) {


      console.error(

        "Evidence analysis error:",

        error

      );


      setError(

        error?.message ||

        "Evidence analysis failed."

      );


    } finally {


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

          {isDocument

            ? "Upload Document Evidence"

            : "Upload Image Evidence"

          }

        </h3>


        <p className="mt-3 text-sm text-slate-400">

          {supportedText}

        </p>


        <label className="mt-6 inline-block cursor-pointer rounded-lg bg-blue-600 px-6 py-3 font-semibold transition hover:bg-blue-500">


          {isDocument

            ? "Select Documents"

            : "Select Images"

          }


          <input

            type="file"

            multiple

            accept={
              acceptedTypes
            }

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

                : isDocument

                  ? "Analyze Document"

                  : "Analyze Images"

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