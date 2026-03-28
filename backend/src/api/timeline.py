"""Timeline API endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..db.queries import QueryManager

router = APIRouter(tags=["timeline"])

_qm: Optional[QueryManager] = None

_VALID_GRANULARITIES = {"day", "week", "month"}


def init_query_manager(qm: QueryManager) -> None:
    global _qm
    _qm = qm


def _get_qm() -> QueryManager:
    if _qm is None:
        raise RuntimeError("QueryManager not initialized")
    return _qm


@router.get("/timeline/session/{session_id}")
def get_session_timeline(session_id: str):
    """Get interaction-by-interaction timeline for a specific session."""
    timeline = _get_qm().get_session_timeline(session_id)
    if not timeline:
        raise HTTPException(status_code=404, detail="Session not found or has no interactions")
    return {"timeline": timeline}


@router.get("/timeline/historical")
def get_historical_timeline(
    granularity: str = Query("day", description="day, week, or month"),
    language: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None, description="ISO format"),
    end_date: Optional[str] = Query(None, description="ISO format"),
):
    """Get historical timeline of sessions aggregated by day/week/month."""
    if granularity not in _VALID_GRANULARITIES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid granularity {granularity!r}. Must be one of: {sorted(_VALID_GRANULARITIES)}",
        )
    try:
        timeline = _get_qm().get_historical_timeline(
            granularity, language, start_date, end_date
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"timeline": timeline}
