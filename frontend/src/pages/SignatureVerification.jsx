import { useState } from "react";

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

            if (onResult) {
                onResult(data.result);
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

        <div className="min-h-screen bg-slate-950 text-white p-8">

            <div className="max-w-5xl mx-auto">

                <h1 className="text-3xl font-bold mb-2">

                    Signature Verification

                </h1>


                <p className="text-slate-400 mb-8">

                    Compare a reference signature
                    against a suspected signature
                    using the AI-FORGE Siamese Network.

                </p>


                <div className="grid md:grid-cols-2 gap-6">


                    {/* Reference Signature */}

                    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">

                        <h2 className="text-lg font-semibold mb-4">

                            Reference Signature

                        </h2>


                        <input

                            type="file"

                            accept=".png,.jpg,.jpeg"

                            onChange={(e) =>
                                setReferenceFile(
                                    e.target.files[0]
                                )
                            }

                            className="w-full text-sm"

                        />


                        {referenceFile && (

                            <p className="text-green-400 mt-3">

                                ✓ {referenceFile.name}

                            </p>

                        )}

                    </div>


                    {/* Query Signature */}

                    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">

                        <h2 className="text-lg font-semibold mb-4">

                            Signature to Verify

                        </h2>


                        <input

                            type="file"

                            accept=".png,.jpg,.jpeg"

                            onChange={(e) =>
                                setQueryFile(
                                    e.target.files[0]
                                )
                            }

                            className="w-full text-sm"

                        />


                        {queryFile && (

                            <p className="text-green-400 mt-3">

                                ✓ {queryFile.name}

                            </p>

                        )}

                    </div>

                </div>


                {/* Verify Button */}

                <button

                    onClick={
                        handleVerify
                    }

                    disabled={
                        loading
                    }

                    className="mt-6 px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-semibold disabled:opacity-50"

                >

                    {loading

                        ? "Verifying..."

                        : "Verify Signature"

                    }

                </button>


                {/* Error */}

                {error && (

                    <div className="mt-6 p-4 bg-red-900/30 border border-red-700 rounded-lg">

                        {error}

                    </div>

                )}


                {/* Result */}

                {result && (

                    <div className="mt-8 bg-slate-900 border border-slate-800 rounded-xl p-8">

                        <h2 className="text-xl font-bold mb-6">

                            Verification Result

                        </h2>


                        <div className="grid md:grid-cols-3 gap-6">


                            <div>

                                <p className="text-slate-400">

                                    Verdict

                                </p>

                                <p className="text-2xl font-bold mt-2">

                                    {result.verdict}

                                </p>

                            </div>


                            <div>

                                <p className="text-slate-400">

                                    Similarity

                                </p>

                                <p className="text-2xl font-bold mt-2">

                                    {(
                                        result.similarity
                                        * 100
                                    ).toFixed(2)}%

                                </p>

                            </div>


                            <div>

                                <p className="text-slate-400">

                                    Confidence

                                </p>

                                <p className="text-2xl font-bold mt-2">

                                    {(
                                        result.confidence
                                        * 100
                                    ).toFixed(2)}%

                                </p>

                            </div>

                        </div>

                    </div>

                )}

            </div>

        </div>

    );

}