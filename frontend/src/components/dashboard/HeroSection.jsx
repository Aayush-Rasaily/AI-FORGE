import { motion } from "framer-motion";
import { Sparkles, ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { useAnimatedCounter } from "../../hooks/useAnimatedCounter";

function HeroSection() {
  const cases = useAnimatedCounter(128);
  const accuracy = useAnimatedCounter(97);

  return (
    <motion.section
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className="relative mb-10 overflow-hidden rounded-3xl border border-[#1F2937] bg-gradient-to-br from-blue-600/10 via-[#111827] to-cyan-600/5 p-8 md:p-12"
    >
      <div className="pointer-events-none absolute -right-20 -top-20 h-64 w-64 rounded-full bg-blue-500/10 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-16 -left-16 h-48 w-48 rounded-full bg-cyan-500/10 blur-3xl" />

      <div className="relative z-10 flex flex-col gap-8 lg:flex-row lg:items-center lg:justify-between">
        <div className="max-w-2xl">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-blue-500/30 bg-blue-500/10 px-4 py-1.5 text-xs font-medium text-blue-300">
            <Sparkles className="h-3.5 w-3.5" />
            AI-Powered Digital Forensics Platform
          </div>

          <h1 className="text-3xl font-bold tracking-tight text-white md:text-5xl lg:text-6xl">
            Detect Fraud with
            <span className="bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
              {" "}Precision Intelligence
            </span>
          </h1>

          <p className="mt-4 text-base leading-relaxed text-slate-400 md:text-lg">
            Multimodal evidence analysis across images, documents, signatures,
            and video — powered by ensemble AI agents and forensic science.
          </p>

          <div className="mt-8 flex flex-wrap gap-4">
            <Link
              to="/investigation"
              className="group inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-600 px-6 py-3 font-semibold text-white shadow-lg shadow-blue-500/25 transition hover:shadow-blue-500/40"
            >
              Start Investigation
              <ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" />
            </Link>
            <div className="flex items-center gap-6 text-sm">
              <div>
                <p className="text-2xl font-bold text-white">{cases}+</p>
                <p className="text-xs text-slate-500">Cases Analyzed</p>
              </div>
              <div className="h-8 w-px bg-[#1F2937]" />
              <div>
                <p className="text-2xl font-bold text-white">{accuracy}%</p>
                <p className="text-xs text-slate-500">Detection Accuracy</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </motion.section>
  );
}

export default HeroSection;
