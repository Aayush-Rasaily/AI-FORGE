import asyncio
import logging
import tempfile
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Query,
    Request,
)

from fastapi.responses import FileResponse, JSONResponse
from fastapi.encoders import jsonable_encoder

from backend.core.evidence_manager import generate_evidence_id
from backend.forensics.integration import on_evidence_uploaded
from backend.forensics.user_context import get_investigator

from backend.ingestion.file_router import (
    identify_file_type,
)

from backend.analysis.document_forensics import (
    analyze_document,
)

from backend.services.image_analysis_service import run_image_analysis
from backend.services.document_analysis_service import run_document_analysis
from backend.utils.artifact_paths import resolve_artifact_path, artifact_api_urls
from backend.services.artifact_service import generate_artifact, get_artifact_status

from backend.models.signature.inference import (
    verify_signature,
)

from backend.analysis.copy_move import (
    detect_copy_move,
)

from backend.document_analysis.evidence_fusion import (
    make_json_serializable,
)

from backend.utils.cache import AnalysisCache
from backend.utils.errors import (
    DocumentAnalysisError,
    ForensicAnalysisError,
    structured_error,
)
from backend.pipeline.completion import build_standard_response
from backend.pipeline.validator import PipelineValidationError
from backend.database import init_db, get_analysis_by_evidence_id
from backend.utils.progress import ProgressBus

logger = logging.getLogger("ai_forge.api")

# Initialize database on module load
init_db()
# ============================================================
# SAFE JSON RESPONSE
# ============================================================

def safe_json_response(data):
    """
    Convert the complete response recursively into
    JSON-safe native Python objects.

    This prevents errors such as:

        TypeError: 'numpy.int32' object is not iterable

    and:

        ValueError: [TypeError(...), TypeError(...)]
    """

    # First pass:
    # Convert NumPy, Torch, dataclasses, tuples, etc.
    cleaned = make_json_serializable(data)

    # Second pass:
    # Let FastAPI's encoder handle any remaining
    # supported special objects.
    return jsonable_encoder(cleaned)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/api",
    tags=["Evidence"],
)


# ============================================================
# DIRECTORIES
# ============================================================

UPLOAD_DIR = Path(
    "data/temp/uploads"
)

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# MAXIMUM UPLOAD SIZE
# ============================================================

