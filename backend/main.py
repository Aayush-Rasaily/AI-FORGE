from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.video_routes import router as video_router
from backend.api.routes import router
from backend.api.signature_routes import (
    router as signature_router
)
from backend.api.signature_routes import (
    router as signature_router
)
app = FastAPI(
    title="AI-FORGE API",
    description="AI-Powered Multimodal Fraud Detection and Digital Forensics Platform",
    version="1.0.0"
)
from fastapi.staticfiles import StaticFiles

app.mount(
    "/data",
    StaticFiles(directory="data"),
    name="data",
)


# React frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    video_router
)

# Register API routes
app.include_router(
    router
)

app.include_router(
    signature_router
)
@app.get("/")
def root():

    return {
        "message": "Welcome to AI-FORGE API",
        "status": "success"
    }


@app.get("/api/health")
def health_check():

    return {
        "status": "healthy",
        "service": "AI-FORGE Backend"
    }