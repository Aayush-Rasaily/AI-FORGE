"""
Case management API — investigators, folders, comments, assignments, audit.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backend.cases.case_audit import CASE_PRIORITIES, CASE_STATUSES
from backend.cases.case_service import (
    add_comment,
    assign_investigator,
    create_assignment,
    create_case,
    create_folder,
    get_case_audit_log,
    get_case_detail,
    get_dashboard_stats,
    link_evidence_to_case,
    list_cases,
    list_investigators,
    register_investigator,
    update_assignment_status,
    update_case_priority,
    update_case_status,
)
from backend.cases.case_audit import get_case_timeline
from backend.forensics.user_context import get_investigator

router = APIRouter(prefix="/api/cases", tags=["Case Management"])


class CreateCaseBody(BaseModel):
    title: str
    description: Optional[str] = None
    organization: Optional[str] = None
    department: Optional[str] = None
    priority: str = "normal"


class UpdateStatusBody(BaseModel):
    status: str = Field(..., description=f"One of: {', '.join(sorted(CASE_STATUSES))}")


class UpdatePriorityBody(BaseModel):
    priority: str = Field(..., description=f"One of: {', '.join(sorted(CASE_PRIORITIES))}")


class CommentBody(BaseModel):
    body: str


class FolderBody(BaseModel):
    name: str
    parent_id: Optional[str] = None


class AssignmentBody(BaseModel):
    title: str
    assignee_id: str
    assignee_name: Optional[str] = None
    description: Optional[str] = None
    priority: str = "normal"
    evidence_id: Optional[str] = None


class InvestigatorBody(BaseModel):
    name: str
    email: Optional[str] = None
    role: str = "investigator"
    department: Optional[str] = None


class AssignInvestigatorBody(BaseModel):
    investigator_id: str
    investigator_name: Optional[str] = None
    role: str = "lead"


class MemberBody(BaseModel):
    investigator_id: str
    role: str = "member"


@router.get("/meta")
async def case_meta():
    return {
        "success": True,
        "statuses": sorted(CASE_STATUSES),
        "priorities": sorted(CASE_PRIORITIES),
    }


@router.get("/investigators/list")
async def get_investigators():
    return {"success": True, "investigators": list_investigators()}


@router.post("/investigators")
async def post_investigator(body: InvestigatorBody):
    inv = register_investigator(body.name, email=body.email, role=body.role, department=body.department)
    return {"success": True, "investigator": inv}


@router.get("/dashboard/stats")
async def dashboard_stats():
    try:
        return {"success": True, "stats": get_dashboard_stats()}
    except Exception as exc:
        return {
            "success": True,
            "stats": {
                "total_investigations": 0,
                "open_investigations": 0,
                "high_risk_cases": 0,
                "total_evidence": 0,
                "total_analyses": 0,
                "pending_assignments": 0,
                "recent_cases": [],
                "warning": str(exc)[:200],
            },
        }


@router.get("")
async def get_cases(
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
):
    return {"success": True, "cases": list_cases(limit=limit, status=status)}


@router.post("")
async def post_case(request: Request, body: CreateCaseBody):
    inv = get_investigator(request)
    case = create_case(
        body.title,
        description=body.description,
        organization=body.organization,
        department=body.department,
        priority=body.priority,
        owner_id=inv.user_id,
        owner_name=inv.display_name,
    )
    return {"success": True, "case": case}


@router.get("/{case_id}")
async def get_case(case_id: str):
    detail = get_case_detail(case_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"success": True, "case": detail}


@router.patch("/{case_id}/status")
async def patch_case_status(case_id: str, request: Request, body: UpdateStatusBody):
    inv = get_investigator(request)
    try:
        case = update_case_status(
            case_id, body.status,
            actor_id=inv.user_id, actor_name=inv.display_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"success": True, "case": case}


@router.patch("/{case_id}/priority")
async def patch_case_priority(case_id: str, request: Request, body: UpdatePriorityBody):
    inv = get_investigator(request)
    try:
        case = update_case_priority(
            case_id, body.priority,
            actor_id=inv.user_id, actor_name=inv.display_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"success": True, "case": case}


@router.post("/{case_id}/assign")
async def post_assign_investigator(case_id: str, request: Request, body: AssignInvestigatorBody):
    inv = get_investigator(request)
    detail = get_case_detail(case_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Case not found")
    member = assign_investigator(
        case_id, body.investigator_id,
        investigator_name=body.investigator_name,
        role=body.role,
        actor_id=inv.user_id, actor_name=inv.display_name,
    )
    return {"success": True, "assignment": member}


@router.get("/{case_id}/timeline")
async def case_timeline(case_id: str, limit: int = Query(100, ge=1, le=500)):
    detail = get_case_detail(case_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"success": True, "timeline": get_case_timeline(case_id, limit=limit)}


@router.get("/{case_id}/audit")
async def case_audit(case_id: str, limit: int = Query(100, ge=1, le=500)):
    detail = get_case_detail(case_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"success": True, "audit": get_case_audit_log(case_id, limit=limit)}


@router.post("/{case_id}/comments")
async def post_comment(case_id: str, request: Request, body: CommentBody):
    inv = get_investigator(request)
    comment = add_comment(case_id, body.body, author_id=inv.user_id, author_name=inv.display_name)
    return {"success": True, "comment": comment}


@router.post("/{case_id}/folders")
async def post_folder(case_id: str, request: Request, body: FolderBody):
    inv = get_investigator(request)
    folder = create_folder(case_id, body.name, parent_id=body.parent_id, created_by=inv.user_id)
    return {"success": True, "folder": folder}


@router.post("/{case_id}/assignments")
async def post_assignment(case_id: str, request: Request, body: AssignmentBody):
    inv = get_investigator(request)
    assignment = create_assignment(
        case_id, body.title, body.assignee_id,
        assignee_name=body.assignee_name,
        description=body.description,
        priority=body.priority,
        evidence_id=body.evidence_id,
        actor_id=inv.user_id,
        actor_name=inv.display_name,
    )
    return {"success": True, "assignment": assignment}


@router.patch("/assignments/{assignment_id}")
async def patch_assignment(assignment_id: str, request: Request, status: str = Query(...)):
    inv = get_investigator(request)
    result = update_assignment_status(
        assignment_id, status,
        actor_id=inv.user_id, actor_name=inv.display_name,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return {"success": True, "assignment": result}


@router.post("/{case_id}/members")
async def post_member(case_id: str, request: Request, body: MemberBody):
    inv = get_investigator(request)
    member = assign_investigator(
        case_id, body.investigator_id, role=body.role,
        actor_id=inv.user_id, actor_name=inv.display_name,
    )
    return {"success": True, "member": member}


@router.post("/{case_id}/evidence/{evidence_id}")
async def attach_evidence(case_id: str, evidence_id: str, request: Request):
    inv = get_investigator(request)
    ok = link_evidence_to_case(
        evidence_id, case_id,
        actor_id=inv.user_id, actor_name=inv.display_name,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return {"success": True, "evidence_id": evidence_id, "case_id": case_id}


@router.get("/{case_id}/graph")
async def case_graph(
    case_id: str,
    focus_evidence_id: Optional[str] = None,
    rebuild: bool = Query(False),
):
    from backend.graph.case_correlation import get_case_graph

    detail = get_case_detail(case_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Case not found")
    graph = get_case_graph(case_id, focus_evidence_id=focus_evidence_id, rebuild=rebuild)
    return {"success": True, "graph": graph}


@router.get("/{case_id}/correlation")
async def case_correlation(case_id: str, rebuild: bool = Query(False)):
    from backend.graph.case_correlation import get_case_correlation

    detail = get_case_detail(case_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Case not found")
    result = get_case_correlation(case_id, rebuild=rebuild)
    return {"success": True, "correlation": result}


@router.post("/{case_id}/graph/rebuild")
async def rebuild_case_graph(case_id: str):
    from backend.graph.case_correlation import build_case_correlation

    detail = get_case_detail(case_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Case not found")
    graph = build_case_correlation(case_id)
    return {"success": True, "graph": graph}


@router.get("/{case_id}/export")
async def export_case(case_id: str):
    from fastapi.responses import FileResponse
    from backend.cases.case_service import export_case_bundle

    detail = get_case_detail(case_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Case not found")
        
    try:
        zip_path = export_case_bundle(case_id)
        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename=f"Case_Bundle_{case_id}.zip"
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