MAX_FILE_SIZE = (
    100
    * 1024
    * 1024
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

@router.get("/evidence/recent")
async def list_recent_evidence_endpoint(limit: int = Query(50, ge=1, le=200)):
    """Shared evidence list for Dashboard / Investigation / Timeline / Reports."""
    from backend.forensics.repository import list_recent_evidence

    items = list_recent_evidence(limit)
    return safe_json_response({
        "success": True,
        "evidence": items,
        "count": len(items),
    })


def find_evidence_file(
    evidence_id: str,
):
    """
    Find the uploaded evidence file using its generated evidence ID.
    Prefers working copy, then original vault, then legacy upload path.
    """
    from backend.evidence.paths import find_evidence_file as vault_find

    path = vault_find(evidence_id)
    if path and path.is_file():
        return path

    files = list(
        UPLOAD_DIR.glob(
            f"{evidence_id}.*"
        )
    )

    files = [
        file
        for file in files
        if file.is_file()
    ]

    if not files:

        raise HTTPException(
            status_code=404,
            detail="Evidence not found",
        )

    return files[0]


def get_analysis_dir(
    evidence_id: str,
):
    """
    Return the dedicated analysis directory
    for a specific evidence item.
    """

    analysis_dir = (
        UPLOAD_DIR
        / "analysis"
        / evidence_id
    )

    analysis_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    return analysis_dir


def _error_response(exc: Exception, module: str, status_code: int = 500):
    """Return structured JSON error without crashing the server."""
    logger.exception("%s failed: %s", module, exc)
    payload = structured_error(
        error=str(exc),
        module=module,
        details=str(exc),
        include_traceback=True,
        exc=exc,
    )
    return JSONResponse(status_code=status_code, content=payload)


# ============================================================
# 1. UPLOAD EVIDENCE
# ============================================================

@router.post(
    "/evidence/upload"
)
async def upload_evidence(
    request: Request,
    file: UploadFile = File(...),
    investigation_id: str | None = Query(None, description="Link evidence to investigation"),
):

    # -----------------------------------------
    # Validate filename
    # -----------------------------------------

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="No filename provided",
        )

    # -----------------------------------------
    # Identify file type
    # -----------------------------------------

    file_type = identify_file_type(
        file.filename
    )

    # -----------------------------------------
    # Reject unsupported files
    # -----------------------------------------

    if file_type == "unsupported":

        raise HTTPException(
            status_code=400,
            detail="Unsupported file type",
        )

    # -----------------------------------------
    # Generate evidence ID
    # -----------------------------------------

    evidence_id = (
        generate_evidence_id()
    )

    # -----------------------------------------
    # Preserve original extension
    # -----------------------------------------

    extension = Path(
        file.filename
    ).suffix.lower()

    # -----------------------------------------
    # Create unique filename
    # -----------------------------------------

    saved_filename = (
        f"{evidence_id}"
        f"{extension}"
    )

    file_path = (
        UPLOAD_DIR
        / saved_filename
    )

    # -----------------------------------------
    # Save uploaded file
    # -----------------------------------------

    total_size = 0

    try:

        with open(
            file_path,
            "wb",
        ) as buffer:

            while True:

                chunk = await file.read(
                    1024 * 1024
                )

                if not chunk:

                    break

                total_size += len(
                    chunk
                )

                # -----------------------------------------
                # Check maximum file size
                # -----------------------------------------

                if (
                    total_size
                    > MAX_FILE_SIZE
                ):

                    file_path.unlink(
                        missing_ok=True
                    )

                    raise HTTPException(
                        status_code=413,
                        detail=(
                            "File exceeds "
                            "100 MB limit"
                        ),
                    )

                buffer.write(
                    chunk
                )

    except HTTPException:

        raise

    except Exception as e:

        file_path.unlink(
            missing_ok=True
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to save file: "
                f"{str(e)}"
            ),
        )

    # -----------------------------------------
    # Forensic intake — SHA-256 + SHA-512 + custody
    # -----------------------------------------

    investigator = get_investigator(request)
    forensic = on_evidence_uploaded(
        evidence_id,
        file_path,
        original_filename=file.filename,
        media_type=file_type,
        investigator=investigator,
        investigation_id=investigation_id,
    )

    # Archive to evidence vault (original read-only + working copy + metadata.json)
    try:
        from backend.evidence.storage import archive_upload

        archive_upload(
            evidence_id,
            file_path,
            original_filename=file.filename,
            media_type=file_type,
        )
    except Exception as exc:
        logger.warning("Evidence vault archive failed for %s: %s", evidence_id, exc)

    # -----------------------------------------
    # Return upload result
    # -----------------------------------------

    return safe_json_response(
        {
            "success": True,
            "evidence_id": evidence_id,
            "original_filename": file.filename,
            "file_type": file_type,
            "file_size": total_size,
            "stored_filename": saved_filename,
            "hashes": forensic.get("hashes"),
            "investigation_id": investigation_id,
            "intake_timestamp": forensic.get("evidence", {}).get("intake_timestamp"),
            "message": (
                "Evidence uploaded successfully"
            ),
        }
    )


# ============================================================
# 2. UNIFIED IMAGE ANALYSIS
# ============================================================

