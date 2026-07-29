import { Link } from "react-router-dom";

function Dashboard() {
  return (
    <div className="min-h-screen bg-slate-950 text-white">

      {/* Navbar */}
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


      {/* Dashboard */}
      <main className="mx-auto max-w-7xl px-8 py-12">

        <div className="mb-10">

          <h2 className="text-4xl font-bold">
            Investigation Dashboard
          </h2>

          <p className="mt-3 text-slate-400">
            Analyze digital evidence using AI-powered
            fraud detection and forensic analysis.
          </p>

        </div>


        {/* Statistics */}
        <div className="grid gap-6 md:grid-cols-3">

          <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">

            <p className="text-sm text-slate-400">
              Total Investigations
            </p>

            <p className="mt-3 text-3xl font-bold">
              0
            </p>

          </div>


          <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">

            <p className="text-sm text-slate-400">
              High Risk Cases
            </p>

            <p className="mt-3 text-3xl font-bold text-red-400">
              0
            </p>

          </div>


          <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">

            <p className="text-sm text-slate-400">
              Evidence Analyzed
            </p>

            <p className="mt-3 text-3xl font-bold text-blue-400">
              0
            </p>

          </div>

        </div>


        {/* New Investigation */}
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

      </main>

    </div>
  );
}

export default Dashboard;