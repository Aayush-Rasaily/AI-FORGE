import {
    useState
} from "react";


function ArtifactCard({
    title,
    description,
    artifactUrl
}) {

    const [
        imageError,
        setImageError
    ] = useState(false);


    return (

        <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">

            <h5 className="text-lg font-semibold text-white">
                {title}
            </h5>


            <p className="mt-1 text-sm text-slate-400">
                {description}
            </p>


            <div className="mt-4 overflow-hidden rounded-lg bg-slate-950">

                {!artifactUrl ? (

                    <div className="flex min-h-[250px] items-center justify-center text-slate-500">

                        Artifact URL unavailable

                    </div>

                ) : imageError ? (

                    <div className="flex min-h-[250px] flex-col items-center justify-center p-6 text-center">

                        <p className="text-red-400">
                            Failed to load forensic artifact.
                        </p>


                        <p className="mt-2 break-all text-xs text-slate-500">
                            {artifactUrl}
                        </p>

                    </div>

                ) : (

                    <img

                        src={artifactUrl}

                        alt={title}

                        className="h-auto max-h-[500px] w-full object-contain"

                        onError={() => {

                            console.error(
                                "Artifact failed to load:",
                                artifactUrl
                            );

                            setImageError(
                                true
                            );

                        }}

                    />

                )}

            </div>

        </div>

    );

}


export default ArtifactCard;