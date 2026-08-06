import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Image, PenTool, FileText, Copy, Video, Bot, ArrowRight,
  Activity, AlertTriangle, FolderSearch, Zap, Clock,
} from "lucide-react";

import AppLayout from "../components/layout/AppLayout";
import StatCard from "../components/ui/StatCard";
import GlassCard from "../components/ui/GlassCard";
import HeroSection from "../components/dashboard/HeroSection";
import FraudTrendChart from "../components/dashboard/FraudTrendChart";
import AnalysisPieChart from "../components/dashboard/AnalysisPieChart";
import ModelHealthPanel from "../components/dashboard/ModelHealthPanel";
import { SkeletonStat, SkeletonChart } from "../components/ui/SkeletonLoader";
import { useAnimatedCounter } from "../hooks/useAnimatedCounter";
import { getDashboardStats } from "../services/api";
import { useBackend } from "../context/BackendConnectivity";

function Dashboard() {
  const navigate = useNavigate();
  const { online, evidence, health, refreshEvidence } = useBackend();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getDashboardStats()
      .then((s) => {
        if (!cancelled) setStats(s);
      })
      .catch(() => {
        if (!cancelled) setStats(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    refreshEvidence();
    return () => {
      cancelled = true;
    };
  }, [evidence.length, refreshEvidence]);

  const liveAnalyses = useAnimatedCounter(stats?.pending_assignments || 0);

  const modules = [
    { id: "image", title: "Image Forensics", description: "ELA, edge detection, wavelet analysis, and forensic signals.", icon: Image, gradient: "blue", path: "/investigation", action: "Analyze Image" },
    { id: "signature", title: "Signature Verification", description: "Siamese neural network signature authentication.", icon: PenTool, gradient: "purple", path: "/signature", action: "Verify Signature" },
    { id: "document", title: "Document Forensics", description: "OCR, compression analysis, and document inspection.", icon: FileText, gradient: "green", path: "/investigation", action: "Analyze Document" },
    { id: "copy-move", title: "Copy-Move Detection", description: "Detect duplicated regions using advanced forensics.", icon: Copy, gradient: "cyan", path: "/copy-move", action: "Detect Forgery" },
    { id: "video", title: "Video Analysis", description: "Frame extraction and manipulation detection.", icon: Video, gradient: "red", path: "/investigation", action: "Analyze Video" },
    { id: "ai-jury", title: "AI Jury System", description: "Multi-agent ensemble verdict with explainable reasoning.", icon: Bot, gradient: "purple", path: "/investigation", action: "Run AI Jury" },
  ];

  const recentCases = stats?.recent_cases || [];

  return (
    <AppLayout title="Command Center" subtitle="AI-FORGE Fraud Intelligence Platform">
      <HeroSection />

      {/* Live Stats */}
      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {loading ? (
          <>
            <SkeletonStat /><SkeletonStat /><SkeletonStat /><SkeletonStat />
          </>
        ) : (
          <>
            <StatCard
              label="Total Investigations"
              value={String(stats?.total_investigations ?? 0)}
              icon={FolderSearch}
              gradient="blue"
              trend={`${stats?.open_investigations ?? 0} open`}
            />
            <StatCard
              label="High Risk Cases"
              value={String(stats?.high_risk_cases ?? 0)}
              icon={AlertTriangle}
              gradient="red"
              trend="Require review"
            />
            <StatCard
              label="Evidence Analyzed"
              value={String(Math.max(stats?.total_evidence ?? 0, evidence.length))}
              icon={Activity}
              gradient="cyan"
              trend={`${stats?.total_analyses ?? 0} analyses`}
            />
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass-card rounded-xl p-6 gradient-card-purple"
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm text-slate-400">Active Investigators</p>
                  <p className="mt-2 text-3xl font-bold text-white">{liveAnalyses}</p>
                  <p className="mt-1 flex items-center gap-1 text-xs text-emerald-400">
                    <Zap className="h-3 w-3" />
                    {health?.status === "healthy" ? "All systems operational" : "Checking…"}
                  </p>
                </div>
                <div className="rounded-lg bg-white/5 p-2.5">
                  <Activity className="h-5 w-5 text-purple-400 animate-pulse" />
                </div>
              </div>
            </motion.div>
          </>
        )}
      </div>

      {/* Charts Row */}
      <div className="mb-8 grid gap-6 lg:grid-cols-2">
        {loading ? <><SkeletonChart /><SkeletonChart /></> : <><FraudTrendChart /><AnalysisPieChart /></>}
      </div>

      {/* Model Health + Recent */}
      <div className="mb-10 grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <ModelHealthPanel health={health} />
        </div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="glass-card rounded-xl p-5"
        >
          <h3 className="text-lg font-semibold text-white">Recent Investigations</h3>
          <div className="mt-4 space-y-3">
            {recentCases.length === 0 ? (
              <p className="text-sm text-slate-500">No investigations yet</p>
            ) : (
              recentCases.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => navigate("/cases")}
                  className="flex w-full items-center justify-between rounded-lg border border-[#1F2937] bg-[#0B1120]/60 p-3 text-left transition hover:border-cyan-500/30"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-white">{c.title}</p>
                    <p className="text-xs text-slate-500">{c.status} · {c.id}</p>
                  </div>
                  <Clock className="h-3.5 w-3.5 shrink-0 text-slate-600" />
                </button>
              ))
            )}
          </div>
          <Link
            to="/cases"
            className="mt-4 flex items-center gap-1 text-xs font-medium text-cyan-400 hover:text-cyan-300"
          >
            View all cases <ArrowRight className="h-3 w-3" />
          </Link>
        </motion.div>
      </div>

      {/* Module Grid */}
      <div className="mb-10">
        <h3 className="mb-5 text-lg font-semibold text-white">Forensic Modules</h3>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {modules.map((mod, i) => (
            <motion.div
              key={mod.id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06 }}
            >
              <Link to={mod.path}>
                <GlassCard className="group p-5 transition hover:border-cyan-500/30">
                  <div className="flex items-start gap-4">
                    <div className={`rounded-xl bg-gradient-to-br p-2.5 gradient-card-${mod.gradient}`}>
                      <mod.icon className="h-5 w-5 text-white" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <h4 className="font-semibold text-white group-hover:text-cyan-400 transition">{mod.title}</h4>
                      <p className="mt-1 text-xs text-slate-500 line-clamp-2">{mod.description}</p>
                      <span className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-cyan-500">
                        {mod.action} <ArrowRight className="h-3 w-3" />
                      </span>
                    </div>
                  </div>
                </GlassCard>
              </Link>
            </motion.div>
          ))}
        </div>
      </div>

      {/* CTA */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card rounded-2xl p-8 text-center gradient-card-blue"
      >
        <h3 className="text-2xl font-bold text-white">Start a New Investigation</h3>
        <p className="mt-2 text-sm text-slate-400">Upload evidence, run forensic pipelines, and synthesize AI jury verdicts.</p>
        <Link
          to="/cases"
          className="mt-5 inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 px-6 py-3 text-sm font-semibold text-white transition hover:from-cyan-500 hover:to-blue-500"
        >
          Create Case <ArrowRight className="h-4 w-4" />
        </Link>
      </motion.div>
    </AppLayout>
  );
}

export default Dashboard;
