"""Tests for the monitor DatabaseManager."""

import os
import tempfile
from datetime import datetime, timezone, timedelta

import pytest

from src.db import DatabaseManager


@pytest.fixture()
def db():
    """DatabaseManager backed by a temporary SQLite file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        manager = DatabaseManager(db_path)
        yield manager
        manager.engine.dispose()


@pytest.fixture()
def session_id(db):
    """Create a session and return its ID."""
    return db.create_session(
        language="python",
        start_time=datetime.now(timezone.utc) - timedelta(hours=1),
        project_name="test-project",
        file_path="test.py",
    )


@pytest.fixture()
def interaction_id(db, session_id):
    """Create an interaction and return its ID."""
    return db.add_interaction(
        session_id=session_id,
        sequence_number=1,
        timestamp=datetime.now(timezone.utc) - timedelta(minutes=50),
        human_prompt="Write a function",
        claude_response="def hello(): print('hi')",
        was_accepted=True,
        was_modified=False,
        interaction_type="new_code",
        tokens_used=30,
    )


class TestCreateSession:
    def test_returns_uuid(self, db):
        sid = db.create_session(
            language="python",
            start_time=datetime.now(timezone.utc),
        )
        assert isinstance(sid, str)
        assert len(sid) == 36  # UUID format

    def test_default_status(self, db):
        sid = db.create_session(
            language="javascript",
            start_time=datetime.now(timezone.utc),
        )
        # Verify by ending the session (implicitly checks it was in_progress)
        db.end_session(
            sid,
            end_time=datetime.now(timezone.utc),
            acceptance_rate=1.0,
            status="completed",
        )


class TestEndSession:
    def test_sets_duration(self, db, session_id):
        now = datetime.now(timezone.utc)
        db.end_session(session_id, end_time=now, acceptance_rate=0.5, status="completed")
        # Session was created 1 hour ago, so duration should be ~3600s
        from sqlalchemy.orm import Session as SASession
        from src.db import SessionModel
        with SASession(db.engine) as s:
            row = s.get(SessionModel, session_id)
            assert row.duration_seconds is not None
            assert row.duration_seconds > 3500

    def test_nonexistent_session(self, db):
        # Should not raise
        db.end_session("nonexistent", datetime.now(timezone.utc), 0.0, "completed")


class TestAddInteraction:
    def test_returns_uuid(self, db, session_id):
        iid = db.add_interaction(
            session_id=session_id,
            sequence_number=1,
            timestamp=datetime.now(timezone.utc),
            human_prompt="test",
            claude_response="response",
            was_accepted=True,
            was_modified=False,
            interaction_type="new_code",
        )
        assert isinstance(iid, str)
        assert len(iid) == 36

    def test_response_length_calculated(self, db, session_id):
        response = "def hello(): pass"
        db.add_interaction(
            session_id=session_id,
            sequence_number=1,
            timestamp=datetime.now(timezone.utc),
            human_prompt="test",
            claude_response=response,
            was_accepted=True,
            was_modified=False,
            interaction_type="new_code",
        )
        interactions = db.get_session_interactions(session_id)
        assert interactions[0].response_length == len(response)


class TestGetSessionInteractions:
    def test_returns_ordered(self, db, session_id):
        now = datetime.now(timezone.utc)
        db.add_interaction(session_id, 2, now, "p2", "r2", True, False, "refactor")
        db.add_interaction(session_id, 1, now - timedelta(minutes=5), "p1", "r1", True, False, "new_code")
        interactions = db.get_session_interactions(session_id)
        assert len(interactions) == 2
        assert interactions[0].sequence_number == 1
        assert interactions[1].sequence_number == 2

    def test_empty_session(self, db, session_id):
        interactions = db.get_session_interactions(session_id)
        assert interactions == []


class TestGetNextSequenceNumber:
    def test_first_interaction(self, db, session_id):
        assert db.get_next_sequence_number(session_id) == 1

    def test_after_adding(self, db, session_id, interaction_id):
        assert db.get_next_sequence_number(session_id) == 2


class TestAddError:
    def test_returns_uuid(self, db, session_id, interaction_id):
        eid = db.add_error(
            interaction_id=interaction_id,
            session_id=session_id,
            error_type="syntax",
            error_message="SyntaxError: invalid syntax",
            language="python",
            severity="medium",
            timestamp=datetime.now(timezone.utc),
        )
        assert isinstance(eid, str)
        assert len(eid) == 36


class TestAddCodeMetrics:
    def test_returns_uuid(self, db, session_id, interaction_id):
        mid = db.add_code_metrics(
            interaction_id=interaction_id,
            language="python",
            cyclomatic_complexity=2.0,
            lines_of_code=10,
            function_count=1,
            code_quality_score=0.8,
        )
        assert isinstance(mid, str)
        assert len(mid) == 36