@router.post(
    "/evidence/analyze-image/{evidence_id}"
)
async def analyze_uploaded_image(
    evidence_id: str,
    force_deep: bool = Query(False, description="Force full deep forensic scan"),
):

    # -----------------------------------------
    # Find uploaded evidence
    # -----------------------------------------

    image_path = find_evidence_file(
        evidence_id
    )

    # -----------------------------------------
    # Get dedicated analysis directory
    # -----------------------------------------

    analysis_dir = get_analysis_dir(
        evidence_id
    )

    progress = ProgressBus.create(evidence_id)
    progress.emit("pipeline", "running")

    try:

        result, tampering_result, timing, from_cache, completion = await asyncio.to_thread(
            run_image_analysis,
            image_path,
            analysis_dir,
            evidence_id,
            True,
            progress,
            force_deep,
            False,
        )

        return safe_json_response(build_standard_response(
            evidence_id,
            result,
            tampering_result,
            completion,
            timing=timing,
            cached=from_cache,
            scan_mode=result.get("scan_mode", "deep"),
        ))

    except PipelineValidationError as e:
        progress.fail(str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e

    except HTTPException:
        raise

    except ForensicAnalysisError as e:
        progress.fail(str(e))
        return _error_response(e, e.module, e.status_code)

    except Exception as e:
        progress.fail(str(e))
        return _error_response(e, "image_analysis")


# ============================================================
# 3. UNIFIED ANALYSIS ALIAS
# ============================================================

@router.post(
    "/evidence/analyze/{evidence_id}"
)
async def analyze_evidence(
    evidence_id: str,
    force_deep: bool = Query(False, description="Force full deep forensic scan"),
):

    image_path = find_evidence_file(evidence_id)
    analysis_dir = get_analysis_dir(evidence_id)
    progress = ProgressBus.create(evidence_id)
    progress.emit("pipeline", "running")

    try:

        result, tampering_result, timing, from_cache, completion = await asyncio.to_thread(
            run_image_analysis,
            image_path,
            analysis_dir,
            evidence_id,
            True,
            progress,
            force_deep,
            False,
        )

        return safe_json_response(build_standard_response(
            evidence_id,
            result,
            tampering_result,
            completion,
            timing=timing,
            cached=from_cache,
            scan_mode=result.get("scan_mode", "deep"),
        ))

    except PipelineValidationError as e:
        progress.fail(str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e

    except HTTPException:
        raise

    except ForensicAnalysisError as e:
        progress.fail(str(e))
        return _error_response(e, e.module, e.status_code)

    except Exception as e:
        progress.fail(str(e))
        return _error_response(e, "unified_analysis")


@router.get("/evidence/artifacts-status/{evidence_id}")
async def get_artifacts_status(evidence_id: str):
    """Check background artifact generation status."""
    analysis_dir = get_analysis_dir(evidence_id)
    status = get_artifact_status(analysis_dir)
    return safe_json_response({"success": True, "evidence_id": evidence_id, **status})


@router.get("/evidence/report/{evidence_id}")
async def get_stored_report(evidence_id: str):
    """Instantly reopen a stored analysis report from the database."""
    record = get_analysis_by_evidence_id(evidence_id)
    if not record:
        raise HTTPException(status_code=404, detail="Report not found.")
    return safe_json_response({"success": True, "evidence_id": evidence_id, **record})


@router.get("/evidence/report/{evidence_id}/download")
async def download_evidence_report(
    evidence_id: str,
    format: str = Query("pdf", description="pdf | docx | json | html"),
    template: str = Query("full"),
):
    """Backward-compatible report download — serves pre-generated report.pdf when available."""
    analysis_dir = get_analysis_dir(evidence_id)
    canonical = analysis_dir / "report.pdf"
    if format == "pdf" and template in ("full", "executive") and canonical.exists():
        return FileResponse(path=str(canonical), filename=f"{evidence_id}_report.pdf", media_type="application/pdf")

    from backend.reports.exporter import FORMATS, TEMPLATES, export_report

    if format not in FORMATS:
        raise HTTPException(status_code=400, detail=f"Format must be one of: {FORMATS}")
    if template not in TEMPLATES:
        raise HTTPException(status_code=400, detail=f"Template must be one of: {TEMPLATES}")

    try:
        result = export_report(evidence_id, format=format, template=template)
        file_path = Path(result["file_path"])
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Report unavailable")

        media_types = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "json": "application/json",
            "html": "text/html",
        }
        return FileResponse(
            path=str(file_path),
            filename=result["filename"],
            media_type=media_types.get(format, "application/octet-stream"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Report download failed: %s", exc)
        raise HTTPException(status_code=500, detail="Unable to generate report") from exc


# ============================================================
# 4. GET FORENSIC ARTIFACT
# ============================================================

@router.get(
    "/evidence/artifacts/"
    "{evidence_id}/"
    "{artifact_type}"
)
async def get_evidence_artifact(
    evidence_id: str,
    artifact_type: str,
):

    # -----------------------------------------
    # Find uploaded evidence
    # -----------------------------------------

    image_path = find_evidence_file(
        evidence_id
    )

    # -----------------------------------------
    # Analysis directory
    # -----------------------------------------

    analysis_dir = get_analysis_dir(
        evidence_id
    )

    # -----------------------------------------
    # Artifact paths
    # -----------------------------------------

    artifact_map = {
        "ela": resolve_artifact_path(analysis_dir, "ela", image_path.stem),
        "edges": resolve_artifact_path(analysis_dir, "edges", image_path.stem),
        "wavelet": resolve_artifact_path(analysis_dir, "wavelet", image_path.stem),
        "copy_move": resolve_artifact_path(analysis_dir, "copy_move", image_path.stem),
    }

    if artifact_type not in artifact_map:
        raise HTTPException(
            status_code=400,
            detail="Invalid artifact type. Use ela, edges, wavelet, or copy_move.",
        )

    artifact_path = artifact_map[artifact_type]

    if not artifact_path.exists():
        from backend.services.image_analysis_service import _extract_tampering
        from backend.utils.cache import AnalysisCache

        cache = AnalysisCache(evidence_id, analysis_dir)
        cached = cache.load() or {}
        tampering = cached.get("tampering") or _extract_tampering(cached.get("analysis") or {})

        try:
            generated = generate_artifact(
                evidence_id, image_path, analysis_dir, artifact_type, tampering,
            )
            if generated and Path(generated).exists():
                artifact_path = Path(generated)
        except Exception as exc:
            logger.warning("On-demand artifact generation failed: %s", exc)

    if not artifact_path.exists():
        from backend.utils.artifact_visualization import create_placeholder
        from backend.utils.artifact_paths import artifact_path as canonical_path
        placeholder = canonical_path(analysis_dir, artifact_type)
        create_placeholder(
            placeholder,
            artifact_type.upper().replace("_", " "),
            "Generating forensic visualization… please refresh.",
        )
        artifact_path = placeholder

    media = "image/png" if artifact_path.suffix.lower() == ".png" else "image/jpeg"
    return FileResponse(path=str(artifact_path), media_type=media)


# ============================================================
# 5. DOCUMENT ANALYSIS
# ============================================================

@router.post(
    "/evidence/analyze-document/"
    "{evidence_id}"
)
async def analyze_uploaded_document(
    evidence_id: str,
):

    try:
        document_path = find_evidence_file(evidence_id)
        analysis_dir = get_analysis_dir(evidence_id)
        progress = ProgressBus.create(evidence_id)
        progress.emit("pipeline", "running")

        result, timing, from_cache = await asyncio.to_thread(
            run_document_analysis,
            document_path,
            analysis_dir,
            evidence_id,
            True,
            progress,
        )

        try:
            from backend.pipeline.report_manager import persist_analysis_payload, generate_reports

            persist_analysis_payload(evidence_id, result if isinstance(result, dict) else {"result": result}, kind="document")
            generate_reports(evidence_id, background=True)
            logger.info("document_report_queued | evidence_id=%s", evidence_id)
        except Exception as report_exc:
            logger.warning("document_report_queue_failed | evidence_id=%s | error=%s", evidence_id, report_exc)

        return safe_json_response({
            "success": True,
            "evidence_id": evidence_id,
            "job_id": evidence_id,
            "reports_pending": True,
            "report_status": "queued",
            "analysis": result,
            "timing": timing,
            "cached": from_cache,
        })

    except HTTPException:
        raise

    except DocumentAnalysisError as e:
        progress = ProgressBus.get(evidence_id)
        if progress:
            progress.fail(str(e))
        return _error_response(e, e.module, e.status_code)

    except FileNotFoundError as e:
        return _error_response(e, "document_analysis", 404)

    except Exception as e:
        return _error_response(e, "document_analysis")


# ============================================================
# 6. SIGNATURE VERIFICATION
# ============================================================

@router.post(
    "/evidence/verify-signature"
)
async def verify_signature_endpoint(

    reference: UploadFile = File(...),

    query: UploadFile = File(...),

):

    try:

        # -----------------------------------------
        # Validate files
        # -----------------------------------------

        if not reference.filename:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Reference signature "
                    "is required"
                ),
            )

        if not query.filename:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Query signature "
                    "is required"
                ),
            )

        # -----------------------------------------
        # Temporary directory
        # -----------------------------------------

        with tempfile.TemporaryDirectory() as temp_dir:

            temp_path = Path(
                temp_dir
            )

            reference_ext = Path(
                reference.filename
            ).suffix.lower()

            query_ext = Path(
                query.filename
            ).suffix.lower()

            reference_path = (
                temp_path
                / f"reference{reference_ext}"
            )

            query_path = (
                temp_path
                / f"query{query_ext}"
            )

            # -----------------------------------------
            # Save reference signature
            # -----------------------------------------

            with open(
                reference_path,
                "wb",
            ) as buffer:

                buffer.write(
                    await reference.read()
                )

            # -----------------------------------------
            # Save query signature
            # -----------------------------------------

            with open(
                query_path,
                "wb",
            ) as buffer:

                buffer.write(
                    await query.read()
                )

            # -----------------------------------------
            # Run signature verification
            # -----------------------------------------

            result = verify_signature(
                str(reference_path),
                str(query_path),
            )

            evidence_id = None
            try:
                import shutil
                from backend.core.evidence_manager import generate_evidence_id
                from backend.forensics.integration import on_evidence_uploaded
                from backend.pipeline.report_manager import persist_analysis_payload, generate_reports

                evidence_id = generate_evidence_id()
                dest = UPLOAD_DIR / f"{evidence_id}{query_ext}"
                shutil.copy2(query_path, dest)
                on_evidence_uploaded(
                    evidence_id,
                    dest,
                    original_filename=query.filename,
                    media_type="signature",
                )
                persist_analysis_payload(
                    evidence_id,
                    result if isinstance(result, dict) else {"result": result},
                    kind="signature",
                )
                generate_reports(evidence_id, background=True)
            except Exception as report_exc:
                logger.warning("signature_report_queue_failed | error=%s", report_exc)

            return safe_json_response(
                {
                    "success": True,
                    "evidence_id": evidence_id,
                    "analysis": result,
                    "result": result,
                    "reports_pending": True,
                    "report_status": "queued",
                }
            )

    except HTTPException:

        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                "Signature verification "
                "failed: "
                f"{str(e)}"
            ),
        )


