"""
Forensic integrity database models — append-only custody and audit tables.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text

from backend.database.repository import Base


class Investigation(Base):
    __tablename__ = "investigations"

    id = Column(String(64), primary_key=True)
    title = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(32), default="open")
    lead_investigator_id = Column(String(128), nullable=True)
    lead_investigator_name = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class EvidenceRegistry(Base):
    __tablename__ = "evidence_registry"

    evidence_id = Column(String(64), primary_key=True)
    investigation_id = Column(String(64), index=True, nullable=True)
    original_filename = Column(String(512), nullable=False)
    stored_path = Column(String(1024), nullable=False)
    media_type = Column(String(32), nullable=False)
    size_bytes = Column(Integer, default=0)
    sha256 = Column(String(64), index=True, nullable=False)
    sha512 = Column(String(128), index=True, nullable=False)
    intake_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    intake_user_id = Column(String(128), nullable=True)
    intake_user_name = Column(String(256), nullable=True)
    status = Column(String(32), default="active")


class CustodyEvent(Base):
    """Append-only chain of custody — hash-linked events."""

    __tablename__ = "custody_events"

    id = Column(String(64), primary_key=True)
    evidence_id = Column(String(64), index=True, nullable=False)
    investigation_id = Column(String(64), index=True, nullable=True)
    event_type = Column(String(64), nullable=False)
    event_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    actor_id = Column(String(128), nullable=False)
    actor_name = Column(String(256), nullable=True)
    action_description = Column(Text, nullable=False)
    location = Column(String(256), nullable=True)
    sha256_at_event = Column(String(64), nullable=False)
    sha512_at_event = Column(String(128), nullable=False)
    previous_event_hash = Column(String(64), nullable=True)
    event_hash = Column(String(64), nullable=False, index=True)
    metadata_json = Column(Text, nullable=True)


class AuditLogEntry(Base):
    """Append-only audit trail — all forensic operations."""

    __tablename__ = "audit_log"

    id = Column(String(64), primary_key=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    user_id = Column(String(128), nullable=False, index=True)
    user_name = Column(String(256), nullable=True)
    action = Column(String(128), nullable=False, index=True)
    resource_type = Column(String(64), nullable=True)
    resource_id = Column(String(64), nullable=True, index=True)
    evidence_id = Column(String(64), nullable=True, index=True)
    investigation_id = Column(String(64), nullable=True, index=True)
    client_ip = Column(String(64), nullable=True)
    details_json = Column(Text, nullable=True)
    success = Column(String(8), default="true")


class ReportSnapshot(Base):
    """Immutable signed report snapshots — write-once."""

    __tablename__ = "report_snapshots"

    id = Column(String(64), primary_key=True)
    evidence_id = Column(String(64), index=True, nullable=False)
    investigation_id = Column(String(64), index=True, nullable=True)
    report_type = Column(String(64), nullable=False)
    version = Column(Integer, default=1)
    content_sha256 = Column(String(64), nullable=False)
    content_sha512 = Column(String(128), nullable=False)
    signature = Column(String(128), nullable=False)
    signature_algorithm = Column(String(32), default="HMAC-SHA512")
    manifest_hash = Column(String(64), nullable=True)
    file_path = Column(String(1024), nullable=False)
    sealed_by_id = Column(String(128), nullable=True)
    sealed_by_name = Column(String(256), nullable=True)
    sealed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    immutable = Column(String(8), default="true")


class Investigator(Base):
    """Registered forensic investigators."""

    __tablename__ = "investigators"

    id = Column(String(64), primary_key=True)
    name = Column(String(256), nullable=False)
    email = Column(String(256), nullable=True, index=True)
    role = Column(String(64), default="investigator")
    department = Column(String(128), nullable=True)
    active = Column(String(8), default="true")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class CaseMember(Base):
    """Investigators assigned to a case."""

    __tablename__ = "case_members"

    id = Column(String(64), primary_key=True)
    investigation_id = Column(String(64), index=True, nullable=False)
    investigator_id = Column(String(64), index=True, nullable=False)
    role = Column(String(64), default="member")
    assigned_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class CaseComment(Base):
    """Threaded comments on investigations."""

    __tablename__ = "case_comments"

    id = Column(String(64), primary_key=True)
    investigation_id = Column(String(64), index=True, nullable=False)
    author_id = Column(String(128), nullable=False)
    author_name = Column(String(256), nullable=True)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class EvidenceFolder(Base):
    """Organize evidence within a case."""

    __tablename__ = "evidence_folders"

    id = Column(String(64), primary_key=True)
    investigation_id = Column(String(64), index=True, nullable=False)
    name = Column(String(256), nullable=False)
    parent_id = Column(String(64), nullable=True)
    created_by = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class CaseAssignment(Base):
    """Task assignments within a case."""

    __tablename__ = "case_assignments"

    id = Column(String(64), primary_key=True)
    investigation_id = Column(String(64), index=True, nullable=False)
    assignee_id = Column(String(128), nullable=False)
    assignee_name = Column(String(256), nullable=True)
    title = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(32), default="pending")
    priority = Column(String(16), default="normal")
    evidence_id = Column(String(64), nullable=True)
    due_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
