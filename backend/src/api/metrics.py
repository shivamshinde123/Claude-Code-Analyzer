"""Metrics API endpoints."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..db.queries import QueryManager
from ..utils.aggregations import (
    compute_rolling_average,
    detect_error_patterns,
    detect_trend,
)

router = APIRouter(tags=["metrics"])

_qm: Optional[QueryManager] = None

_VALID_TIME_PERIODS = {"all_time", "last_7_days", "last_30_days", "last_60_days", "last_90_days"}

_PERIOD_DAYS = {
    "last_7_days": 7,
    "last_30_days": 30,
    "last_60_days": 60,
    "last_90_days": 90,
}


def init_query_manager(qm: QueryManager) -> None:
    """Wire the shared :class:`QueryManager` into this router module.

    Called once at application startup from ``main.py`` so all endpoint
    handlers share the same database session factory.
    """
    global _qm
    _qm = qm


def _get_qm() -> QueryManager:
    """Return the module-level QueryManager, raising if not yet initialised."""
    if _qm is None:
        raise RuntimeError("QueryManager not initialized")
    return _qm


def _period_start_date(time_period: str) -> Optional[str]:
    """Return an ISO-format start datetime for the given time_period, or None for all_time."""
    days = _PERIOD_DAYS.get(time_period)
    if days is None:
        return None
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


@router.get("/metrics/quality")
def get_quality_metrics(
    session_id: Optional[str] = Query(None, description="Filter to a specific session"),
    time_period: str = Query("all_time", description="last_7_days, last_30_days, last_60_days, last_90_days, or all_time"),
):
    """Get code quality metrics over time."""
    if time_period not in _VALID_TIME_PERIODS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid time_period {time_period!r}. Must be one of: {sorted(_VALID_TIME_PERIODS)}",
        )
    start_date = _period_start_date(time_period)
    metrics = _get_qm().get_quality_metrics(session_id, start_date)

    scores = [
        m["code_quality_score"]
        for m in metrics
        if m.get("code_quality_score") is not None
    ]
    avg_score = round(sum(scores) / len(scores), 4) if scores else 0.0
    trend = detect_trend(scores)

    return {
        "metrics": metrics,
        "average_quality_score": avg_score,
        "trend": trend,
    }


@router.get("/metrics/errors")
def get_error_metrics(
    session_id: Optional[str] = Query(None),
    error_type: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    time_period: str = Query("all_time", description="last_7_days, last_30_days, last_60_days, last_90_days, or all_time"),
):
    """Analyze errors across sessions."""
    if time_period not in _VALID_TIME_PERIODS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid time_period {time_period!r}. Must be one of: {sorted(_VALID_TIME_PERIODS)}",
        )
    start_date = _period_start_date(time_period)
    errors = _get_qm().get_error_analysis(session_id, error_type, language, start_date)
    patterns = detect_error_patterns(errors)

    return {
        "error_distribution": patterns["distribution"],
        "most_common_error": patterns["most_common"],
        "average_recovery_iterations": patterns["avg_recovery"],
        "recovery_rate": patterns["recovery_rate"],
    }


@router.get("/metrics/acceptance")
def get_acceptance_metrics(
    language: Optional[str] = Query(None),
    time_period: str = Query("all_time", description="last_7_days, last_30_days, last_60_days, last_90_days, or all_time"),
):
    """Analyze acceptance rates with breakdowns by language and type."""
    if time_period not in _VALID_TIME_PERIODS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid time_period {time_period!r}. Must be one of: {sorted(_VALID_TIME_PERIODS)}",
        )
    data = _get_qm().get_acceptance_metrics(language, time_period)

    trend_data = data.get("daily_rates", [])
    smoothed = compute_rolling_average(trend_data, window=7)

    return {
        "acceptance_rate": data["overall"],
        "by_language": data["by_language"],
        "by_interaction_type": data["by_interaction_type"],
        "trend": [
            {"timestamp": ts, "value": val} for ts, val in smoothed
        ],
    }
