"""Tests for QueryManager database queries."""

import pytest


class TestGetAllSessions:
    def test_returns_all(self, query_manager, seeded_db):
        sessions, total = query_manager.get_all_sessions({})
        assert total == 3
        assert len(sessions) == 3

    def test_filter_by_language(self, query_manager, seeded_db):
        sessions, total = query_manager.get_all_sessions({"language": "python"})
        assert total == 2
        assert all(s["language"] == "python" for s in sessions)

    def test_filter_by_status(self, query_manager, seeded_db):
        sessions, total = query_manager.get_all_sessions({"status": "completed"})
        assert total == 2
        assert all(s["status"] == "completed" for s in sessions)

    def test_pagination(self, query_manager, seeded_db):
        sessions, total = query_manager.get_all_sessions({}, limit=2, offset=0)
        assert len(sessions) == 2
        assert total == 3

        sessions2, _ = query_manager.get_all_sessions({}, limit=2, offset=2)
        assert len(sessions2) == 1

    def test_interaction_and_error_counts(self, query_manager, seeded_db):
        sessions, _ = query_manager.get_all_sessions({})
        # Find the python session with 2 interactions (s1)
        s1 = next(s for s in sessions if s["interaction_count"] == 2)
        assert s1["error_count"] == 1

    def test_invalid_date_raises(self, query_manager, seeded_db):
        with pytest.raises(ValueError, match="Invalid start_date"):
            query_manager.get_all_sessions({"start_date": "not-a-date"})


class TestGetSessionDetail:
    def test_existing_session(self, query_manager, seeded_db):
        s1_id = seeded_db["session_ids"][0]
        result = query_manager.get_session_detail(s1_id)
        assert result is not None
        assert result["session"]["id"] == s1_id
        assert len(result["session"]["interactions"]) == 2
        assert len(result["session"]["errors"]) == 1
        assert result["summary"]["total_interactions"] == 2

    def test_nonexistent_session(self, query_manager, seeded_db):
        result = query_manager.get_session_detail("nonexistent-id")
        assert result is None


class TestGetSessionStats:
    def test_stats(self, query_manager, seeded_db):
        stats = query_manager.get_session_stats()
        assert stats["total_sessions"] == 3
        assert stats["total_interactions"] == 4
        assert stats["languages"]["python"] == 2
        assert stats["languages"]["javascript"] == 1
        assert stats["session_statuses"]["completed"] == 2
        assert stats["session_statuses"]["in_progress"] == 1


class TestGetQualityMetrics:
    def test_all_metrics(self, query_manager, seeded_db):
        metrics = query_manager.get_quality_metrics()
        assert len(metrics) == 3

    def test_filter_by_session(self, query_manager, seeded_db):
        s1_id = seeded_db["session_ids"][0]
        metrics = query_manager.get_quality_metrics(session_id=s1_id)
        assert len(metrics) == 2
        assert all(m["language"] == "python" for m in metrics)


class TestGetErrorAnalysis:
    def test_all_errors(self, query_manager, seeded_db):
        errors = query_manager.get_error_analysis()
        assert len(errors) == 2

    def test_filter_by_type(self, query_manager, seeded_db):
        errors = query_manager.get_error_analysis(error_type="syntax")
        assert len(errors) == 1
        assert errors[0]["error_type"] == "syntax"

    def test_filter_by_language(self, query_manager, seeded_db):
        errors = query_manager.get_error_analysis(language="javascript")
        assert len(errors) == 1
        assert errors[0]["language"] == "javascript"


class TestGetAcceptanceMetrics:
    def test_overall_rate(self, query_manager, seeded_db):
        result = query_manager.get_acceptance_metrics()
        # 3 accepted out of 4 = 0.75
        assert result["overall"] == 0.75

    def test_by_language(self, query_manager, seeded_db):
        result = query_manager.get_acceptance_metrics()
        # python: 2/3 accepted (i1=True, i2=False, i4=True)
        assert result["by_language"]["python"] == pytest.approx(2 / 3, abs=0.01)
        # javascript: 1/1 accepted
        assert result["by_language"]["javascript"] == 1.0

    def test_filter_by_language(self, query_manager, seeded_db):
        result = query_manager.get_acceptance_metrics(language="javascript")
        assert result["overall"] == 1.0
        assert "python" not in result["by_language"]


class TestGetSessionTimeline:
    def test_timeline(self, query_manager, seeded_db):
        s1_id = seeded_db["session_ids"][0]
        timeline = query_manager.get_session_timeline(s1_id)
        assert len(timeline) == 2
        assert timeline[0]["sequence_number"] == 1
        assert timeline[1]["sequence_number"] == 2
        assert timeline[1]["error_count"] == 1

    def test_empty_timeline(self, query_manager, seeded_db):
        timeline = query_manager.get_session_timeline("nonexistent-id")
        assert timeline == []


class TestGetHistoricalTimeline:
    def test_daily(self, query_manager, seeded_db):
        timeline = query_manager.get_historical_timeline(granularity="day")
        assert len(timeline) >= 1
        point = timeline[0]
        assert "date" in point
        assert "session_count" in point
        assert "avg_duration" in point
        assert "avg_acceptance_rate" in point
        assert "error_count" in point

    def test_filter_by_language(self, query_manager, seeded_db):
        timeline = query_manager.get_historical_timeline(language="javascript")
        total_sessions = sum(p["session_count"] for p in timeline)
        assert total_sessions == 1
