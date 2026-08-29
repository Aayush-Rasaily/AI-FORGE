import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  BarChart3,
  Gauge,
  Loader2,
  Play,
  RefreshCw,
  Shield,
  TrendingUp,
  Zap,
} from "lucide-react";
import {
  getEvaluationDashboard,
  runBenchmark,
} from "../../services/api";
import { useBackend } from "../../context/BackendConnectivity";

function pct(v) {
  const n = Number(v);
  if (Number.isNaN(n)) return "—";
  return `${(n * 100).toFixed(1)}%`;
}

function DetectorWeightBar({ name, weight }) {
  const pctVal = Math.round(Number(weight) * 100);
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="font-medium uppercase tracking-wide text-slate-400">{name}</span>
        <span className="text-cyan-400">{Number(weight).toFixed(2)}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-[#1F2937]">
        <div
          className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-blue-500"
          style={{ width: `${pctVal}%` }}
        />
      </div>
    </div>
  );
}

function BenchmarkLearningDashboard() {
  const { online } = useBackend();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!online) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await getEvaluationDashboard();
      setData(res);
    } catch (err) {
      setError(err.message || "Failed to load evaluation dashboard");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [online]);

  useEffect(() => {
    load();
  }, [load]);

  const handleRunBenchmark = async () => {
    setRunning(true);
    setError("");
    try {
      await runBenchmark();
      await load();
    } catch (err) {
      setError(err.message || "Benchmark run failed");
    } finally {
      setRunning(false);
    }
  };

  const weights = data?.detector_weights || {};
  const topWeights = Object.entries(weights)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);

  const monthly = data?.monthly_performance || [];
  const maxMonthTotal = Math.max(...monthly.map((m) => m.total), 1);

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-[#1F2937] bg-[#111827]/80 p-6 backdrop-blur-xl"
    >
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-white">Benchmark & Continuous Learning</h3>
          <p className="text-xs text-slate-500">
            Detector evaluation metrics · fusion weighting only (no model retrain)
          </p>
          {data?.benchmark_last_run && (
            <p className="mt-1 text-[11px] text-slate-600">
              Last benchmark: {new Date(data.benchmark_last_run).toLocaleString()}
            </p>
          )}
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={load}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-lg border border-[#1F2937] bg-[#0B1120]/60 px-3 py-1.5 text-xs text-slate-300 hover:border-cyan-500/30"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <button
            type="button"
            onClick={handleRunBenchmark}
            disabled={running || !online}
            className="flex items-center gap-1.5 rounded-lg bg-cyan-600/20 px-3 py-1.5 text-xs font-medium text-cyan-400 hover:bg-cyan-600/30 disabled:opacity-50"
          >
            {running ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Play className="h-3.5 w-3.5" />
            )}
            Run Benchmark
          </button>
        </div>
      </div>

      {error && (
        <p className="mb-4 text-xs text-red-400">{error}</p>
      )}

      {loading && !data ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-cyan-400" />
        </div>
      ) : (
        <>
          <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              {
                label: "System Accuracy",
                value: pct(data?.overall_system_accuracy),
                icon: Shield,
                color: "text-emerald-400",
              },
              {
                label: "Avg Confidence",
                value: data?.average_confidence != null ? `${data.average_confidence}%` : "—",
                icon: Gauge,
                color: "text-cyan-400",
              },
              {
                label: "Most Reliable",
                value: data?.most_reliable_detector?.detector?.toUpperCase() || "—",
                sub: data?.most_reliable_detector?.reliability
                  ? Number(data.most_reliable_detector.reliability).toFixed(2)
                  : null,
                icon: TrendingUp,
                color: "text-blue-400",
              },
              {
                label: "Weakest Detector",
                value: data?.weakest_detector?.detector?.toUpperCase() || "—",
                sub: data?.weakest_detector?.reliability
                  ? Number(data.weakest_detector.reliability).toFixed(2)
                  : null,
                icon: Zap,
                color: "text-amber-400",
              },
            ].map((card) => {
              const Icon = card.icon;
              return (
                <div
                  key={card.label}
                  className="rounded-xl border border-[#1F2937] bg-[#0B1120]/60 p-4"
                >
                  <div className="flex items-center gap-2">
                    <Icon className={`h-4 w-4 ${card.color}`} />
                    <p className="text-xs text-slate-500">{card.label}</p>
                  </div>
                  <p className="mt-2 text-lg font-bold text-white">{card.value}</p>
                  {card.sub && (
                    <p className="text-xs text-slate-500">reliability {card.sub}</p>
                  )}
                </div>
              );
            })}
          </div>

          <div className="mb-6 grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-[#1F2937] bg-[#0B1120]/40 p-4">
              <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">
                <BarChart3 className="h-4 w-4 text-cyan-400" />
                Classification Metrics
              </h4>
              <div className="grid grid-cols-2 gap-2 text-xs">
                {[
                  ["Precision", data?.precision],
                  ["Recall", data?.recall],
                  ["F1 Score", data?.f1_score],
                  ["ROC AUC", data?.roc_auc],
                  ["False Positive Rate", data?.false_positive_rate],
                  ["False Negative Rate", data?.false_negative_rate],
                ].map(([label, val]) => (
                  <div key={label} className="flex justify-between rounded-lg bg-[#111827]/60 px-3 py-2">
                    <span className="text-slate-500">{label}</span>
                    <span className="font-medium text-white">{pct(val)}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-[#1F2937] bg-[#0B1120]/40 p-4">
              <h4 className="mb-3 text-sm font-semibold text-white">Monthly Performance</h4>
              {monthly.length === 0 ? (
                <p className="text-xs text-slate-500">No investigator feedback yet.</p>
              ) : (
                <div className="flex h-32 items-end gap-2">
                  {monthly.map((m) => (
                    <div key={m.month} className="flex flex-1 flex-col items-center gap-1">
                      <div
                        className="w-full rounded-t bg-gradient-to-t from-cyan-600/40 to-cyan-400/80"
                        style={{
                          height: `${Math.max(8, (m.total / maxMonthTotal) * 100)}%`,
                        }}
                        title={`${m.month}: ${pct(m.accuracy)} accuracy`}
                      />
                      <span className="text-[9px] text-slate-600">{m.month.slice(5)}</span>
                    </div>
                  ))}
                </div>
              )}
              <p className="mt-2 text-[11px] text-slate-500">
                {data?.total_feedback ?? 0} total feedback submissions
              </p>
            </div>
          </div>

          <div className="rounded-xl border border-[#1F2937] bg-[#0B1120]/40 p-4">
            <h4 className="mb-3 text-sm font-semibold text-white">Detector Reliability Weights</h4>
            <div className="grid gap-3 sm:grid-cols-2">
              {topWeights.length === 0 ? (
                <p className="text-xs text-slate-500">Run a benchmark to populate weights.</p>
              ) : (
                topWeights.map(([name, w]) => (
                  <DetectorWeightBar key={name} name={name} weight={w} />
                ))
              )}
            </div>
          </div>
        </>
      )}
    </motion.div>
  );
}

export default BenchmarkLearningDashboard;
