import { Link, useNavigate } from "react-router-dom";
import {
  Image,
  PenTool,
  FileText,
  Copy,
  Video,
  Bot,
  ArrowRight,
  Activity,
  AlertTriangle,
  FolderSearch,
} from "lucide-react";

import AppLayout from "../components/layout/AppLayout";
import StatCard from "../components/ui/StatCard";
import GlassCard from "../components/ui/GlassCard";

function Dashboard() {

  const navigate = useNavigate();


  /* ========================================= */
  /* Forensic Module Cards                     */
  /* ========================================= */

  const modules = [

    {
      id: "image",
      title: "Image Forensics",
      description:
        "Analyze images using ELA, edge detection, wavelet analysis, and forensic signals.",
      icon: Image,
      gradient: "blue",
      path: "/investigation",
      action: "Analyze Image",
    },

    {
      id: "signature",
      title: "Signature Verification",
      description:
        "Compare handwritten signatures using a Siamese neural network to detect forgeries.",
      icon: PenTool,
      gradient: "purple",
      path: "/signature",
      action: "Verify Signature",
    },

    {
      id: "document",
      title: "Document Forensics",
      description:
        "Examine documents using OCR, compression analysis, and forensic document inspection.",
      icon: FileText,
      gradient: "green",
      path: "/investigation",
      action: "Analyze Document",
    },

    {
      id: "copy-move",
      title: "Copy-Move Detection",
      description:
        "Detect duplicated or copied regions inside images using advanced forensic techniques.",
      icon: Copy,
      gradient: "cyan",
      path: "/copy-move",
      action: "Detect Forgery",
    },

    {
      id: "video",
      title: "Video Analysis",
      description:
        "Extract video frames and analyze visual evidence for manipulation or AI-generated content.",
      icon: Video,
      gradient: "red",
      path: "/investigation",
      action: "Analyze Video",
    },

    {
      id: "ai-jury",
      title: "AI Jury System",
      description:
        "Combine forensic evidence with multiple AI critics to produce a reliable fraud verdict.",
      icon: Bot,
      gradient: "purple",
      path: "/investigation",
      action: "Run AI Jury",
    },

  ];


  return (

    <AppLayout
      title="Investigation Dashboard"
      subtitle="Multimodal Fraud Intelligence Platform"
    >

      {/* ================================= */}
      {/* Page Header                       */}
      {/* ================================= */}

      <div className="mb-8">

        <h2 className="text-3xl font-bold tracking-tight text-white md:text-4xl">

          Investigation Dashboard

        </h2>

        <p className="mt-3 max-w-2xl text-slate-400">

          Analyze digital evidence using AI-powered
          fraud detection and forensic analysis.

        </p>

      </div>


      {/* ================================= */}
      {/* Statistics Row                    */}
      {/* ================================= */}

      <div className="mb-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">

        <StatCard
          label="Total Investigations"
          value="0"
          icon={FolderSearch}
          gradient="blue"
          trend="Ready for new cases"
        />

        <StatCard
          label="High Risk Cases"
          value="0"
          icon={AlertTriangle}
          gradient="red"
          trend="No active alerts"
        />

        <StatCard
          label="Evidence Analyzed"
          value="0"
          icon={Activity}
          gradient="cyan"
          trend="All pipelines operational"
        />

      </div>


      {/* ================================= */}
      {/* Start New Investigation CTA       */}
      {/* ================================= */}

      <GlassCard gradient="blue" className="mb-10">

        <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">

          <div>

            <h3 className="text-2xl font-bold text-white">

              Start a New Investigation

            </h3>

            <p className="mt-2 max-w-xl text-slate-400">

              Upload images, videos, documents, and signatures
              for multimodal fraud analysis.

            </p>

          </div>


          <Link
            to="/investigation"
            className="group inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-blue-600 to-cyan-600 px-6 py-3 font-semibold text-white shadow-lg shadow-blue-500/25 transition hover:from-blue-500 hover:to-cyan-500 hover:shadow-blue-500/40"
          >

            Create Investigation

            <ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" />

          </Link>

        </div>

      </GlassCard>


      {/* ================================= */}
      {/* Forensic Analysis Modules         */}
      {/* ================================= */}

      <div>

        <div className="mb-6">

          <h3 className="text-2xl font-bold text-white">

            Forensic Analysis Modules

          </h3>

          <p className="mt-2 text-slate-400">

            Select an AI-powered forensic capability
            to analyze digital evidence.

          </p>

        </div>


        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">

          {modules.map((mod) => {

            const Icon = mod.icon;

            return (

              <GlassCard
                key={mod.id}
                gradient={mod.gradient}
                onClick={() => navigate(mod.path)}
                className="group"
              >

                <div className="mb-4 inline-flex rounded-lg bg-white/5 p-3 transition group-hover:bg-white/10">

                  <Icon
                    className="h-6 w-6 text-slate-300"
                    aria-hidden="true"
                  />

                </div>


                <h4 className="text-lg font-semibold text-white">

                  {mod.title}

                </h4>


                <p className="mt-2 text-sm leading-relaxed text-slate-400">

                  {mod.description}

                </p>


                <p className="mt-4 flex items-center gap-1 text-sm font-semibold text-blue-400 transition group-hover:gap-2">

                  {mod.action}

                  <ArrowRight className="h-3.5 w-3.5" />

                </p>

              </GlassCard>

            );

          })}

        </div>

      </div>

    </AppLayout>

  );

}

export default Dashboard;
