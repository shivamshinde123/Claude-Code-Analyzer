"""Shared fixtures for backend tests."""

import uuid
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.db.models import (
    Base,
    SessionModel,
    InteractionModel,
    ErrorModel,
    CodeMetricsModel,
)
from src.db.queries import QueryManager


def _utcnow():
    return datetime.now(timezone.utc)


@pytest.fixture()
def db_engine():
    """In-memory SQLite engine with foreign keys enabled."""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return engine


@pytest.fixture()
def db_session(db_engine):
    """SQLAlchemy session for direct data insertion in tests."""
    Session = sessionmaker(db_engine, expire_on_commit=False)
    with Session() as session:
        yield session


@pytest.fixture()
def query_manager(db_engine):
    """QueryManager wired to the in-memory database."""
    factory = sessionmaker(db_engine, expire_on_commit=False)
    return QueryManager(factory)


@pytest.fixture()
def seeded_db(db_session):
    """Populate the in-memory DB with realistic test data.

    Creates:
    - 3 sessions (2 python, 1 javascript)
    - 4 interactions across sessions
    - 2 errors
    - 3 code_metrics records
    """
    now = _utcnow()

    # ── Sessions ──
    s1_id = str(uuid.uuid4())
    s2_id = str(uuid.uuid4())
    s3_id = str(uuid.uuid4())

    s1 = SessionModel(
        id=s1_id,
        start_time=now - timedelta(hours=2),
        end_time=now - timedelta(hours=1, minutes=30),
        duration_seconds=1800,
        language="python",
        project_name="analytics",
        file_path="analytics/main.py",
        total_tokens_used=500,
        acceptance_rate=0.75,
        status="completed",
    )
    s2 = SessionModel(
        id=s2_id,
        start_time=now - timedelta(hours=1),
        end_time=now - timedelta(minutes=30),
        duration_seconds=1800,
        language="javascript",
        project_name="frontend",
        file_path="frontend/App.jsx",
        total_tokens_used=300,
        acceptance_rate=1.0,
        status="completed",
    )
    s3 = SessionModel(
        id=s3_id,
        start_time=now - timedelta(minutes=10),
        end_time=None,
        duration_seconds=None,
        language="python",
        project_name="analytics",
        file_path="analytics/utils.py",
        total_tokens_used=None,
        acceptance_rate=None,
        status="in_progress",
    )
    db_session.add_all([s1, s2, s3])
    db_session.flush()

    # ── Interactions ──
    i1_id = str(uuid.uuid4())
    i2_id = str(uuid.uuid4())
    i3_id = str(uuid.uuid4())
    i4_id = str(uuid.uuid4())

    interactions = [
        InteractionModel(
            id=i1_id, session_id=s1_id, sequence_number=1,
            timestamp=now - timedelta(hours=2),
            human_prompt="Write a hello function",
            claude_response="def hello(): print('hello')",
            response_length=28, was_accepted=True, was_modified=False,
            tokens_used=50, interaction_type="new_code",
        ),
        InteractionModel(
            id=i2_id, session_id=s1_id, sequence_number=2,
            timestamp=now - timedelta(hours=1, minutes=45),
            human_prompt="Add type hints",
            claude_response="def hello() -> None: print('hello')",
            response_length=35, was_accepted=False, was_modified=True,
            modification_count=2, tokens_used=60, interaction_type="refactor",
        ),
        InteractionModel(
            id=i3_id, session_id=s2_id, sequence_number=1,
            timestamp=now - timedelta(hours=1),
            human_prompt="Create a React component",
            claude_response="function App() { return <div>Hello</div> }",
            response_length=44, was_accepted=True, was_modified=False,
            tokens_used=80, interaction_type="new_code",
        ),
        InteractionModel(
            id=i4_id, session_id=s3_id, sequence_number=1,
            timestamp=now - timedelta(minutes=10),
            human_prompt="Fix the bug",
            claude_response="if x is not None: return x",
            response_length=26, was_accepted=True, was_modified=False,
            tokens_used=40, interaction_type="bugfix",
        ),
    ]
    db_session.add_all(interactions)
    db_session.flush()

    # ── Errors ──
    errors = [
        ErrorModel(
            id=str(uuid.uuid4()), interaction_id=i2_id, session_id=s1_id,
            error_type="syntax", error_message="SyntaxError: invalid syntax",
            language="python", severity="medium",
            was_resolved_in_next_interaction=True, recovery_interactions_count=1,
            timestamp=now - timedelta(hours=1, minutes=44),
        ),
        ErrorModel(
            id=str(uuid.uuid4()), interaction_id=i3_id, session_id=s2_id,
            error_type="runtime", error_message="TypeError: undefined is not a function",
            language="javascript", severity="high",
            was_resolved_in_next_interaction=False, recovery_interactions_count=3,
            timestamp=now - timedelta(minutes=55),
        ),
    ]
    db_session.add_all(errors)
    db_session.flush()

    # ── Code Metrics ──
    metrics = [
        CodeMetricsModel(
            id=str(uuid.uuid4()), interaction_id=i1_id,
            cyclomatic_complexity=1.0, lines_of_code=2,
            function_count=1, class_count=0, max_nesting_depth=0,
            has_type_hints=False, code_quality_score=0.76, language="python",
        ),
        CodeMetricsModel(
            id=str(uuid.uuid4()), interaction_id=i2_id,
            cyclomatic_complexity=1.0, lines_of_code=2,
            function_count=1, class_count=0, max_nesting_depth=0,
            has_type_hints=True, code_quality_score=0.96, language="python",
        ),
        CodeMetricsModel(
            id=str(uuid.uuid4()), interaction_id=i3_id,
            cyclomatic_complexity=2.0, lines_of_code=1,
            function_count=1, class_count=0, max_nesting_depth=0,
            has_type_hints=False, code_quality_score=0.72, language="javascript",
        ),
    ]
    db_session.add_all(metrics)
    db_session.commit()

    return {
        "session_ids": [s1_id, s2_id, s3_id],
        "interaction_ids": [i1_id, i2_id, i3_id, i4_id],
    }
