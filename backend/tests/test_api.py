"""Integration tests for FastAPI API endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from src.db.models import Base
from src.db.queries import QueryManager
from src.main import app
from src.api import sessions, metrics, timeline


@pytest.fixture()
def client(db_engine, seeded_db):
    """TestClient backed by the seeded in-memory database."""
    factory = sessionmaker(db_engine, expire_on_commit=False)
    qm = QueryManager(factory)
    sessions.init_query_manager(qm)
    metrics.init_query_manager(qm)
    timeline.init_query_manager(qm)
    return TestClient(app)


# ── Health ─────────────────────────────────────────────────────────────


def test_health():
    with TestClient(app) as c:
        resp = c.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── Sessions ───────────────────────────────────────────────────────────


class TestSessionsAPI:
    def test_list_sessions(self, client):
        resp = client.get("/api/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert "sessions" in data
        assert data["total_count"] == 3
        assert len(data["sessions"]) == 3

    def test_list_sessions_filter_language(self, client):
        resp = client.get("/api/sessions?language=python")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 2

    def test_list_sessions_pagination(self, client):
        resp = client.get("/api/sessions?limit=1&offset=0")
        data = resp.json()
        assert len(data["sessions"]) == 1
        assert data["has_more"] is True

    def test_stats_summary(self, client):
        resp = client.get("/api/sessions/stats/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_sessions"] == 3
        assert data["total_interactions"] == 4
        assert "python" in data["languages"]

    def test_session_detail(self, client, seeded_db):
        s1_id = seeded_db["session_ids"][0]
        resp = client.get(f"/api/sessions/{s1_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session"]["id"] == s1_id
        assert len(data["session"]["interactions"]) == 2

    def test_session_detail_not_found(self, client):
        resp = client.get("/api/sessions/nonexistent")
        assert resp.status_code == 404


# ── Metrics ────────────────────────────────────────────────────────────


class TestMetricsAPI:
    def test_quality(self, client):
        resp = client.get("/api/metrics/quality")
        assert resp.status_code == 200
        data = resp.json()
        assert "metrics" in data
        assert len(data["metrics"]) == 3
        assert "average_quality_score" in data
        assert data["trend"] in ("improving", "declining", "stable")

    def test_errors(self, client):
        resp = client.get("/api/metrics/errors")
        assert resp.status_code == 200
        data = resp.json()
        assert "error_distribution" in data
        assert data["error_distribution"]["syntax"] == 1
        assert data["error_distribution"]["runtime"] == 1

    def test_acceptance(self, client):
        resp = client.get("/api/metrics/acceptance")
        assert resp.status_code == 200
        data = resp.json()
        assert data["acceptance_rate"] == 0.75
        assert "by_language" in data
        assert "trend" in data

    def test_acceptance_invalid_period(self, client):
        resp = client.get("/api/metrics/acceptance?time_period=invalid")
        assert resp.status_code == 422


# ── Timeline ───────────────────────────────────────────────────────────


class TestTimelineAPI:
    def test_session_timeline(self, client, seeded_db):
        s1_id = seeded_db["session_ids"][0]
        resp = client.get(f"/api/timeline/session/{s1_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["timeline"]) == 2

    def test_session_timeline_not_found(self, client):
        resp = client.get("/api/timeline/session/nonexistent")
        assert resp.status_code == 404

    def test_historical(self, client):
        resp = client.get("/api/timeline/historical")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["timeline"]) >= 1

    def test_historical_invalid_granularity(self, client):
        resp = client.get("/api/timeline/historical?granularity=century")
        assert resp.status_code == 422
