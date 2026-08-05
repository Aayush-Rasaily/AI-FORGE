import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

import GlassCard from "./ui/GlassCard";
import RiskGauge from "./ui/RiskGauge";
import StatusBadge from "./ui/StatusBadge";

/* ========================================= */
/* Compute aggregate risk from evidence      */
/* ========================================= */

function computeAggregateRisk(
  imageResults,
  documentResult,
  signatureResult,
  videoResult,
  tamperingResult
) {

  const scores = [];

  imageResults.forEach((item) => {

    const score =
      Number(item.analysis?.forensic_score) || 0;

    if (score > 0) {
      scores.push(score);
    }

  });


  if (signatureResult) {

    const sigRisk =
      (1 - (signatureResult.similarity || 0)) * 100;

    scores.push(sigRisk);

  }


  if (documentResult?.risk_score) {

    scores.push(Number(documentResult.risk_score));

  }


  if (videoResult?.summary?.risk_score) {

    scores.push(Number(videoResult.summary.risk_score));

  }
  if (tamperingResult?.tampering_percentage) {

    scores.push(
        Number(tamperingResult.tampering_percentage)
    );

    }


  if (scores.length === 0) {
    return 0;
  }


  return (
    scores.reduce((a, b) => a + b, 0) / scores.length
  );

}


