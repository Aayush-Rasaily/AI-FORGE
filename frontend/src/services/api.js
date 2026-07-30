const API_BASE_URL = "http://localhost:8000";

// ------------------------------------
// Check Backend Health
// ------------------------------------
export async function checkBackendHealth() {
    try {
        const response = await fetch(
            `${API_BASE_URL}/api/health`
        );

        if (!response.ok) {
            throw new Error("Backend is not healthy");
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


// ------------------------------------
// Upload Evidence
// ------------------------------------
export async function uploadEvidence(file) {
    try {
        const formData = new FormData();

        formData.append("file", file);

        const response = await fetch(
            `${API_BASE_URL}/api/evidence/upload`, {
                method: "POST",
                body: formData,
            }
        );

        if (!response.ok) {
            const errorData =
                await response.json();

            throw new Error(
                errorData.detail ||
                "Evidence upload failed"
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


// ------------------------------------
// Analyze Image
// ------------------------------------
export async function analyzeImage(
    evidenceId
) {
    try {
        const response = await fetch(
            `${API_BASE_URL}/api/evidence/analyze-image/${evidenceId}`, {
                method: "POST",
            }
        );

        if (!response.ok) {
            const errorData =
                await response.json();

            throw new Error(
                errorData.detail ||
                "Image analysis failed"
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

export function getArtifactUrl(artifactPath) {

    if (!artifactPath) {
        return "";
    }

    // Full URL
    if (artifactPath.startsWith("http")) {
        return artifactPath;
    }

    // Backend API path
    if (artifactPath.startsWith("/api/")) {
        return `${API_BASE_URL}${artifactPath}`;
    }

    // Fallback for filesystem-style path
    return `${API_BASE_URL}/${artifactPath.replaceAll("\\", "/")}`;
}