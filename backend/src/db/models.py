"""SQLAlchemy ORM models for the backend service.

These mirror the monitor service models exactly so both services
can read/write the same SQLite database consistently.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    ForeignKey,
    create_engine,
    event,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    relationship,
    sessionmaker,
)


def _utcnow() -> datetime:
    """Return the current UTC datetime (used as a column default)."""
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    """Generate a new random UUID string (used as a primary-key default)."""
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    """Declarative base shared by all ORM models in the backend service."""


class SessionModel(Base):
    """ORM model for a Claude Code session, mirroring the monitor service model.

    Read-only from the backend's perspective; rows are written by the monitor.
    """

    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=_new_uuid)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    language = Column(String, nullable=False)
    project_name = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    total_tokens_used = Column(Integer, nullable=True)
    acceptance_rate = Column(Float, nullable=True)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    interactions = relationship("InteractionModel", back_populates="session")
    errors = relationship("ErrorModel", back_populates="session")

    __table_args__ = (
        Index("idx_sessions_start_time", "start_time"),
        Index("idx_sessions_language", "language"),
        Index("idx_sessions_status", "status"),
    )


class InteractionModel(Base):
    """ORM model for a single human→Claude exchange within a session."""

    __tablename__ = "interactions"

    id = Column(String, primary_key=True, default=_new_uuid)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    sequence_number = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    human_prompt = Column(Text, nullable=False)
    claude_response = Column(Text, nullable=False)
    response_length = Column(Integer, nullable=True)
    was_accepted = Column(Boolean, nullable=False)
    was_modified = Column(Boolean, nullable=False)
    modification_count = Column(Integer, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    interaction_type = Column(String, nullable=False)
    created_at = Column(DateTime, default=_utcnow)

    session = relationship("SessionModel", back_populates="interactions")
    errors = relationship("ErrorModel", back_populates="interaction")
    metrics = relationship("CodeMetricsModel", back_populates="interaction")

    __table_args__ = (
        Index("idx_interactions_session_id", "session_id"),
        Index("idx_interactions_timestamp", "timestamp"),
        Index("idx_interactions_type", "interaction_type"),
    )


class ErrorModel(Base):
    """ORM model for an error pattern detected inside a conversation turn."""

    __tablename__ = "errors"

    id = Column(String, primary_key=True, default=_new_uuid)
    interaction_id = Column(String, ForeignKey("interactions.id"), nullable=False)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    error_type = Column(String, nullable=False)
    error_message = Column(Text, nullable=False)
    language = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    was_resolved_in_next_interaction = Column(Boolean, nullable=True)
    recovery_interactions_count = Column(Integer, nullable=True)
    timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=_utcnow)

    interaction = relationship("InteractionModel", back_populates="errors")
    session = relationship("SessionModel", back_populates="errors")

    __table_args__ = (
        Index("idx_errors_session_id", "session_id"),
        Index("idx_errors_interaction_id", "interaction_id"),
        Index("idx_errors_type", "error_type"),
    )


class CodeMetricsModel(Base):
    """ORM model for static-analysis metrics derived from a code response."""

    __tablename__ = "code_metrics"

    id = Column(String, primary_key=True, default=_new_uuid)
    interaction_id = Column(String, ForeignKey("interactions.id"), nullable=False)
    cyclomatic_complexity = Column(Float, nullable=True)
    lines_of_code = Column(Integer, nullable=True)
    function_count = Column(Integer, nullable=True)
    class_count = Column(Integer, nullable=True)
    max_nesting_depth = Column(Integer, nullable=True)
    has_type_hints = Column(Boolean, nullable=True)
    code_quality_score = Column(Float, nullable=True)
    language = Column(String, nullable=False)
    created_at = Column(DateTime, default=_utcnow)

    interaction = relationship("InteractionModel", back_populates="metrics")

    __table_args__ = (
        Index("idx_code_metrics_interaction_id", "interaction_id"),
    )


def get_engine(db_path: str):
    """Create a SQLAlchemy engine with SQLite foreign key support."""
    engine = create_engine(f"sqlite:///{db_path}", echo=False)

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def get_session_factory(db_path: str, engine=None):
    """Create a sessionmaker bound to the database at db_path.

    If an existing engine is provided it will be reused, otherwise a new one
    is created.  Passing the engine avoids creating a second connection pool
    when the caller already has one (e.g., for schema migration in main.py).
    """
    if engine is None:
        engine = get_engine(db_path)
    return sessionmaker(engine, expire_on_commit=False)
