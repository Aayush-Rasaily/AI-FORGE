"""
Lightweight investigator attribution from request headers.

No full auth — uses X-Investigator-ID / X-Investigator-Name when present.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Request


@dataclass
class InvestigatorContext:
    user_id: str
    display_name: str
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None


def get_investigator(request: Optional[Request] = None) -> InvestigatorContext:
    if request is None:
        return InvestigatorContext(user_id="system", display_name="System")

    user_id = request.headers.get("X-Investigator-ID", "anonymous")
    display_name = request.headers.get("X-Investigator-Name", user_id)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    return InvestigatorContext(
        user_id=user_id,
        display_name=display_name,
        client_ip=client_ip,
        user_agent=user_agent,
    )
