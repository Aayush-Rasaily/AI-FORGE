"""
Case management service — enterprise investigations, audit, timeline, tasks.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from backend.cases.case_audit import (
    CASE_PRIORITIES,
    CASE_STATUSES,
    get_case_timeline,
    record_case_event,
)
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
from backend.forensics.repository import append_audit_log, get_audit_log

logger = logging.getLogger("ai_forge.cases")


def _init():
    from backend.cases.case_audit import _ensure_tables
    _ensure_tables()


def create_case(
    title: str,
    *,
    description: Optional[str] = None,
    organization: Optional[str] = None,
    department: Optional[str] = None,
    priority: str = "normal",
    owner_id: str = "anonymous",
    owner_name: str = "Anonymous",
    status: str = "open",
) -> Dict[str, Any]:
    _init()
    priority = priority if priority in CASE_PRIORITIES else "normal"
    status = status if status in CASE_STATUSES else "open"
    case_id = f"CASE-{uuid.uuid4().hex[:10].upper()}"
    session = get_session()
    try:
        inv = Investigation(
            id=case_id,
            title=title,
            description=description,
            organization=organization,
            department=department,
            status=status,
            priority=priority,
            lead_investigator_id=owner_id,
            lead_investigator_name=owner_name,
        )
        session.add(inv)
        session.commit()
        case = _case_dict(inv, evidence_count=0)
    finally:
        session.close()

    record_case_event(
        case_id, "case_created", f"Case created: {title}",
        actor_id=owner_id, actor_name=owner_name,
        details={"priority": priority, "status": status},
    )
    return case


def list_cases(*, limit: int = 50, status: Optional[str] = None) -> List[Dict[str, Any]]:
    _init()
    session = get_session()
    try:
        q = session.query(Investigation).order_by(Investigation.updated_at.desc())
        if status:
            q = q.filter_by(status=status)
        rows = q.limit(limit).all()
        return [_enriched_case_dict(session, inv) for inv in rows]
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

        base = _enriched_case_dict(session, inv)
        return {
            **base,
            "owner": base.get("owner"),
            "members": [_member_dict(m, session) for m in members],
            "comments": [_comment_dict(c) for c in comments],
            "folders": [_folder_dict(f) for f in folders],
            "assignments": [_assignment_dict(a) for a in assignments],
            "evidence": [_evidence_detail(session, e) for e in evidence],
            "timeline": get_case_timeline(investigation_id, limit=100),
            "audit_log": get_case_audit_log(investigation_id, limit=100),
        }
    finally:
        session.close()


def update_case_status(
    investigation_id: str,
    status: str,
    *,
    actor_id: str = "system",
    actor_name: str = "System",
) -> Optional[Dict[str, Any]]:
    if status not in CASE_STATUSES:
        raise ValueError(f"Invalid status. Allowed: {sorted(CASE_STATUSES)}")
    _init()
    session = get_session()
    try:
        inv = session.query(Investigation).filter_by(id=investigation_id).first()
        if not inv:
            return None
        old = inv.status
        inv.status = status
        inv.updated_at = datetime.now(timezone.utc)
        session.commit()
        case = _enriched_case_dict(session, inv)
    finally:
        session.close()

    record_case_event(
        investigation_id, "status_changed",
        f"Status changed: {old} → {status}",
        actor_id=actor_id, actor_name=actor_name,
        details={"from": old, "to": status},
    )
    return case


def update_case_priority(
    investigation_id: str,
    priority: str,
    *,
    actor_id: str = "system",
    actor_name: str = "System",
) -> Optional[Dict[str, Any]]:
    if priority not in CASE_PRIORITIES:
        raise ValueError(f"Invalid priority. Allowed: {sorted(CASE_PRIORITIES)}")
    _init()
    session = get_session()
    try:
        inv = session.query(Investigation).filter_by(id=investigation_id).first()
        if not inv:
            return None
        old = getattr(inv, "priority", None) or "normal"
        inv.priority = priority
        inv.updated_at = datetime.now(timezone.utc)
        session.commit()
        case = _enriched_case_dict(session, inv)
    finally:
        session.close()

    record_case_event(
        investigation_id, "priority_changed",
        f"Priority changed: {old} → {priority}",
        actor_id=actor_id, actor_name=actor_name,
        details={"from": old, "to": priority},
    )
    return case


def assign_investigator(
    investigation_id: str,
    investigator_id: str,
    *,
    investigator_name: Optional[str] = None,
    role: str = "lead",
    actor_id: str = "system",
    actor_name: str = "System",
) -> Dict[str, Any]:
    _init()
    session = get_session()
    try:
        inv = session.query(Investigation).filter_by(id=investigation_id).first()
        if not inv:
            raise ValueError("Case not found")

        reg = session.query(Investigator).filter_by(id=investigator_id).first()
        name = investigator_name or (reg.name if reg else investigator_id)

        if role == "lead":
            inv.lead_investigator_id = investigator_id
            inv.lead_investigator_name = name
            inv.updated_at = datetime.now(timezone.utc)

        existing = (
            session.query(CaseMember)
            .filter_by(investigation_id=investigation_id, investigator_id=investigator_id)
            .first()
        )
        if not existing:
            member = CaseMember(
                id=str(uuid.uuid4()),
                investigation_id=investigation_id,
                investigator_id=investigator_id,
                role=role,
            )
            session.add(member)
        session.commit()
        member_data = {
            "investigation_id": investigation_id,
            "investigator_id": investigator_id,
            "investigator_name": name,
            "role": role,
        }
    finally:
        session.close()

    record_case_event(
        investigation_id, "investigator_assigned",
        f"Investigator assigned: {name} ({role})",
        actor_id=actor_id, actor_name=actor_name,
        details=member_data,
    )
    return member_data


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


def add_case_member(
    investigation_id: str,
    investigator_id: str,
    role: str = "member",
    *,
    actor_id: str = "system",
    actor_name: str = "System",
) -> Dict[str, Any]:
    return assign_investigator(
        investigation_id, investigator_id, role=role,
        actor_id=actor_id, actor_name=actor_name,
    )


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
        result = _comment_dict(comment)
    finally:
        session.close()

    record_case_event(
        investigation_id, "comment_added",
        f"Comment by {author_name}",
        actor_id=author_id, actor_name=author_name,
        details={"preview": body[:200]},
    )
    return result


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
    actor_id: str = "system",
    actor_name: str = "System",
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
        inv = session.query(Investigation).filter_by(id=investigation_id).first()
        if inv:
            inv.updated_at = datetime.now(timezone.utc)
        session.commit()
        result = _assignment_dict(assignment)
    finally:
        session.close()

    record_case_event(
        investigation_id, "task_created",
        f"Task created: {title}",
        actor_id=actor_id, actor_name=actor_name,
        evidence_id=evidence_id,
        details={"assignee": assignee_name or assignee_id, "priority": priority},
    )
    return result


def update_assignment_status(
    assignment_id: str,
    status: str,
    *,
    actor_id: str = "system",
    actor_name: str = "System",
) -> Optional[Dict[str, Any]]:
    _init()
    session = get_session()
    try:
        a = session.query(CaseAssignment).filter_by(id=assignment_id).first()
        if not a:
            return None
        old = a.status
        a.status = status
        a.updated_at = datetime.now(timezone.utc)
        session.commit()
        result = _assignment_dict(a)
        case_id = a.investigation_id
        title = a.title
    finally:
        session.close()

    record_case_event(
        case_id, "task_updated",
        f"Task '{title}' status: {old} → {status}",
        actor_id=actor_id, actor_name=actor_name,
        details={"assignment_id": assignment_id, "from": old, "to": status},
    )
    return result


def link_evidence_to_case(
    evidence_id: str,
    investigation_id: str,
    *,
    folder_id: Optional[str] = None,
    actor_id: str = "system",
    actor_name: str = "System",
) -> bool:
    _init()
    session = get_session()
    try:
        rec = session.query(EvidenceRegistry).filter_by(evidence_id=evidence_id).first()
        if not rec:
            return False
        rec.investigation_id = investigation_id
        inv = session.query(Investigation).filter_by(id=investigation_id).first()
        if inv:
            inv.updated_at = datetime.now(timezone.utc)
            if inv.status == "open":
                inv.status = "investigating"
        session.commit()
        filename = rec.original_filename
    finally:
        session.close()

    record_case_event(
        investigation_id, "evidence_linked",
        f"Evidence linked: {filename}",
        actor_id=actor_id, actor_name=actor_name,
        evidence_id=evidence_id,
        details={"folder_id": folder_id},
    )
    try:
        from backend.graph.case_correlation import build_case_correlation
        build_case_correlation(investigation_id)
    except Exception as exc:
        logger.warning("Case correlation rebuild skipped: %s", exc)
    _refresh_case_verdict(investigation_id)
    return True


def on_evidence_uploaded_to_case(
    investigation_id: str,
    evidence_id: str,
    filename: str,
    *,
    actor_id: str = "system",
    actor_name: str = "System",
    media_type: str = "unknown",
) -> None:
    """Record upload in timeline and move case to investigating."""
    _init()
    session = get_session()
    try:
        inv = session.query(Investigation).filter_by(id=investigation_id).first()
        if inv and inv.status == "open":
            inv.status = "investigating"
            inv.updated_at = datetime.now(timezone.utc)
            session.commit()
    finally:
        session.close()

    record_case_event(
        investigation_id, "evidence_uploaded",
        f"Evidence uploaded: {filename}",
        actor_id=actor_id, actor_name=actor_name,
        evidence_id=evidence_id,
        details={"media_type": media_type, "filename": filename},
    )


def get_case_audit_log(investigation_id: str, *, limit: int = 100) -> List[Dict[str, Any]]:
    return get_audit_log(investigation_id=investigation_id, limit=limit)


def _refresh_case_verdict(investigation_id: str) -> None:
    verdict = _compute_case_verdict(investigation_id)
    if not verdict:
        return
    session = get_session()
    try:
        inv = session.query(Investigation).filter_by(id=investigation_id).first()
        if inv and inv.verdict != verdict:
            inv.verdict = verdict
            inv.updated_at = datetime.now(timezone.utc)
            session.commit()
    finally:
        session.close()


def _compute_case_verdict(investigation_id: str) -> Optional[str]:
    from backend.database.repository import AnalysisRecord

    session = get_session()
    try:
        evidence = session.query(EvidenceRegistry).filter_by(investigation_id=investigation_id).all()
        if not evidence:
            return None
        eids = [e.evidence_id for e in evidence]
        records = session.query(AnalysisRecord).filter(AnalysisRecord.evidence_id.in_(eids)).all()
        if not records:
            return "pending_analysis"
        verdicts = [r.verdict for r in records if r.verdict]
        if not verdicts:
            return "pending_analysis"
        risk_order = {"critical": 4, "high": 3, "medium": 2, "low": 1, "suspicious": 3, "tampered": 4}
        worst = max(verdicts, key=lambda v: risk_order.get(str(v).lower(), 0))
        return worst
    finally:
        session.close()


def _enriched_case_dict(session, inv: Investigation) -> Dict[str, Any]:
    evidence_count = session.query(EvidenceRegistry).filter_by(investigation_id=inv.id).count()
    verdict = inv.verdict or _compute_case_verdict(inv.id)
    return {
        **_case_dict(inv, evidence_count=evidence_count),
        "owner": {
            "id": inv.lead_investigator_id,
            "name": inv.lead_investigator_name,
        },
        "verdict": verdict,
        "evidence_count": evidence_count,
    }


def get_dashboard_stats() -> Dict[str, Any]:
    _init()
    session = get_session()
    try:
        from backend.database.repository import AnalysisRecord
        from sqlalchemy import func

        now = datetime.now(timezone.utc)
        total_cases = session.query(Investigation).count()
        open_cases = session.query(Investigation).filter(
            Investigation.status.in_(["open", "investigating", "pending"])
        ).count()
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

        # Evidence types
        evidence_by_type: Dict[str, int] = {}
        for media_type, count in (
            session.query(EvidenceRegistry.media_type, func.count())
            .group_by(EvidenceRegistry.media_type)
            .all()
        ):
            key = str(media_type or "unknown").lower()
            evidence_by_type[key] = int(count)

        # Monthly cases (last 6 months)
        six_months_ago = now - timedelta(days=183)
        monthly_map: Dict[str, Dict[str, int]] = defaultdict(lambda: {"cases": 0, "high_risk": 0})
        for inv in session.query(Investigation).filter(Investigation.created_at >= six_months_ago).all():
            if not inv.created_at:
                continue
            key = inv.created_at.strftime("%Y-%m")
            monthly_map[key]["cases"] += 1
        for rec in session.query(AnalysisRecord).filter(AnalysisRecord.created_at >= six_months_ago).all():
            if not rec.created_at:
                continue
            key = rec.created_at.strftime("%Y-%m")
            if (rec.risk_score or 0) >= 61:
                monthly_map[key]["high_risk"] += 1
        month_keys = sorted(monthly_map.keys())[-6:]
        monthly_cases = [
            {
                "month": m,
                "label": datetime.strptime(m, "%Y-%m").strftime("%b"),
                "cases": monthly_map[m]["cases"],
                "high_risk": monthly_map[m]["high_risk"],
            }
            for m in month_keys
        ]

        # Weekly timeline (last 7 days)
        day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        weekly_map: Dict[str, Dict[str, int]] = {}
        for i in range(6, -1, -1):
            d = (now - timedelta(days=i)).date()
            weekly_map[d.isoformat()] = {"cases": 0, "flagged": 0, "evidence": 0}

        week_start = now - timedelta(days=6)
        for inv in session.query(Investigation).filter(Investigation.created_at >= week_start).all():
            if inv.created_at:
                key = inv.created_at.date().isoformat()
                if key in weekly_map:
                    weekly_map[key]["cases"] += 1
        for rec in session.query(AnalysisRecord).filter(AnalysisRecord.created_at >= week_start).all():
            if rec.created_at:
                key = rec.created_at.date().isoformat()
                if key in weekly_map:
                    if (rec.risk_score or 0) >= 61:
                        weekly_map[key]["flagged"] += 1
        for ev in session.query(EvidenceRegistry).filter(EvidenceRegistry.intake_timestamp >= week_start).all():
            if ev.intake_timestamp:
                key = ev.intake_timestamp.date().isoformat()
                if key in weekly_map:
                    weekly_map[key]["evidence"] += 1

        weekly_timeline = []
        for i in range(6, -1, -1):
            d = (now - timedelta(days=i)).date()
            key = d.isoformat()
            weekly_timeline.append({
                "day": day_labels[d.weekday()],
                "date": key,
                **weekly_map.get(key, {"cases": 0, "flagged": 0, "evidence": 0}),
            })

        # Fraud categories from verdicts
        fraud_categories: Dict[str, int] = defaultdict(int)
        for (verdict,) in session.query(AnalysisRecord.verdict).all():
            v = str(verdict or "unclassified").lower()
            if any(k in v for k in ("tamper", "forgery", "fake", "manipul")):
                cat = "Tampering"
            elif any(k in v for k in ("suspicious", "elevated", "anomal")):
                cat = "Suspicious"
            elif any(k in v for k in ("authentic", "genuine", "clean", "legitimate")):
                cat = "Authentic"
            elif any(k in v for k in ("deepfake", "synthetic", "ai")):
                cat = "AI Generated"
            elif any(k in v for k in ("copy", "clone", "duplicate")):
                cat = "Copy-Move"
            else:
                cat = (verdict or "Unclassified").title()[:32]
            fraud_categories[cat] += 1

        # AI confidence distribution (proxy from risk or jury JSON)
        confidence_buckets = [
            {"label": "0–20%", "min": 0, "max": 20, "count": 0},
            {"label": "21–40%", "min": 21, "max": 40, "count": 0},
            {"label": "41–60%", "min": 41, "max": 60, "count": 0},
            {"label": "61–80%", "min": 61, "max": 80, "count": 0},
            {"label": "81–100%", "min": 81, "max": 100, "count": 0},
        ]
        for rec in session.query(AnalysisRecord).all():
            conf = None
            try:
                data = json.loads(rec.analysis_json or "{}")
                conf = data.get("confidence") or data.get("overall_confidence")
                if rec.jury_json:
                    jury = json.loads(rec.jury_json)
                    fusion = jury.get("fusion") or jury
                    conf = conf or fusion.get("confidence")
            except (json.JSONDecodeError, TypeError, AttributeError):
                pass
            if conf is None:
                conf = max(0.0, min(100.0, 100.0 - float(rec.risk_score or 0)))
            else:
                conf = float(conf)
                if conf <= 1.0:
                    conf *= 100.0
            for bucket in confidence_buckets:
                if bucket["min"] <= conf <= bucket["max"]:
                    bucket["count"] += 1
                    break

        # Average processing time
        processing_times: List[float] = []
        for (exec_json,) in session.query(AnalysisRecord.execution_times_json).filter(
            AnalysisRecord.execution_times_json.isnot(None)
        ).all():
            try:
                et = json.loads(exec_json or "{}")
                total_ms = et.get("total_ms")
                if total_ms is None:
                    total_ms = sum(
                        float(v) for v in et.values()
                        if isinstance(v, (int, float)) and v > 0
                    )
                if total_ms and total_ms > 0:
                    processing_times.append(float(total_ms))
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
        avg_processing_time_ms = round(sum(processing_times) / len(processing_times)) if processing_times else 0

        # Investigator activity
        inv_activity: Counter = Counter()
        for inv in session.query(Investigation).order_by(Investigation.updated_at.desc()).limit(50).all():
            name = inv.lead_investigator_name or "Unassigned"
            inv_activity[name] += 1
        for assign in session.query(CaseAssignment).filter_by(status="completed").limit(100).all():
            inv_activity[assign.assignee_name or "Unassigned"] += 1
        investigator_activity = [
            {"name": name, "cases": count}
            for name, count in inv_activity.most_common(8)
        ]

        # Activity heatmap: 7 days × 6 blocks (4-hour windows)
        heatmap = [[0 for _ in range(6)] for _ in range(7)]
        for rec in session.query(AnalysisRecord).filter(AnalysisRecord.created_at >= week_start).all():
            if not rec.created_at:
                continue
            days_ago = (now.date() - rec.created_at.date()).days
            if 0 <= days_ago <= 6:
                row = 6 - days_ago
                col = min(5, rec.created_at.hour // 4)
                heatmap[row][col] += 1

        return {
            "total_investigations": total_cases,
            "open_investigations": open_cases,
            "total_evidence": total_evidence,
            "total_analyses": total_analyses,
            "high_risk_cases": high_risk,
            "pending_assignments": pending_assignments,
            "active_investigators": investigators,
            "recent_cases": [_enriched_case_dict(session, c) for c in recent],
            "evidence_by_type": evidence_by_type,
            "monthly_cases": monthly_cases,
            "weekly_timeline": weekly_timeline,
            "fraud_categories": dict(fraud_categories),
            "confidence_distribution": [
                {"label": b["label"], "count": b["count"]} for b in confidence_buckets
            ],
            "avg_processing_time_ms": avg_processing_time_ms,
            "investigator_activity": investigator_activity,
            "activity_heatmap": heatmap,
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


def _case_dict(inv: Investigation, *, evidence_count: int = 0) -> Dict[str, Any]:
    return {
        "id": inv.id,
        "title": inv.title,
        "description": inv.description,
        "organization": getattr(inv, "organization", None),
        "department": getattr(inv, "department", None),
        "status": inv.status,
        "priority": getattr(inv, "priority", "normal"),
        "verdict": getattr(inv, "verdict", None),
        "lead_investigator_id": inv.lead_investigator_id,
        "lead_investigator_name": inv.lead_investigator_name,
        "owner_id": inv.lead_investigator_id,
        "owner_name": inv.lead_investigator_name,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
        "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
        "evidence_count": evidence_count,
    }


def _member_dict(m: CaseMember, session) -> Dict[str, Any]:
    inv = session.query(Investigator).filter_by(id=m.investigator_id).first()
    return {
        "id": m.id, "investigation_id": m.investigation_id,
        "investigator_id": m.investigator_id,
        "investigator_name": inv.name if inv else m.investigator_id,
        "role": m.role,
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


def _evidence_detail(session, e: EvidenceRegistry) -> Dict[str, Any]:
    from backend.database.repository import AnalysisRecord

    rec = session.query(AnalysisRecord).filter_by(evidence_id=e.evidence_id).first()
    return {
        "evidence_id": e.evidence_id,
        "filename": e.original_filename,
        "media_type": e.media_type,
        "sha256": e.sha256[:16] + "…",
        "size_bytes": e.size_bytes,
        "intake_timestamp": e.intake_timestamp.isoformat() if e.intake_timestamp else None,
        "verdict": rec.verdict if rec else None,
        "risk_score": rec.risk_score if rec else None,
        "status": e.status,
    }


def _evidence_brief(e: EvidenceRegistry) -> Dict[str, Any]:
    return {
        "evidence_id": e.evidence_id,
        "filename": e.original_filename,
        "media_type": e.media_type,
        "sha256": e.sha256[:16] + "…",
        "intake_timestamp": e.intake_timestamp.isoformat() if e.intake_timestamp else None,
    }


def export_case_bundle(investigation_id: str) -> str:
    """Generate a comprehensive ZIP bundle for the entire investigation."""
    import zipfile
    import tempfile
    from pathlib import Path

    _init()
    detail = get_case_detail(investigation_id)
    if not detail:
        raise ValueError("Case not found")

    temp_dir = Path(tempfile.mkdtemp())
    zip_path = temp_dir / f"Case_Bundle_{investigation_id}.zip"

    UPLOAD_DIR = Path("data/temp/uploads")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{investigation_id}/case_metadata.json", json.dumps(detail, indent=2))
        
        for ev in detail.get("evidence", []):
            ev_id = ev["evidence_id"]
            analysis_dir = UPLOAD_DIR / "analysis" / ev_id
            if analysis_dir.exists():
                for file in analysis_dir.rglob("*"):
                    if file.is_file():
                        arcname = f"{investigation_id}/evidence_{ev_id}/{file.relative_to(analysis_dir)}"
                        zf.write(file, arcname)
                        
            report_dir = UPLOAD_DIR / "reports" / ev_id
            if report_dir.exists():
                for file in report_dir.rglob("*"):
                    if file.is_file():
                        arcname = f"{investigation_id}/reports_{ev_id}/{file.name}"
                        zf.write(file, arcname)

    record_case_event(
        investigation_id, "case_exported",
        f"Exported case bundle ZIP for investigation {investigation_id}",
    )
    return str(zip_path)
