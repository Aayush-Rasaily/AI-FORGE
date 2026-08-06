"""
Prometheus metrics for enterprise monitoring.
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Response

logger = logging.getLogger("ai_forge.metrics")

router = APIRouter(tags=["Monitoring"])

_start_time = time.time()
_request_count = 0
_analysis_count = 0


def increment_analysis():
    global _analysis_count
    _analysis_count += 1


@router.get("/metrics")
async def prometheus_metrics():
    uptime = time.time() - _start_time
    lines = [
        "# HELP aiforge_up AI-FORGE service availability",
        "# TYPE aiforge_up gauge",
        "aiforge_up 1",
        "# HELP aiforge_uptime_seconds Service uptime",
        "# TYPE aiforge_uptime_seconds gauge",
        f"aiforge_uptime_seconds {uptime:.1f}",
        "# HELP aiforge_analyses_total Total analyses run",
        "# TYPE aiforge_analyses_total counter",
        f"aiforge_analyses_total {_analysis_count}",
    ]
    try:
        from backend.cases.case_service import get_dashboard_stats
        stats = get_dashboard_stats()
        lines += [
            "# HELP aiforge_investigations_total Total investigations",
            "# TYPE aiforge_investigations_total gauge",
            f"aiforge_investigations_total {stats.get('total_investigations', 0)}",
            "# HELP aiforge_evidence_total Total evidence items",
            "# TYPE aiforge_evidence_total gauge",
            f"aiforge_evidence_total {stats.get('total_evidence', 0)}",
            "# HELP aiforge_high_risk_total High risk analyses",
            "# TYPE aiforge_high_risk_total gauge",
            f"aiforge_high_risk_total {stats.get('high_risk_cases', 0)}",
        ]
    except Exception:
        pass

    return Response(content="\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")
