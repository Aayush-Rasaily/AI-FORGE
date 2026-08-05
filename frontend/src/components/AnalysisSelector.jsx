import {
  Image,
  PenTool,
  FileText,
  Video,
  LayoutDashboard,
} from "lucide-react";

import GlassCard from "./ui/GlassCard";

function AnalysisSelector({
  analysisType,
  setAnalysisType,
}) {

  const options = [

    {
      id: "image",
      label: "Image Forensics",
      description:
        "ELA, Edge, Wavelet and Copy-Move Detection",
      icon: Image,
      activeColor:
        "border-blue-500 bg-blue-500/10 shadow-blue-500/10",
      iconColor: "text-blue-400",
    },

    {
      id: "signature",
      label: "Signature Verification",
      description:
        "Siamese Neural Network Signature Authentication",
      icon: PenTool,
      activeColor:
        "border-purple-500 bg-purple-500/10 shadow-purple-500/10",
      iconColor: "text-purple-400",
    },

    {
      id: "document",
      label: "Document Forensics",
      description:
        "Document authenticity and forgery detection",
      icon: FileText,
      activeColor:
        "border-emerald-500 bg-emerald-500/10 shadow-emerald-500/10",
      iconColor: "text-emerald-400",
    },

    {
      id: "video",
      label: "Video Analytics",
      description:
        "Video metadata, key-frame and forensic signal analysis",
      icon: Video,
      activeColor:
        "border-red-500 bg-red-500/10 shadow-red-500/10",
      iconColor: "text-red-400",
    },

    {
      id: "dashboard",
      label: "Fraud Risk Dashboard",
      description:
        "Unified forensic risk assessment across all evidence",
      icon: LayoutDashboard,
      activeColor:
        "border-amber-500 bg-amber-500/10 shadow-amber-500/10",
      iconColor: "text-amber-400",
    },

  ];

  return (

    <GlassCard hover={false} className="mb-8">

      {/* Header */}

      <h3 className="text-xl font-semibold text-white">

        Select Analysis Type

      </h3>

      <p className="mt-2 text-sm text-slate-400">

        Choose the forensic analysis pipeline
        or view the unified fraud risk assessment.

      </p>

      {/* Cards */}

      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">

        {options.map(

          ({
            id,
            label,
            description,
            icon: Icon,
            activeColor,
            iconColor,
          }) => (

            <button

              key={id}

              onClick={() => setAnalysisType(id)}

              className={`group flex items-start gap-3 rounded-xl border p-4 text-left transition-all duration-200 ${
                analysisType === id
                  ? `${activeColor} shadow-sm`
                  : "border-slate-700/50 bg-slate-900/30 hover:border-slate-600 hover:bg-slate-800/30"
              }`}

            >

              <div

                className={`mt-0.5 rounded-lg bg-white/5 p-2 ${
                  analysisType === id
                    ? iconColor
                    : "text-slate-500"
                }`}

              >

                <Icon
                  className="h-5 w-5"
                  aria-hidden="true"
                />

              </div>

              <div>

                <p className="font-semibold text-white">

                  {label}

                </p>

                <p className="mt-1 text-xs leading-relaxed text-slate-400">

                  {description}

                </p>

              </div>

            </button>

          )

        )}

      </div>

    </GlassCard>

  );

}

export default AnalysisSelector;