"""
Case management service — investigators, folders, comments, assignments.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.database.repository import get_session, init_db
from backend.forensics.models import (
    CaseAssignment,
    CaseComment,
    CaseMember,
    EvidenceFolder,
    EvidenceRegistry,
    Investigation,
    Investigator,
)

logger = logging.getLogger("ai_forge.cases")


def _init():
    init_db()
    from backend.database.repository import Base, engine
    from backend.forensics import models as _  # noqa
    Base.metadata.create_all(bind=engine)


def register_investigator(
    name: str,
    *,
    email: Optional[str] = None,
    role: str = "investigator",
    department: Optional[str] = None,
) -> Dict[str, Any]:
    _init()
    inv_id = f"INV-{uuid.uuid4().hex[:10].upper()}"
    session = get_session()
    try:
        inv = Investigator(id=inv_id, name=name, email=email, role=role, department=department)
        session.add(inv)
        session.commit()
        return _inv_dict(inv)
    finally:
        session.close()


def list_investigators(active_only: bool = True) -> List[Dict[str, Any]]:
    _init()
    session = get_session()
    try:
        q = session.query(Investigator)
        if active_only:
            q = q.filter_by(active="true")
        return [_inv_dict(r) for r in q.order_by(Investigator.name).all()]
    finally:
        session.close()


def get_case_detail(investigation_id: str) -> Optional[Dict[str, Any]]:
    _init()
    session = get_session()
    try:
        inv = session.query(Investigation).filter_by(id=investigation_id).first()
        if not inv:
            return None

        members = session.query(CaseMember).filter_by(investigation_id=investigation_id).all()
        comments = (
            session.query(CaseComment)
            .filter_by(investigation_id=investigation_id)
            .order_by(CaseComment.created_at.desc())
            .limit(100)
            .all()
        )
        folders = session.query(EvidenceFolder).filter_by(investigation_id=investigation_id).all()
        assignments = session.query(CaseAssignment).filter_by(investigation_id=investigation_id).all()
        evidence = session.query(EvidenceRegistry).filter_by(investigation_id=investigation_id).all()

        return {
            **_case_dict(inv),
            "members": [_member_dict(m) for m in members],
            "comments": [_comment_dict(c) for c in comments],
            "folders": [_folder_dict(f) for f in folders],
            "assignments": [_assignment_dict(a) for a in assignments],
            "evidence": [_evidence_brief(e) for e in evidence],
            "evidence_count": len(evidence),
        }
    finally:
        session.close()


def add_case_member(
    investigation_id: str,
    investigator_id: str,
    role: str = "member",
) -> Dict[str, Any]:
    _init()
    session = get_session()
    try:
        member = CaseMember(
            id=str(uuid.uuid4()),
            investigation_id=investigation_id,
            investigator_id=investigator_id,
            role=role,
        )
        session.add(member)
        session.commit()
        return _member_dict(member)
    finally:
        session.close()


def add_comment(
    investigation_id: str,
    body: str,
    *,
    author_id: str = "anonymous",
    author_name: str = "Anonymous",
) -> Dict[str, Any]:
    _init()
    session = get_session()
    try:
        comment = CaseComment(
            id=str(uuid.uuid4()),
            investigation_id=investigation_id,
            author_id=author_id,
            author_name=author_name,
            body=body,
        )
        session.add(comment)
        inv = session.query(Investigation).filter_by(id=investigation_id).first()
        if inv:
            inv.updated_at = datetime.now(timezone.utc)
        session.commit()
        return _comment_dict(comment)
    finally:
        session.close()


def create_folder(
    investigation_id: str,
    name: str,
    *,
    parent_id: Optional[str] = None,
    created_by: Optional[str] = None,
) -> Dict[str, Any]:
    _init()
    session = get_session()
    try:
        folder = EvidenceFolder(
            id=f"FLD-{uuid.uuid4().hex[:10].upper()}",
            investigation_id=investigation_id,
            name=name,
            parent_id=parent_id,
            created_by=created_by,
        )
        session.add(folder)
        session.commit()
        return _folder_dict(folder)
    finally:
        session.close()


def create_assignment(
    investigation_id: str,
    title: str,
    assignee_id: str,
    *,
    assignee_name: Optional[str] = None,
    description: Optional[str] = None,
    priority: str = "normal",
    evidence_id: Optional[str] = None,
) -> Dict[str, Any]:
    _init()
    session = get_session()
    try:
        assignment = CaseAssignment(
            id=str(uuid.uuid4()),
            investigation_id=investigation_id,
            assignee_id=assignee_id,
            assignee_name=assignee_name,
            title=title,
            description=description,
            priority=priority,
            evidence_id=evidence_id,
        )
        session.add(assignment)
        session.commit()
        return _assignment_dict(assignment)
    finally:
        session.close()


def update_assignment_status(assignment_id: str, status: str) -> Optional[Dict[str, Any]]:
    _init()
    session = get_session()
    try:
        a = session.query(CaseAssignment).filter_by(id=assignment_id).first()
        if not a:
            return None
        a.status = status
        a.updated_at = datetime.now(timezone.utc)
        session.commit()
        return _assignment_dict(a)
    finally:
        session.close()


def link_evidence_to_case(evidence_id: str, investigation_id: str, folder_id: Optional[str] = None) -> bool:
    _init()
    session = get_session()
    try:
        rec = session.query(EvidenceRegistry).filter_by(evidence_id=evidence_id).first()
        if not rec:
            return False
        rec.investigation_id = investigation_id
        session.commit()
        return True
    finally:
        session.close()


def get_dashboard_stats() -> Dict[str, Any]:
    _init()
    session = get_session()
    try:
        from backend.database.repository import AnalysisRecord

        total_cases = session.query(Investigation).count()
        open_cases = session.query(Investigation).filter(Investigation.status == "open").count()
        total_evidence = session.query(EvidenceRegistry).count()
        total_analyses = session.query(AnalysisRecord).count()
        high_risk = session.query(AnalysisRecord).filter(AnalysisRecord.risk_score >= 61).count()
        pending_assignments = session.query(CaseAssignment).filter_by(status="pending").count()
        investigators = session.query(Investigator).filter_by(active="true").count()

        recent = (
            session.query(Investigation)
            .order_by(Investigation.updated_at.desc())
            .limit(8)
            .all()
        )

        return {
            "total_investigations": total_cases,
            "open_investigations": open_cases,
            "total_evidence": total_evidence,
            "total_analyses": total_analyses,
            "high_risk_cases": high_risk,
            "pending_assignments": pending_assignments,
            "active_investigators": investigators,
            "recent_cases": [_case_dict(c) for c in recent],
        }
    finally:
        session.close()


def _inv_dict(inv: Investigator) -> Dict[str, Any]:
    return {
        "id": inv.id, "name": inv.name, "email": inv.email,
        "role": inv.role, "department": inv.department,
        "active": inv.active == "true",
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
    }


def _case_dict(inv: Investigation) -> Dict[str, Any]:
    return {
        "id": inv.id, "title": inv.title, "description": inv.description,
        "status": inv.status,
        "lead_investigator_id": inv.lead_investigator_id,
        "lead_investigator_name": inv.lead_investigator_name,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
        "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
    }


def _member_dict(m: CaseMember) -> Dict[str, Any]:
    return {
        "id": m.id, "investigation_id": m.investigation_id,
        "investigator_id": m.investigator_id, "role": m.role,
        "assigned_at": m.assigned_at.isoformat() if m.assigned_at else None,
    }


def _comment_dict(c: CaseComment) -> Dict[str, Any]:
    return {
        "id": c.id, "investigation_id": c.investigation_id,
        "author_id": c.author_id, "author_name": c.author_name,
        "body": c.body,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def _folder_dict(f: EvidenceFolder) -> Dict[str, Any]:
    return {
        "id": f.id, "investigation_id": f.investigation_id,
        "name": f.name, "parent_id": f.parent_id,
        "created_by": f.created_by,
        "created_at": f.created_at.isoformat() if f.created_at else None,
    }


def _assignment_dict(a: CaseAssignment) -> Dict[str, Any]:
    return {
        "id": a.id, "investigation_id": a.investigation_id,
        "assignee_id": a.assignee_id, "assignee_name": a.assignee_name,
        "title": a.title, "description": a.description,
        "status": a.status, "priority": a.priority,
        "evidence_id": a.evidence_id,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }


def _evidence_brief(e: EvidenceRegistry) -> Dict[str, Any]:
    return {
        "evidence_id": e.evidence_id,
        "filename": e.original_filename,
        "media_type": e.media_type,
        "sha256": e.sha256[:16] + "…",
        "intake_timestamp": e.intake_timestamp.isoformat() if e.intake_timestamp else None,
    }
