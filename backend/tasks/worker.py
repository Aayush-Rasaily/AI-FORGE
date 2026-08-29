"""
Background worker — processes Redis job queue.
Run: python -m backend.tasks.worker
"""

from __future__ import annotations

import logging
import signal
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("ai_forge.worker")

_running = True


def _handle_signal(*_):
    global _running
    _running = False
    logger.info("Worker shutdown requested")


def process_job(job: dict) -> None:
    from backend.tasks.queue import update_job_status

    job_id = job.get("job_id", "unknown")
    job_type = job.get("type", "")
    payload = job.get("payload") or {}

    try:
        if job_type == "analyze":
            evidence_id = payload.get("evidence_id")
            media_type = payload.get("media_type", "image")
            from backend.evidence.paths import find_evidence_file, get_analysis_dir

            if media_type == "image":
                image_path = find_evidence_file(evidence_id)
                if not image_path:
                    raise FileNotFoundError(f"Evidence not found: {evidence_id}")
                analysis_dir = get_analysis_dir(evidence_id)
                from backend.services.image_analysis_service import run_image_analysis
                run_image_analysis(
                    image_path,
                    analysis_dir,
                    evidence_id,
                    True,
                    None,
                    payload.get("deep_scan", True),
                    False,
                )
            elif media_type == "document":
                from backend.services.document_analysis_service import run_document_analysis
                doc_path = find_evidence_file(evidence_id)
                if not doc_path:
                    raise FileNotFoundError(f"Evidence not found: {evidence_id}")
                analysis_dir = get_analysis_dir(evidence_id)
                run_document_analysis(doc_path, analysis_dir, evidence_id)
            elif media_type == "video":
                from backend.services.video_service import analyze_video_parallel
                analyze_video_parallel(evidence_id)
            else:
                raise ValueError(f"Unknown media type: {media_type}")
            update_job_status(job_id, "completed", {"evidence_id": evidence_id, "success": True})
            logger.info("Job %s completed | %s", job_id, evidence_id)
            return

        if job_type == "report":
            from backend.pipeline.report_manager import generate_reports
            evidence_id = payload.get("evidence_id")
            generate_reports(evidence_id, background=False)
            update_job_status(job_id, "completed", {"evidence_id": evidence_id})
            return

        update_job_status(job_id, "failed", {"error": f"Unknown job type: {job_type}"})
    except Exception as exc:
        logger.exception("Job %s failed: %s", job_id, exc)
        update_job_status(job_id, "failed", {"error": str(exc)[:500]})


def main() -> None:
    from backend.database import init_db
    from backend.forensics.repository import init_forensic_db
    from backend.security.user_service import init_auth_db
    from backend.tasks.queue import dequeue_job

    init_db()
    init_forensic_db()
    init_auth_db()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    logger.info("AI-FORGE background worker started")

    while _running:
        job = dequeue_job(timeout=3)
        if job:
            process_job(job)
        else:
            time.sleep(0.5)

    logger.info("Worker stopped")


if __name__ == "__main__":
    main()
