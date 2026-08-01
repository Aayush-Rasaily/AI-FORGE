function AnalysisSelector({

  analysisType,

  setAnalysisType

}) {

  return (

    <div className="mt-8 rounded-xl border border-slate-800 bg-slate-900 p-6">


      {/* ================================= */}
      {/* HEADER */}
      {/* ================================= */}

      <h3 className="text-xl font-semibold">

        Select Analysis Type

      </h3>


      <p className="mt-2 text-sm text-slate-400">

        Choose the forensic analysis pipeline
        or view the unified fraud risk assessment.

      </p>


      {/* ================================= */}
      {/* ANALYSIS OPTIONS */}
      {/* ================================= */}

      <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-3">


        {/* ================================= */}
        {/* IMAGE FORENSICS */}
        {/* ================================= */}

        <button

          onClick={() =>

            setAnalysisType("image")

          }

          className={`rounded-lg border p-5 text-left transition ${

            analysisType === "image"

              ? "border-blue-500 bg-blue-950"

              : "border-slate-700 bg-slate-950 hover:border-slate-500"

          }`}

        >

          <p className="text-lg font-semibold">

            Image Forensics

          </p>


          <p className="mt-2 text-sm text-slate-400">

            ELA, Edge, Wavelet and
            Copy-Move Detection

          </p>

        </button>


        {/* ================================= */}
        {/* SIGNATURE VERIFICATION */}
        {/* ================================= */}

        <button

          onClick={() =>

            setAnalysisType("signature")

          }

          className={`rounded-lg border p-5 text-left transition ${

            analysisType === "signature"

              ? "border-purple-500 bg-purple-950"

              : "border-slate-700 bg-slate-950 hover:border-slate-500"

          }`}

        >

          <p className="text-lg font-semibold">

            Signature Verification

          </p>


          <p className="mt-2 text-sm text-slate-400">

            Siamese Neural Network
            Signature Authentication

          </p>

        </button>


        {/* ================================= */}
        {/* DOCUMENT FORENSICS */}
        {/* ================================= */}

        <button

          onClick={() =>

            setAnalysisType("document")

          }

          className={`rounded-lg border p-5 text-left transition ${

            analysisType === "document"

              ? "border-green-500 bg-green-950"

              : "border-slate-700 bg-slate-950 hover:border-slate-500"

          }`}

        >

          <p className="text-lg font-semibold">

            Document Forensics

          </p>


          <p className="mt-2 text-sm text-slate-400">

            Document authenticity and
            forgery detection

          </p>

        </button>


        {/* ================================= */}
        {/* VIDEO ANALYTICS */}
        {/* ================================= */}

        <button

          onClick={() =>

            setAnalysisType("video")

          }

          className={`rounded-lg border p-5 text-left transition ${

            analysisType === "video"

              ? "border-red-500 bg-red-950"

              : "border-slate-700 bg-slate-950 hover:border-slate-500"

          }`}

        >

          <p className="text-lg font-semibold">

            Video Analytics

          </p>


          <p className="mt-2 text-sm text-slate-400">

            Video metadata, key-frame
            and forensic signal analysis

          </p>

        </button>


        {/* ================================= */}
        {/* UNIFIED DASHBOARD */}
        {/* ================================= */}

        <button

          onClick={() =>

            setAnalysisType("dashboard")

          }

          className={`rounded-lg border p-5 text-left transition ${

            analysisType === "dashboard"

              ? "border-yellow-500 bg-yellow-950"

              : "border-slate-700 bg-slate-950 hover:border-slate-500"

          }`}

        >

          <p className="text-lg font-semibold">

            Fraud Risk Dashboard

          </p>


          <p className="mt-2 text-sm text-slate-400">

            Unified forensic risk assessment
            across all evidence

          </p>

        </button>


      </div>

    </div>

  );

}


export default AnalysisSelector;