function UnifiedFraudDashboard({

    imageResults = [],

    documentResult = null,

    signatureResult = null,

    videoResult = null,
    
    tamperingResult = null

}) {

    /* ========================================= */
    /* Derived risk metrics (display only)       */
    /* ========================================= */

    const aggregateRisk = computeAggregateRisk(
      imageResults,
      documentResult,
      signatureResult,
      videoResult,
        tamperingResult
    );


    const pipelineData = [

      {
        name: "Image",
        status: imageResults.length > 0 ? 1 : 0,
        label: imageResults.length > 0 ? "Available" : "Pending",
      },

      {
        name: "Document",
        status: documentResult ? 1 : 0,
        label: documentResult ? "Available" : "Pending",
      },

      {
        name: "Signature",
        status: signatureResult ? 1 : 0,
        label: signatureResult ? signatureResult.verdict : "Pending",
      },

      {
        name: "Video",
        status: videoResult ? 1 : 0,
        label: videoResult ? "Available" : "Pending",
      },

      {
        name: "Tampering",
        status: tamperingResult ? 1 : 0,
        label: tamperingResult ? tamperingResult.verdict : "Pending",
      },

    ];


    const activePipelines =
      pipelineData.filter((p) => p.status === 1).length;


    return (

        <div className="space-y-8">

            {/* ================================= */}
            {/* HEADER                            */}
            {/* ================================= */}

            <div>

                <h2 className="text-3xl font-bold text-white">

                    Unified Fraud Risk Dashboard

                </h2>

                <p className="mt-2 text-slate-400">

                    Consolidated forensic analysis
                    across all evidence pipelines.

                </p>

            </div>


            {/* ================================= */}
            {/* RISK GAUGE + PIPELINE CHART       */}
            {/* ================================= */}

            <div className="grid gap-6 lg:grid-cols-2">

              <GlassCard gradient="red" hover={false} className="flex flex-col items-center justify-center">

                <RiskGauge
                  score={aggregateRisk}
                  label="Aggregate Fraud Risk"
                />

                <p className="mt-4 text-sm text-slate-400">

                  Based on {activePipelines} active pipeline{activePipelines !== 1 ? "s" : ""}

                </p>

              </GlassCard>


              <GlassCard gradient="blue" hover={false}>

                <h3 className="mb-4 text-lg font-semibold text-white">

                  Pipeline Status

                </h3>

                <ResponsiveContainer width="100%" height={200}>

                  <BarChart data={pipelineData}>

                    <XAxis
                      dataKey="name"
                      tick={{ fill: "#94a3b8", fontSize: 12 }}
                      axisLine={false}
                      tickLine={false}
                    />

                    <YAxis hide domain={[0, 1]} />

                    <Tooltip
                      contentStyle={{
                        background: "rgba(15, 23, 42, 0.9)",
                        border: "1px solid rgba(148, 163, 184, 0.2)",
                        borderRadius: "8px",
                        color: "#f8fafc",
                      }}
                      formatter={(_, __, props) => [
                        props.payload.label,
                        "Status",
                      ]}
                    />

                    <Bar dataKey="status" radius={[6, 6, 0, 0]}>

                      {pipelineData.map((entry, index) => (

                        <Cell
                          key={index}
                          fill={entry.status ? "#3b82f6" : "#334155"}
                        />

                      ))}

                    </Bar>

                  </BarChart>

                </ResponsiveContainer>

              </GlassCard>

            </div>


            {/* ================================= */}
            {/* ANALYSIS STATUS CARDS             */}
            {/* ================================= */}

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">


                {/* IMAGE */}

                <GlassCard gradient="blue" hover={false}>

                    <p className="text-sm text-slate-400">

                        Image Forensics

                    </p>

                    <p className="mt-3 text-xl font-bold text-white">

                        {imageResults.length > 0

                            ? "Analysis Available"

                            : "No Analysis"

                        }

                    </p>

                    {imageResults.length > 0 && (
                      <div className="mt-2">
                        <StatusBadge
                          status={imageResults[0]?.analysis?.verdict}
                        />
                      </div>
                    )}

                </GlassCard>


                {/* DOCUMENT */}

                <GlassCard gradient="green" hover={false}>

                    <p className="text-sm text-slate-400">

                        Document Forensics

                    </p>

                    <p className="mt-3 text-xl font-bold text-white">

                        {documentResult

                            ? "Analysis Available"

                            : "No Analysis"

                        }

                    </p>

                </GlassCard>


                {/* SIGNATURE */}

                <GlassCard gradient="purple" hover={false}>

                    <p className="text-sm text-slate-400">

                        Signature Verification

                    </p>

                    <p className="mt-3 text-xl font-bold text-white">

                        {signatureResult

                            ? signatureResult.verdict

                            : "No Analysis"

                        }

                    </p>

                    {signatureResult && (
                      <StatusBadge status={signatureResult.verdict} />
                    )}

                </GlassCard>


                {/* VIDEO */}

                <GlassCard gradient="red" hover={false}>

                    <p className="text-sm text-slate-400">

                        Video Analytics

                    </p>

                    <p className="mt-3 text-xl font-bold text-white">

                        {videoResult

                            ? "Analysis Available"

                            : "No Analysis"

                        }

                    </p>

                </GlassCard>
                {/* TAMPERING */}

                <GlassCard gradient="orange" hover={false}>

                    <p className="text-sm text-slate-400">

                        Tampering Detection

                    </p>

                    <p className="mt-3 text-xl font-bold text-white">

                        {tamperingResult
                            ? tamperingResult.verdict
                            : "No Analysis"}

                    </p>

                    {tamperingResult && (

                        <StatusBadge
                            status={tamperingResult.verdict}
                        />

                    )}

                </GlassCard>

            </div>


            {/* ================================= */}
            {/* SIGNATURE RESULT                  */}
            {/* ================================= */}

            {signatureResult && (

                <GlassCard gradient="purple" hover={false}>

                    <h3 className="text-xl font-bold text-white">

                        Signature Verification

                    </h3>


                    <div className="mt-6 grid gap-6 md:grid-cols-3">


                        <div className="rounded-lg bg-slate-800/50 p-4">

                            <p className="text-sm text-slate-400">

                                Verdict

                            </p>

                            <p className="mt-2 text-2xl font-bold text-white">

                                {signatureResult.verdict}

                            </p>

                        </div>


                        <div className="rounded-lg bg-slate-800/50 p-4">

                            <p className="text-sm text-slate-400">

                                Similarity

                            </p>

                            <p className="mt-2 text-2xl font-bold text-white">

                                {(

                                    signatureResult.similarity *

                                    100

                                ).toFixed(2)}%

                            </p>

                        </div>


                        <div className="rounded-lg bg-slate-800/50 p-4">

                            <p className="text-sm text-slate-400">

                                Confidence

                            </p>

                            <p className="mt-2 text-2xl font-bold text-white">

                                {(

                                    signatureResult.confidence *

                                    100

                                ).toFixed(2)}%

                            </p>

                        </div>

                    </div>

                </GlassCard>

            )}


            {/* ================================= */}
            {/* VIDEO RESULT                      */}
            {/* ================================= */}

            {videoResult && (

                <GlassCard gradient="red" hover={false}>

                    <h3 className="text-xl font-bold text-white">

                        Video Analytics

                    </h3>


                    <div className="mt-6 grid gap-6 md:grid-cols-3">


                        <div className="rounded-lg bg-slate-800/50 p-4">

                            <p className="text-sm text-slate-400">

                                Frames Analyzed

                            </p>

                            <p className="mt-2 text-2xl font-bold text-white">

                                {videoResult.summary
                                    ?.frames_analyzed ?? 0}

                            </p>

                        </div>


                        <div className="rounded-lg bg-slate-800/50 p-4">

                            <p className="text-sm text-slate-400">

                                Average Brightness

                            </p>

                            <p className="mt-2 text-2xl font-bold text-white">

                                {videoResult.summary
                                    ?.average_brightness ?? 0}

                            </p>

                        </div>


                        <div className="rounded-lg bg-slate-800/50 p-4">

                            <p className="text-sm text-slate-400">

                                Average Blur Score

                            </p>

                            <p className="mt-2 text-2xl font-bold text-white">

                                {videoResult.summary
                                    ?.average_blur_score ?? 0}

                            </p>

                        </div>

                    </div>

                </GlassCard>

            )}


            {/* ================================= */}
            {/* IMAGE RESULTS                     */}
            {/* ================================= */}

            {imageResults.length > 0 && (

                <GlassCard gradient="blue" hover={false}>

                    <h3 className="text-xl font-bold text-white">

                        Image Forensics

                    </h3>


                    <div className="mt-6 space-y-4">

                        {imageResults.map(

                            (item, index) => (

                                <div

                                    key={index}

                                    className="rounded-lg border border-slate-700/50 bg-slate-800/40 p-5"

                                >

                                    <div className="flex items-center justify-between">

                                      <p className="font-semibold text-white">

                                          {item.filename}

                                      </p>

                                      <StatusBadge
                                        status={item.analysis?.verdict}
                                      />

                                    </div>


                                    <p className="mt-2 text-slate-400">

                                        Verdict:{" "}

                                        {item.analysis
                                            ?.verdict || "N/A"}

                                    </p>


                                    <p className="mt-1 text-slate-400">

                                        Forensic Score:{" "}

                                        {item.analysis
                                            ?.forensic_score ?? "N/A"}

                                    </p>

                                </div>

                            )

                        )}

                    </div>

                </GlassCard>

            )}


            {/* ================================= */}
            {/* DOCUMENT RESULTS                  */}
            {/* ================================= */}

            {documentResult && (

                <GlassCard gradient="green" hover={false}>

                    <h3 className="text-xl font-bold text-white">

                        Document Forensics

                    </h3>


                    <div className="mt-6 grid gap-4 sm:grid-cols-2">

                        <div className="rounded-lg bg-slate-800/50 p-4">

                            <p className="text-slate-400">

                                Document Type:

                            </p>

                            <p className="mt-1 font-semibold text-white">

                                {documentResult.document_type
                                    || "PDF"}

                            </p>

                        </div>


                        <div className="rounded-lg bg-slate-800/50 p-4">

                            <p className="text-slate-400">

                                Pages Analyzed:

                            </p>

                            <p className="mt-1 font-semibold text-white">

                                {documentResult.page_count
                                    || 0}

                            </p>

                        </div>

                    </div>

                </GlassCard>

            )}

            {/* ================================= */}
            {/* TAMPERING RESULT                  */}
            {/* ================================= */}

            {tamperingResult && (

            <GlassCard gradient="orange" hover={false}>

                <h3 className="text-xl font-bold text-white">

                    Tampering Detection

                </h3>

                <div className="mt-6 grid gap-4 md:grid-cols-3">

                    <div className="rounded-lg bg-slate-800/50 p-4">

                        <p className="text-slate-400">

                            Verdict

                        </p>

                        <p className="mt-2 text-xl font-bold text-white">

                            {tamperingResult.verdict}

                        </p>

                    </div>

                    <div className="rounded-lg bg-slate-800/50 p-4">

                        <p className="text-slate-400">

                            Severity

                        </p>

                        <p className="mt-2 text-xl font-bold text-white">

                            {tamperingResult.severity}

                        </p>

                    </div>

                    <div className="rounded-lg bg-slate-800/50 p-4">

                        <p className="text-slate-400">

                            Tampering Score

                        </p>

                        <p className="mt-2 text-xl font-bold text-white">

                            {tamperingResult.tampering_percentage}%

                        </p>

                    </div>

                </div>

                <div className="mt-6">

                    <h4 className="mb-2 font-semibold text-white">

                        Detected Signals

                    </h4>

                    <ul className="list-disc space-y-2 pl-6 text-slate-300">

                        {tamperingResult.signals?.map((signal, index) => (

                            <li key={index}>{signal}</li>

                        ))}

                    </ul>

                </div>

            </GlassCard>

            )}


        </div>

    );

}


export default UnifiedFraudDashboard;
