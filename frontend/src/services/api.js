const API_BASE_URL = "http://localhost:8000";


// ==========================================
// HELPER: Parse API Error
// ==========================================

async function getApiError(response, defaultMessage) {

    try {

        const errorData =
            await response.json();

        return (
            errorData.detail ||
            errorData.message ||
            defaultMessage
        );

    } catch {

        // We intentionally ignore JSON parsing errors
        // and return the default message.
        return defaultMessage;

    }

}


// ==========================================
// Check Backend Health
// ==========================================

export async function checkBackendHealth() {

    try {

        const response = await fetch(
            `${API_BASE_URL}/api/health`
        );


        if (!response.ok) {

            throw new Error(
                "Backend is not healthy"
            );

        }


        return await response.json();

    } catch (error) {

        console.error(
            "Backend health check failed:",
            error
        );

        throw error;

    }

}


// ==========================================
// Upload Evidence
// ==========================================

export async function uploadEvidence(file) {

    try {

        const formData =
            new FormData();


        formData.append(
            "file",
            file
        );


        const response =
            await fetch(

                `${API_BASE_URL}/api/evidence/upload`,

                {
                    method: "POST",
                    body: formData
                }

            );


        if (!response.ok) {

            const errorMessage =
                await getApiError(

                    response,

                    "Evidence upload failed"

                );


            throw new Error(
                errorMessage
            );

        }


        return await response.json();

    } catch (error) {

        console.error(
            "Evidence upload error:",
            error
        );

        throw error;

    }

}


// ==========================================
// Analyze Image
//
// IMPORTANT:
// This now uses the UNIFIED analysis endpoint.
//
// Endpoint:
// POST /api/evidence/analyze/{evidenceId}
//
// This runs:
// - ELA
// - Edge Detection
// - Wavelet Analysis
// - Copy-Move Detection
// ==========================================

export async function analyzeImage(evidenceId) {

    try {

        const response = await fetch(
            `${API_BASE_URL}/api/evidence/analyze/${evidenceId}`, {
                method: "POST",
            }
        );

        if (!response.ok) {

            let errorMessage =
                "Image analysis failed";

            try {

                const errorData =
                    await response.json();

                errorMessage =
                    errorData.detail ||
                    errorMessage;

            } catch {
                // Ignore JSON parsing error
            }

            throw new Error(
                errorMessage
            );
        }

        return await response.json();

    } catch (error) {

        console.error(
            "Image analysis error:",
            error
        );

        throw error;

    }
}

// ==========================================
// Unified Evidence Analysis
//
// Same backend endpoint as analyzeImage().
// Kept as a separate function for compatibility.
// ==========================================

export async function analyzeEvidence(
    evidenceId
) {

    if (!evidenceId) {

        throw new Error(
            "Evidence ID is required"
        );

    }


    try {

        const response =
            await fetch(

                `${API_BASE_URL}/api/evidence/analyze/${evidenceId}`,

                {
                    method: "POST"
                }

            );


        if (!response.ok) {

            const errorMessage =
                await getApiError(

                    response,

                    "Evidence analysis failed"

                );


            throw new Error(
                errorMessage
            );

        }


        return await response.json();

    } catch (error) {

        console.error(
            "Unified evidence analysis error:",
            error
        );

        throw error;

    }

}


// ==========================================
// Get Artifact URL
//
// Supports:
// 1. Full URL
// 2. API path
// 3. Relative path
// ==========================================

export function getArtifactUrl(
    artifactPath
) {

    if (!artifactPath) {

        console.error(
            "Artifact path is missing"
        );

        return "";

    }


    // Already a complete URL
    if (
        artifactPath.startsWith(
            "http://"
        ) ||
        artifactPath.startsWith(
            "https://"
        )
    ) {

        return artifactPath;

    }


    // Backend API path
    if (
        artifactPath.startsWith(
            "/api/"
        )
    ) {

        return (
            `${API_BASE_URL}` +
            artifactPath
        );

    }


    // Filesystem-style path
    return (

        `${API_BASE_URL}/` +

        artifactPath
        .replaceAll(
            "\\",
            "/"
        )
        .replace(/^\/+/, "")

    );

}


// ==========================================
// Verify Signature
// ==========================================

export async function verifySignature(
    referenceFile,
    queryFile
) {

    try {

        const formData =
            new FormData();


        formData.append(
            "reference",
            referenceFile
        );


        formData.append(
            "query",
            queryFile
        );


        const response =
            await fetch(

                `${API_BASE_URL}/api/evidence/verify-signature`,

                {
                    method: "POST",
                    body: formData
                }

            );


        if (!response.ok) {

            const errorMessage =
                await getApiError(

                    response,

                    "Signature verification failed"

                );


            throw new Error(
                errorMessage
            );

        }


        return await response.json();

    } catch (error) {

        console.error(
            "Signature verification error:",
            error
        );

        throw error;

    }

}


// ==========================================
// Copy-Move Detection
// ==========================================

export async function analyzeCopyMove(
    evidenceId
) {

    if (!evidenceId) {

        throw new Error(
            "Evidence ID is required"
        );

    }


    try {

        const response =
            await fetch(

                `${API_BASE_URL}/api/evidence/analyze-copy-move/${evidenceId}`,

                {
                    method: "POST"
                }

            );


        if (!response.ok) {

            const errorMessage =
                await getApiError(

                    response,

                    "Copy-Move analysis failed"

                );


            throw new Error(
                errorMessage
            );

        }


        return await response.json();

    } catch (error) {

        console.error(
            "Copy-Move analysis error:",
            error
        );

        throw error;

    }

}


// ==========================================
// Get Copy-Move Artifact URL
// ==========================================

export function getCopyMoveArtifactUrl(
    evidenceId
) {

    if (!evidenceId) {

        return "";

    }


    return (

        `${API_BASE_URL}` +

        `/api/evidence/artifacts/` +

        `${evidenceId}/copy_move`

    );

}


// ==========================================
// Get Unified Artifact URL
//
// Artifact types:
// - ela
// - edges
// - wavelet
// - copy_move
// ==========================================

export function getUnifiedArtifactUrl(
    evidenceId,
    artifactType
) {

    if (!evidenceId ||
        !artifactType
    ) {

        return "";

    }


    return (

        `${API_BASE_URL}` +

        `/api/evidence/artifacts/` +

        `${evidenceId}/` +

        `${artifactType}`

    );

}


// ==========================================
// Get API Base URL
// ==========================================

export function getApiBaseUrl() {

    return API_BASE_URL;

}

// ------------------------------------
// Analyze PDF Document
// ------------------------------------

export async function analyzeDocument(
    evidenceId
) {

    try {

        const response = await fetch(
            `${API_BASE_URL}/api/evidence/analyze-document/${evidenceId}`, {
                method: "POST",
            }
        );


        if (!response.ok) {

            let errorMessage =
                "Document analysis failed";


            try {

                const errorData =
                    await response.json();

                errorMessage =
                    errorData.detail ||
                    errorMessage;

            } catch {

                // Ignore JSON parsing error

            }


            throw new Error(
                errorMessage
            );

        }


        return await response.json();

    } catch (error) {

        console.error(
            "Document analysis error:",
            error
        );

        throw error;

    }

}