# ============================================================
# 7. SIGNATURE VERIFICATION ALIAS
# ============================================================

@router.post(
    "/signature/verify"
)
async def verify_signature_api(

    reference: UploadFile = File(...),

    query: UploadFile = File(...),

):

    allowed_extensions = {
        ".png",
        ".jpg",
        ".jpeg",
    }

    # -----------------------------------------
    # Validate filenames
    # -----------------------------------------

    if not reference.filename:

        raise HTTPException(
            status_code=400,
            detail=(
                "Reference signature "
                "is required"
            ),
        )

    if not query.filename:

        raise HTTPException(
            status_code=400,
            detail=(
                "Query signature "
                "is required"
            ),
        )

    # -----------------------------------------
    # Validate extensions
    # -----------------------------------------

    reference_ext = Path(
        reference.filename
    ).suffix.lower()

    query_ext = Path(
        query.filename
    ).suffix.lower()

    if (
        reference_ext
        not in allowed_extensions
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Reference signature must be "
                "PNG, JPG, or JPEG"
            ),
        )

    if (
        query_ext
        not in allowed_extensions
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Query signature must be "
                "PNG, JPG, or JPEG"
            ),
        )

    # -----------------------------------------
    # Temporary signature directory
    # -----------------------------------------

    signature_dir = Path(
        "data/temp/signatures"
    )

    signature_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    reference_id = str(
        uuid.uuid4()
    )

    query_id = str(
        uuid.uuid4()
    )

    reference_path = (
        signature_dir
        / f"{reference_id}"
        f"{reference_ext}"
    )

    query_path = (
        signature_dir
        / f"{query_id}"
        f"{query_ext}"
    )

    try:

        # -----------------------------------------
        # Save reference
        # -----------------------------------------

        with open(
            reference_path,
            "wb",
        ) as buffer:

            while True:

                chunk = await reference.read(
                    1024 * 1024
                )

                if not chunk:

                    break

                buffer.write(
                    chunk
                )

        # -----------------------------------------
        # Save query
        # -----------------------------------------

        with open(
            query_path,
            "wb",
        ) as buffer:

            while True:

                chunk = await query.read(
                    1024 * 1024
                )

                if not chunk:

                    break

                buffer.write(
                    chunk
                )

        # -----------------------------------------
        # Run model
        # -----------------------------------------

        result = verify_signature(
            str(reference_path),
            str(query_path),
        )

        # -----------------------------------------
        # Return sanitized result
        # -----------------------------------------

        return safe_json_response(
            {
                "success": True,
                "analysis": {
                    "verdict":
                        result.get(
                            "verdict"
                        ),

                    "similarity":
                        result.get(
                            "similarity"
                        ),

                    "confidence":
                        result.get(
                            "confidence"
                        ),
                },
            }
        )

    except HTTPException:

        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                "Signature verification "
                "failed: "
                f"{str(e)}"
            ),
        )

    finally:

        # -----------------------------------------
        # Cleanup
        # -----------------------------------------

        reference_path.unlink(
            missing_ok=True
        )

        query_path.unlink(
            missing_ok=True
        )


# ============================================================
# 8. COPY-MOVE ANALYSIS
# ============================================================

@router.post(
    "/evidence/analyze-copy-move/"
    "{evidence_id}"
)
async def analyze_copy_move_endpoint(
    evidence_id: str,
):

    # -----------------------------------------
    # Find evidence
    # -----------------------------------------

    image_path = find_evidence_file(
        evidence_id
    )

    # -----------------------------------------
    # Get dedicated analysis directory
    # -----------------------------------------

    analysis_dir = get_analysis_dir(
        evidence_id
    )

    # -----------------------------------------
    # Run Copy-Move Detection
    # -----------------------------------------

    try:

        result = detect_copy_move(
            str(image_path),
            output_dir=analysis_dir,
        )

        # -----------------------------------------
        # Sanitize result
        # -----------------------------------------

        return safe_json_response(
            {
                "success": True,
                "evidence_id": evidence_id,
                "analysis": result,
            }
        )

    except HTTPException:

        raise

    except Exception as e:

        print(
            "\n========== COPY-MOVE ANALYSIS ERROR =========="
        )

        print(
            "Evidence ID:",
            evidence_id,
        )

        print(
            "Error:",
            repr(e),
        )

        print(
            "===============================================\n"
        )

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )
        