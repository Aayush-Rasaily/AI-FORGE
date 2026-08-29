"""
Role-Based Access Control — Investigator, Admin, Supervisor, Auditor.
"""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet, Iterable, Set


class Role(str, Enum):
    INVESTIGATOR = "investigator"
    ADMIN = "admin"
    SUPERVISOR = "supervisor"
    AUDITOR = "auditor"


# Permission strings
PERM_UPLOAD = "evidence:upload"
PERM_ANALYZE = "evidence:analyze"
PERM_CASE_READ = "case:read"
PERM_CASE_WRITE = "case:write"
PERM_CASE_ASSIGN = "case:assign"
PERM_REPORT_EXPORT = "report:export"
PERM_AUDIT_READ = "audit:read"
PERM_ADMIN = "admin:all"
PERM_LEARNING = "learning:manage"
PERM_USER_MANAGE = "user:manage"


_ROLE_PERMISSIONS: dict[Role, FrozenSet[str]] = {
    Role.ADMIN: frozenset({
        PERM_UPLOAD, PERM_ANALYZE, PERM_CASE_READ, PERM_CASE_WRITE,
        PERM_CASE_ASSIGN, PERM_REPORT_EXPORT, PERM_AUDIT_READ,
        PERM_ADMIN, PERM_LEARNING, PERM_USER_MANAGE,
    }),
    Role.SUPERVISOR: frozenset({
        PERM_UPLOAD, PERM_ANALYZE, PERM_CASE_READ, PERM_CASE_WRITE,
        PERM_CASE_ASSIGN, PERM_REPORT_EXPORT, PERM_AUDIT_READ, PERM_LEARNING,
    }),
    Role.INVESTIGATOR: frozenset({
        PERM_UPLOAD, PERM_ANALYZE, PERM_CASE_READ, PERM_CASE_WRITE,
        PERM_REPORT_EXPORT,
    }),
    Role.AUDITOR: frozenset({
        PERM_CASE_READ, PERM_REPORT_EXPORT, PERM_AUDIT_READ,
    }),
}


def normalize_role(role: str) -> Role:
    r = str(role or "investigator").lower().strip()
    for member in Role:
        if member.value == r:
            return member
    return Role.INVESTIGATOR


def permissions_for(role: str) -> Set[str]:
    return set(_ROLE_PERMISSIONS.get(normalize_role(role), _ROLE_PERMISSIONS[Role.INVESTIGATOR]))


def has_permission(role: str, permission: str) -> bool:
    perms = permissions_for(role)
    return permission in perms or PERM_ADMIN in perms


def has_any_permission(role: str, required: Iterable[str]) -> bool:
    return any(has_permission(role, p) for p in required)


def has_all_permissions(role: str, required: Iterable[str]) -> bool:
    return all(has_permission(role, p) for p in required)
