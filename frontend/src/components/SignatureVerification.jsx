import { useState } from "react";

import {
  verifySignature
} from "../services/api";


function SignatureVerification() {


  // ==========================================
  // STATE
  // ==========================================

  const [
    referenceFile,
    setReferenceFile
  ] = useState(null);


  const [
    queryFile,
    setQueryFile
  ] = useState(null);


  const [
    signatureResult,
    setSignatureResult
  ] = useState(null);


  const [
    signatureLoading,
    setSignatureLoading
  ] = useState(false);


  const [
    signatureError,
    setSignatureError
  ] = useState("");


  // ==========================================
  // VERIFY
  // ==========================================

  const handleSignatureVerification =
    async () => {


      if (!referenceFile) {

        setSignatureError(
          "Please upload a reference signature."
        );

        return;

      }


      if (!queryFile) {

        setSignatureError(
          "Please upload a query signature."
        );

        return;

      }


      setSignatureLoading(
        true
      );

      setSignatureError("");

      setSignatureResult(
        null
      );


      try {

        const response =
          await verifySignature(

            referenceFile,

            queryFile

          );


        setSignatureResult(

          response.analysis

        );


      } catch (error) {

        console.error(

          "Signature verification error:",

          error

        );


        setSignatureError(

          error.message ||

          "Signature verification failed."

        );


      } finally {

        setSignatureLoading(
          false
        );

      }

    };


  // ==========================================
  // RESET
  // ==========================================

  const resetSignatureVerification =
    () => {

      setReferenceFile(
        null
      );

      setQueryFile(
        null
      );

      setSignatureResult(
        null
      );

      setSignatureError(
        ""
      );

    };


  return (

    <div className="mt-10 rounded-xl border border-slate-800 bg-slate-900 p-8">


      <h3 className="text-2xl font-bold">
        Signature Verification
      </h3>


      <p className="mt-2 text-slate-400">

        Compare a reference signature against
        a query signature using the trained
        Siamese Neural Network.

      </p>


      {/* FILES */}

      <div className="mt-8 grid gap-6 md:grid-cols-2">


        {/* REFERENCE */}

        <div className="rounded-xl border border-slate-700 bg-slate-950 p-6">

          <h4 className="font-semibold">
            Reference Signature
          </h4>


          <p className="mt-2 text-sm text-slate-400">
            Upload a known genuine signature.
          </p>


          <input

            type="file"

            accept="image/png,image/jpeg,image/jpg"

            onChange={(event) => {

              setReferenceFile(

                event.target.files[0] ||
                null

              );

              setSignatureResult(
                null
              );

            }}

            className="mt-5 block w-full text-sm text-slate-400"

          />


          {referenceFile && (

            <div className="mt-5">

              <img

                src={URL.createObjectURL(
                  referenceFile
                )}

                alt="Reference Signature"

                className="h-48 w-full rounded-lg bg-white object-contain"

              />


              <p className="mt-2 text-xs text-slate-500">
                {referenceFile.name}
              </p>

            </div>

          )}

        </div>


        {/* QUERY */}

        <div className="rounded-xl border border-slate-700 bg-slate-950 p-6">

          <h4 className="font-semibold">
            Query Signature
          </h4>


          <p className="mt-2 text-sm text-slate-400">
            Upload the signature you want
            to verify.
          </p>


          <input

            type="file"

            accept="image/png,image/jpeg,image/jpg"

            onChange={(event) => {

              setQueryFile(

                event.target.files[0] ||
                null

              );

              setSignatureResult(
                null
              );

            }}

            className="mt-5 block w-full text-sm text-slate-400"

          />


          {queryFile && (

            <div className="mt-5">

              <img

                src={URL.createObjectURL(
                  queryFile
                )}

                alt="Query Signature"

                className="h-48 w-full rounded-lg bg-white object-contain"

              />


              <p className="mt-2 text-xs text-slate-500">
                {queryFile.name}
              </p>

            </div>

          )}

        </div>

      </div>


      {/* ERROR */}

      {signatureError && (

        <div className="mt-6 rounded-lg border border-red-800 bg-red-950 p-4 text-red-300">

          🔴 {signatureError}

        </div>

      )}


      {/* BUTTONS */}

      <div className="mt-8 flex gap-4">


        <button

          onClick={
            handleSignatureVerification
          }

          disabled={
            signatureLoading
          }

          className="rounded-lg bg-purple-600 px-8 py-3 font-semibold transition hover:bg-purple-500 disabled:cursor-not-allowed disabled:opacity-50"

        >

          {signatureLoading

            ? "Verifying Signature..."

            : "Verify Signature"

          }

        </button>


        <button

          onClick={
            resetSignatureVerification
          }

          className="rounded-lg border border-slate-700 px-8 py-3 font-semibold transition hover:bg-slate-800"

        >

          Reset

        </button>

      </div>


      {/* RESULT */}

      {signatureResult && (

        <div className="mt-10 rounded-xl border border-slate-700 bg-slate-950 p-8">


          <h3 className="text-2xl font-bold">
            Signature Verification Result
          </h3>


          {/* VERDICT */}

          <div className="mt-8">

            <p className="text-sm text-slate-400">
              Verdict
            </p>


            <p className={`mt-2 text-3xl font-bold ${
              signatureResult.verdict ===
              "Genuine"

                ? "text-green-400"

                : "text-red-400"

            }`}>

              {signatureResult.verdict}

            </p>

          </div>


          {/* METRICS */}

          <div className="mt-8 grid gap-6 md:grid-cols-2">


            <div className="rounded-lg bg-slate-900 p-6">

              <p className="text-sm text-slate-400">
                Similarity
              </p>


              <p className="mt-2 text-3xl font-bold">

                {(
                  signatureResult.similarity *

                  100

                ).toFixed(2)}%

              </p>

            </div>


            <div className="rounded-lg bg-slate-900 p-6">

              <p className="text-sm text-slate-400">
                Confidence
              </p>


              <p className="mt-2 text-3xl font-bold">

                {(
                  signatureResult.confidence *

                  100

                ).toFixed(2)}%

              </p>

            </div>

          </div>


          {/* SIMILARITY BAR */}

          <div className="mt-8">

            <div className="flex justify-between">

              <p className="text-sm text-slate-400">
                Similarity Score
              </p>


              <p className="text-sm text-slate-400">

                {(
                  signatureResult.similarity *

                  100

                ).toFixed(2)}%

              </p>

            </div>


            <div className="mt-3 h-4 overflow-hidden rounded-full bg-slate-800">

              <div

                className={`h-full ${
                  signatureResult.verdict ===
                  "Genuine"

                    ? "bg-green-500"

                    : "bg-red-500"

                }`}

                style={{

                  width:

                    `${Math.max(

                      0,

                      Math.min(

                        signatureResult.similarity *

                        100,

                        100

                      )

                    )}%`

                }}

              />

            </div>

          </div>

        </div>

      )}

    </div>

  );

}

export default SignatureVerification;