import { useEffect, useState } from "react";
import { analyzeTampering } from "../services/api";

export default function TamperingDetection({ evidenceId  }) {

    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState("");

    useEffect(() => {

        if (!evidenceId) return;

        async function runAnalysis() {

            try {

                setLoading(true);
                setError("");

                const data = await analyzeTampering(evidenceId);

                console.log("Tampering API Response:", data);

                setResult(data);

                console.log("Tampering API Response:", data);

                // Works whether backend returns {tampering:{...}}
                // or directly the tampering object.
                setResult(data.tampering ?? data);

            } catch (err) {

                console.error(err);
                setError(err.message);

            } finally {

                setLoading(false);

            }

        }

        runAnalysis();

    }, [evidenceId]);

    if (!evidenceId) return null;

    if (loading) {

        return (

            <div className="bg-white rounded-xl shadow p-6">

                <h2 className="text-xl font-bold mb-4">
                    Image Tampering Detection
                </h2>

                <p>Running forensic analysis...</p>

            </div>

        );

    }

    if (error) {

        return (

            <div className="bg-white rounded-xl shadow p-6">

                <h2 className="text-xl font-bold mb-4">
                    Image Tampering Detection
                </h2>

                <p className="text-red-500">{error}</p>

            </div>

        );

    }

    if (!result) return null;

    return (

        <div className="bg-white rounded-xl shadow p-6">

            <h2 className="text-2xl font-bold mb-5">
                Image Tampering Detection
            </h2>

            <div className="grid grid-cols-2 gap-4">

                <div>

                    <p className="text-gray-500">
                        Verdict
                    </p>

                    <p className="font-bold text-lg">
                        {result.verdict ?? "Unknown"}
                    </p>

                </div>

                <div>

                    <p className="text-gray-500">
                        Severity
                    </p>

                    <p className="font-bold text-lg">
                        {result.severity ?? "Unknown"}
                    </p>

                </div>

                <div>

                    <p className="text-gray-500">
                        Tampering Score
                    </p>

                    <p className="font-bold">
                        {(((result.tampering_score ?? 0) * 100)).toFixed(2)}%
                    </p>

                </div>

                <div>

                    <p className="text-gray-500">
                        Confidence
                    </p>

                    <p className="font-bold">
                        {(((result.confidence ?? 0) * 100)).toFixed(2)}%
                    </p>

                </div>

            </div>

            <hr className="my-5" />

            <h3 className="font-semibold mb-2">
                Forensic Signals
            </h3>

            <ul className="list-disc ml-5 space-y-2">

                {(result.signals ?? []).map((signal, index) => (

                    <li key={index}>
                        {signal}
                    </li>

                ))}

            </ul>

            <hr className="my-5" />

            <h3 className="font-semibold mb-3">
                Module Scores
            </h3>

            <div className="space-y-2">

                <div>

                    <strong>ELA :</strong>{" "}

                    {(
                        ((result.analysis?.ela?.suspicion_score ?? 0) * 100)
                    ).toFixed(1)}%

                </div>

                <div>

                    <strong>Copy Move :</strong>{" "}

                    {(
                        ((result.analysis?.copy_move?.suspicion_score ?? 0) * 100)
                    ).toFixed(1)}%

                </div>

                <div>

                    <strong>Edge Inconsistency :</strong>{" "}

                    {(
                        ((result.analysis?.edge_inconsistency?.suspicion_score ?? 0) * 100)
                    ).toFixed(1)}%

                </div>

                <div>

                    <strong>Metadata :</strong>{" "}

                    {(
                        ((result.analysis?.metadata?.suspicion_score ?? 0) * 100)
                    ).toFixed(1)}%

                </div>

            </div>

        </div>

    );

}