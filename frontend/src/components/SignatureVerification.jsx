import { useState } from "react";
import { Upload, CheckCircle, AlertCircle, Loader2 } from "lucide-react";

import GlassCard from "./ui/GlassCard";
import StatusBadge from "./ui/StatusBadge";
import ProgressBar from "./ui/ProgressBar";

import {
    verifySignature
} from "../services/api";


export default function SignatureVerification({ onResult }) {

    const [
        referenceFile,
        setReferenceFile
    ] = useState(null);


    const [
        queryFile,
        setQueryFile
    ] = useState(null);


    const [
        result,
        setResult
    ] = useState(null);


    const [
        loading,
        setLoading
    ] = useState(false);


    const [
        error,
        setError
    ] = useState("");


    async function handleVerify() {

        if (
            !referenceFile ||
            !queryFile
        ) {

            setError(
                "Please upload both signatures."
            );

            return;
        }


        try {

            setLoading(true);

            setError("");

            setResult(null);


            const data =
                await verifySignature(

                    referenceFile,

                    queryFile

                );


            setResult(data.result);

            setResult(data.analysis);

            if (onResult) {
                onResult(data.analysis);
            }

        } catch (err) {

            setError(
                err.message
            );

        } finally {

            setLoading(false);

        }

    }


    return (

        <div>

            {/* ================================= */}
            {/* PAGE HEADER (when standalone)     */}
            {/* ================================= */}

            {!onResult && (

                <div className="mb-8">

                    <h2 className="text-3xl font-bold tracking-tight text-white md:text-4xl">

                        Signature Verification

                    </h2>

                    <p className="mt-3 text-slate-400">

                        Compare a reference signature against a suspected
                        signature using the AI-FORGE Siamese Network.

                    </p>

                </div>

            )}


            {/* ================================= */}
            {/* UPLOAD GRID                       */}
            {/* ================================= */}

            <div className="grid gap-6 md:grid-cols-2">


                {/* Reference Signature */}

                <GlassCard gradient="purple">

                    <h2 className="text-lg font-semibold text-white mb-4">

                        Reference Signature

                    </h2>


                    <div className="upload-zone rounded-xl p-6 text-center">

                        <Upload className="mx-auto h-8 w-8 text-slate-500" />

                        <label className="mt-4 inline-flex cursor-pointer items-center gap-2 rounded-lg bg-purple-600/80 px-4 py-2 text-sm font-semibold text-white transition hover:bg-purple-500">

                            Select Reference

                            <input
                                type="file"
                                accept=".png,.jpg,.jpeg"
                                onChange={(e) =>
                                    setReferenceFile(
                                        e.target.files[0]
                                    )
                                }
                                className="hidden"
                            />

                        </label>

                    </div>


                    {referenceFile && (

                        <p className="mt-3 flex items-center gap-2 text-sm text-emerald-400">

                            <CheckCircle className="h-4 w-4" />

                            {referenceFile.name}

                        </p>

                    )}

                </GlassCard>


                {/* Query Signature */}

                <GlassCard gradient="blue">

                    <h2 className="text-lg font-semibold text-white mb-4">

                        Signature to Verify

                    </h2>


                    <div className="upload-zone rounded-xl p-6 text-center">

                        <Upload className="mx-auto h-8 w-8 text-slate-500" />

                        <label className="mt-4 inline-flex cursor-pointer items-center gap-2 rounded-lg bg-blue-600/80 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-500">

                            Select Query

                            <input
                                type="file"
                                accept=".png,.jpg,.jpeg"
                                onChange={(e) =>
                                    setQueryFile(
                                        e.target.files[0]
                                    )
                                }
                                className="hidden"
                            />

                        </label>

                    </div>


                    {queryFile && (

                        <p className="mt-3 flex items-center gap-2 text-sm text-emerald-400">

                            <CheckCircle className="h-4 w-4" />

                            {queryFile.name}

                        </p>

                    )}

                </GlassCard>

            </div>


            {/* ================================= */}
            {/* VERIFY BUTTON                     */}
            {/* ================================= */}

            <button

                onClick={handleVerify}

                disabled={loading}

                className="mt-6 inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-6 py-3 font-semibold text-white shadow-lg shadow-purple-500/20 transition hover:from-purple-500 hover:to-blue-500 disabled:cursor-not-allowed disabled:opacity-50"

            >

                {loading ? (
                    <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Verifying...
                    </>
                ) : (
                    "Verify Signature"
                )}

            </button>


            {loading && (

                <div className="mt-4 max-w-md">

                    <ProgressBar
                        value={75}
                        label="Running Siamese network inference..."
                        color="purple"
                    />

                </div>

            )}


            {/* ================================= */}
            {/* ERROR                             */}
            {/* ================================= */}

            {error && (

                <div className="mt-6 flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-red-400">

                    <AlertCircle className="h-4 w-4 shrink-0" />

                    {error}

                </div>

            )}


            {/* ================================= */}
            {/* RESULT                            */}
            {/* ================================= */}

            {result && (

                <GlassCard gradient="green" className="mt-8">

                    <div className="flex items-center justify-between mb-6">

                        <h2 className="text-xl font-bold text-white">

                            Verification Result

                        </h2>

                        <StatusBadge status={result.verdict} />

                    </div>


                    <div className="grid gap-6 md:grid-cols-3">


                        <div className="rounded-lg bg-slate-800/50 p-5">

                            <p className="text-sm text-slate-400">

                                Verdict

                            </p>

                            <p className="mt-2 text-2xl font-bold text-white">

                                {result.verdict}

                            </p>

                        </div>


                        <div className="rounded-lg bg-slate-800/50 p-5">

                            <p className="text-sm text-slate-400">

                                Similarity

                            </p>

                            <p className="mt-2 text-2xl font-bold text-white">

                                {(
                                    result.similarity
                                    * 100
                                ).toFixed(2)}%

                            </p>

                            <ProgressBar
                                value={result.similarity * 100}
                                color="blue"
                                showPercent={false}
                                className="mt-3"
                            />

                        </div>


                        <div className="rounded-lg bg-slate-800/50 p-5">

                            <p className="text-sm text-slate-400">

                                Confidence

                            </p>

                            <p className="mt-2 text-2xl font-bold text-white">

                                {(
                                    result.confidence
                                    * 100
                                ).toFixed(2)}%

                            </p>

                            <ProgressBar
                                value={result.confidence * 100}
                                color="purple"
                                showPercent={false}
                                className="mt-3"
                            />

                        </div>

                    </div>

                </GlassCard>

            )}

        </div>

    );

}
