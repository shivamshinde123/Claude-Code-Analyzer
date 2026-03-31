"""Session API endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..db.queries import QueryManager

router = APIRouter(tags=["sessions"])

# Initialized at startup via init_query_manager
_qm: Optional[QueryManager] = None


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


@router.get("/sessions")
def list_sessions(
    language: Optional[str] = Query(None, description="Filter by programming language"),
    status: Optional[str] = Query(None, description="Filter by status"),
    start_date: Optional[str] = Query(None, description="ISO format start date"),
    end_date: Optional[str] = Query(None, description="ISO format end date"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List all sessions with optional filtering and pagination."""
    filters = {
        "language": language,
        "status": status,
        "start_date": start_date,
        "end_date": end_date,
    }

    try:
        sessions, total_count = _get_qm().get_all_sessions(filters, limit, offset)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return {
        "sessions": sessions,
        "total_count": total_count,
        "has_more": offset + limit < total_count,
    }


@router.get("/sessions/stats/summary")
def get_session_stats_summary():
    """Get high-level statistics across all sessions."""
    return _get_qm().get_session_stats()


@router.get("/sessions/{session_id}")
def get_session_detail(session_id: str):
    """Get full details for a specific session, including interactions and errors."""
    result = _get_qm().get_session_detail(session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return result
