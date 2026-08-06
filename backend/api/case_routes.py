"""
Case management API — investigators, folders, comments, assignments.
Extends existing /api/forensics/investigations without breaking compatibility.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from backend.cases.case_service import (
    add_case_member,
    add_comment,
    create_assignment,
    create_folder,
    get_case_detail,
    get_dashboard_stats,
    link_evidence_to_case,
    list_investigators,
    register_investigator,
    update_assignment_status,
)
from backend.forensics.repository import create_investigation, list_investigations
from backend.forensics.user_context import get_investigator

router = APIRouter(prefix="/api/cases", tags=["Case Management"])


class CreateCaseBody(BaseModel):
    title: str
    description: Optional[str] = None


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


class MemberBody(BaseModel):
    investigator_id: str
    role: str = "member"


@router.get("/investigators/list")
async def get_investigators():
    return {"success": True, "investigators": list_investigators()}


@router.post("/investigators")
async def post_investigator(body: InvestigatorBody):
    inv = register_investigator(body.name, email=body.email, role=body.role, department=body.department)
    return {"success": True, "investigator": inv}


@router.get("/dashboard/stats")
async def dashboard_stats():
    return {"success": True, "stats": get_dashboard_stats()}


@router.get("")
async def list_cases(limit: int = Query(50, ge=1, le=200)):
    return {"success": True, "cases": list_investigations(limit)}


@router.post("")
async def create_case(request: Request, body: CreateCaseBody):
    inv = get_investigator(request)
    case = create_investigation(
        body.title,
        description=body.description,
        lead_investigator_id=inv.user_id,
        lead_investigator_name=inv.display_name,
    )
    return {"success": True, "case": case}


@router.get("/{case_id}")
async def get_case(case_id: str):
    detail = get_case_detail(case_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"success": True, "case": detail}


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
async def post_assignment(case_id: str, body: AssignmentBody):
    assignment = create_assignment(
        case_id, body.title, body.assignee_id,
        assignee_name=body.assignee_name,
        description=body.description,
        priority=body.priority,
        evidence_id=body.evidence_id,
    )
    return {"success": True, "assignment": assignment}


@router.patch("/assignments/{assignment_id}")
async def patch_assignment(assignment_id: str, status: str = Query(...)):
    result = update_assignment_status(assignment_id, status)
    if not result:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return {"success": True, "assignment": result}


@router.post("/{case_id}/members")
async def post_member(case_id: str, body: MemberBody):
    member = add_case_member(case_id, body.investigator_id, body.role)
    return {"success": True, "member": member}


@router.post("/{case_id}/evidence/{evidence_id}")
async def attach_evidence(case_id: str, evidence_id: str):
    ok = link_evidence_to_case(evidence_id, case_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return {"success": True, "evidence_id": evidence_id, "case_id": case_id}
