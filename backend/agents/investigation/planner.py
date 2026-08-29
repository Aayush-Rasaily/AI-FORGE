"""
Planner Agent — detects evidence type and builds a dynamic investigation plan.
Skips unnecessary modules to reduce execution time.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import cv2

from backend.agents.investigation.base import AgentResult, InvestigationPlan
from backend.utils.module_registry import (
    classify_image_profile,
    get_file_category,
    likely_contains_text,
    modules_for_document,
    modules_for_image,
    modules_for_video,
)

logger = logging.getLogger("ai_forge.agents.planner")


def _has_face(image_path: Path) -> bool:
    try:
        img = cv2.imread(str(image_path))
        if img is None:
            return False
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        faces = cascade.detectMultiScale(gray, 1.2, 4, minSize=(40, 40))
        return len(faces) > 0
    except Exception:
        return False


def _has_audio_hint(path: Path) -> bool:
    # Lightweight: assume common containers may have audio; skip only for mute extensions
    return path.suffix.lower() not in {".gif"}


def build_investigation_plan(
    evidence_id: str,
    evidence_path: Path,
    *,
    force_deep: bool = False,
) -> InvestigationPlan:
    evidence_path = Path(evidence_path)
    category = get_file_category(evidence_path)
    skip_reasons: Dict[str, str] = {}
    modules: Set[str] = set()
    agents: List[str] = ["planner", "metadata", "reasoning", "judge", "report"]
    profile = category
    estimated = 8.0

    if category == "image":
        profile = classify_image_profile(str(evidence_path))
        ocr_ok = likely_contains_text(str(evidence_path))
        modules = modules_for_image(evidence_path, ocr_applicable=ocr_ok, profile=profile)
        agents.insert(1, "image")

        if ocr_ok or profile in ("scanned_document", "text_document"):
            modules.update({"ocr", "layout", "font"})
            # OCR/layout run inside image pipeline — no separate Document Agent for images
        else:
            skip_reasons["ocr"] = "No text bands detected — skip OCR/layout"
            skip_reasons["document"] = "Natural photo profile — skip document agent"

        face = _has_face(evidence_path)
        if face or force_deep:
            modules.add("deepfake")
            modules.add("face_forensics")
        else:
            modules.discard("deepfake")
            skip_reasons["deepfake"] = "No face detected — skip DeepFake"
            if not force_deep:
                modules.discard("face_forensics")
                skip_reasons["face_forensics"] = "No face detected — skip face forensics"

        estimated = 12.0 if force_deep else (9.0 if ocr_ok else 6.0)

    elif category == "document":
        modules = modules_for_document(evidence_path)
        agents.insert(1, "document")
        agents.insert(2, "image")  # page renders may need image forensics
        # Signature only if force_deep (signature crop unknown at plan time)
        if force_deep:
            agents.insert(3, "signature")
            modules.add("signature")
        else:
            skip_reasons["signature"] = "No signature region declared — skip Signature Agent"
        estimated = 18.0

    elif category == "video":
        modules = modules_for_video()
        agents.insert(1, "video")
        if _has_audio_hint(evidence_path):
            modules.add("audio")
        else:
            skip_reasons["audio"] = "No audio track expected — skip Audio Analysis"
        modules.add("deepfake")
        estimated = 25.0

    else:
        modules = {"metadata", "hash"}
        skip_reasons["forensics"] = f"Unsupported category '{category}' — metadata only"
        estimated = 3.0

    priorities = [a for a in agents if a not in ("reasoning", "judge", "report")]
    priorities += ["reasoning", "judge", "report"]

    return InvestigationPlan(
        evidence_id=evidence_id,
        evidence_type=category,
        profile=profile,
        modules=sorted(modules),
        agents=agents,
        skip_reasons=skip_reasons,
        priorities=priorities,
        estimated_seconds=estimated,
    )


def run_planner_agent(
    evidence_id: str,
    evidence_path: Path,
    *,
    force_deep: bool = False,
) -> AgentResult:
    t0 = time.perf_counter()
    plan = build_investigation_plan(evidence_id, evidence_path, force_deep=force_deep)
    duration = (time.perf_counter() - t0) * 1000
    findings = [
        f"Evidence type: {plan.evidence_type}",
        f"Profile: {plan.profile}",
        f"Modules selected: {len(plan.modules)}",
        f"Agents: {', '.join(plan.agents)}",
    ]
    for mod, reason in plan.skip_reasons.items():
        findings.append(f"Skip {mod}: {reason}")

    logger.info(
        "Planner | evidence=%s type=%s modules=%s skipped=%s",
        evidence_id,
        plan.evidence_type,
        plan.modules,
        list(plan.skip_reasons.keys()),
    )

    return AgentResult(
        agent_id="planner",
        agent_name="Planner Agent",
        status="completed",
        confidence=0.95,
        risk_score=0.0,
        verdict="PLANNED",
        findings=findings,
        skipped_modules=list(plan.skip_reasons.keys()),
        executed_modules=["plan"],
        data={"plan": plan.to_dict()},
        duration_ms=duration,
        reason="Dynamic investigation plan created from evidence profile.",
    )
