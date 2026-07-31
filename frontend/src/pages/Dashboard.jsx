import { Link, useNavigate } from "react-router-dom";

function Dashboard() {

  const navigate = useNavigate();

  return (

    <div className="min-h-screen bg-slate-950 text-white">

      {/* ================================= */}
      {/* Navbar */}
      {/* ================================= */}

      <nav className="border-b border-slate-800 px-8 py-5">

        <div className="flex items-center justify-between">

          <div>

            <h1 className="text-2xl font-bold">
              AI-FORGE
            </h1>

            <p className="text-sm text-slate-400">
              Multimodal Fraud Intelligence Platform
            </p>

          </div>


          <div className="text-sm text-green-400">

            ● System Online

          </div>

        </div>

      </nav>


      {/* ================================= */}
      {/* Dashboard */}
      {/* ================================= */}

      <main className="mx-auto max-w-7xl px-8 py-12">


        {/* ================================= */}
        {/* Header */}
        {/* ================================= */}

        <div className="mb-10">

          <h2 className="text-4xl font-bold">

            Investigation Dashboard

          </h2>

          <p className="mt-3 text-slate-400">

            Analyze digital evidence using AI-powered
            fraud detection and forensic analysis.

          </p>

        </div>


        {/* ================================= */}
        {/* Statistics */}
        {/* ================================= */}

        <div className="grid gap-6 md:grid-cols-3">


          {/* Total Investigations */}

          <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">

            <p className="text-sm text-slate-400">

              Total Investigations

            </p>

            <p className="mt-3 text-3xl font-bold">

              0

            </p>

          </div>


          {/* High Risk Cases */}

          <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">

            <p className="text-sm text-slate-400">

              High Risk Cases

            </p>

            <p className="mt-3 text-3xl font-bold text-red-400">

              0

            </p>

          </div>


          {/* Evidence Analyzed */}

          <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">

            <p className="text-sm text-slate-400">

              Evidence Analyzed

            </p>

            <p className="mt-3 text-3xl font-bold text-blue-400">

              0

            </p>

          </div>


        </div>


        {/* ================================= */}
        {/* New Investigation */}
        {/* ================================= */}

        <div className="mt-10 rounded-xl border border-slate-800 bg-slate-900 p-8">

          <h3 className="text-2xl font-bold">

            Start a New Investigation

          </h3>

          <p className="mt-2 text-slate-400">

            Upload images, videos, documents, and signatures
            for multimodal fraud analysis.

          </p>


          <Link

            to="/investigation"

            className="mt-6 inline-block rounded-lg bg-blue-600 px-6 py-3 font-semibold transition hover:bg-blue-500"

          >

            Create Investigation

          </Link>

        </div>


        {/* ================================= */}
        {/* Forensic Analysis Modules */}
        {/* ================================= */}

        <div className="mt-12">

          <div className="mb-6">

            <h3 className="text-2xl font-bold">

              Forensic Analysis Modules

            </h3>

            <p className="mt-2 text-slate-400">

              Select an AI-powered forensic capability
              to analyze digital evidence.

            </p>

          </div>


          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">


            {/* ================================= */}
            {/* Image Forensics */}
            {/* ================================= */}

            <button

              onClick={() =>
                navigate("/investigation")
              }

              className="group rounded-xl border border-slate-800 bg-slate-900 p-6 text-left transition hover:-translate-y-1 hover:border-blue-500 hover:bg-slate-800"

            >

              <div className="mb-5 text-4xl">

                🖼️

              </div>


              <h4 className="text-xl font-semibold">

                Image Forensics

              </h4>


              <p className="mt-2 text-sm leading-6 text-slate-400">

                Analyze images using ELA, edge detection,
                wavelet analysis, and forensic signals.

              </p>


              <p className="mt-5 text-sm font-semibold text-blue-400">

                Analyze Image →

              </p>

            </button>


            {/* ================================= */}
            {/* Signature Verification */}
            {/* ================================= */}

            <button

              onClick={() =>
                navigate("/signature")
              }

              className="group rounded-xl border border-slate-800 bg-slate-900 p-6 text-left transition hover:-translate-y-1 hover:border-blue-500 hover:bg-slate-800"

            >

              <div className="mb-5 text-4xl">

                ✍️

              </div>


              <h4 className="text-xl font-semibold">

                Signature Verification

              </h4>


              <p className="mt-2 text-sm leading-6 text-slate-400">

                Compare handwritten signatures using
                a Siamese neural network to detect
                potential forgeries.

              </p>


              <p className="mt-5 text-sm font-semibold text-blue-400">

                Verify Signature →

              </p>

            </button>


            {/* ================================= */}
            {/* Document Forensics */}
            {/* ================================= */}

            <button

              onClick={() =>
                navigate("/investigation")
              }

              className="group rounded-xl border border-slate-800 bg-slate-900 p-6 text-left transition hover:-translate-y-1 hover:border-blue-500 hover:bg-slate-800"

            >

              <div className="mb-5 text-4xl">

                📄

              </div>


              <h4 className="text-xl font-semibold">

                Document Forensics

              </h4>


              <p className="mt-2 text-sm leading-6 text-slate-400">

                Examine documents using OCR,
                compression analysis, and forensic
                document inspection.

              </p>


              <p className="mt-5 text-sm font-semibold text-blue-400">

                Analyze Document →

              </p>

            </button>


            {/* ================================= */}
            {/* Copy-Move Detection */}
            {/* ================================= */}

            <button

              onClick={() =>
                navigate("/copy-move")
              }

              className="group rounded-xl border border-slate-800 bg-slate-900 p-6 text-left transition hover:-translate-y-1 hover:border-blue-500 hover:bg-slate-800"

            >

              <div className="mb-5 text-4xl">

                🔍

              </div>


              <h4 className="text-xl font-semibold">

                Copy-Move Detection

              </h4>


              <p className="mt-2 text-sm leading-6 text-slate-400">

                Detect duplicated or copied regions
                inside images using advanced
                image forensic techniques.

              </p>


              <p className="mt-5 text-sm font-semibold text-blue-400">

                Detect Forgery →

              </p>

            </button>


            {/* ================================= */}
            {/* Video Analysis */}
            {/* ================================= */}

            <button

              onClick={() =>
                navigate("/investigation")
              }

              className="group rounded-xl border border-slate-800 bg-slate-900 p-6 text-left transition hover:-translate-y-1 hover:border-blue-500 hover:bg-slate-800"

            >

              <div className="mb-5 text-4xl">

                🎥

              </div>


              <h4 className="text-xl font-semibold">

                Video Analysis

              </h4>


              <p className="mt-2 text-sm leading-6 text-slate-400">

                Extract video frames and analyze
                visual evidence for potential
                manipulation or AI-generated content.

              </p>


              <p className="mt-5 text-sm font-semibold text-blue-400">

                Analyze Video →

              </p>

            </button>


            {/* ================================= */}
            {/* AI Jury System */}
            {/* ================================= */}

            <button

              onClick={() =>
                navigate("/investigation")
              }

              className="group rounded-xl border border-slate-800 bg-slate-900 p-6 text-left transition hover:-translate-y-1 hover:border-blue-500 hover:bg-slate-800"

            >

              <div className="mb-5 text-4xl">

                🤖

              </div>


              <h4 className="text-xl font-semibold">

                AI Jury System

              </h4>


              <p className="mt-2 text-sm leading-6 text-slate-400">

                Combine forensic evidence with
                multiple AI critics to produce
                a more reliable fraud verdict.

              </p>


              <p className="mt-5 text-sm font-semibold text-blue-400">

                Run AI Jury →

              </p>

            </button>


          </div>

        </div>


      </main>

    </div>

  );

}

export default Dashboard;