"""Database models and CRUD operations for Claude Code Analyzer."""

import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

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
    func,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    relationship,
    sessionmaker,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


# ── ORM Models ──────────────────────────────────────────────────────────────


class Base(DeclarativeBase):
    pass


class SessionModel(Base):
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


# ── Database Manager ────────────────────────────────────────────────────────


class DatabaseManager:
    """Handles all database CRUD operations."""

    def __init__(self, db_path: str):
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)

        # Enable SQLite foreign key enforcement on every connection
        @event.listens_for(self.engine, "connect")
        def _set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.create_all(self.engine)
        self._session_factory = sessionmaker(self.engine, expire_on_commit=False)

    # ── Session CRUD ────────────────────────────────────────────────────

    def create_session(
        self,
        language: str,
        start_time: datetime,
        status: str = "in_progress",
        project_name: Optional[str] = None,
        file_path: Optional[str] = None,
    ) -> str:
        """Create a new session record. Returns the session ID."""
        session_model = SessionModel(
            language=language,
            start_time=start_time,
            status=status,
            project_name=project_name,
            file_path=file_path,
        )
        with self._session_factory() as db:
            db.add(session_model)
            db.commit()
            return session_model.id

    def end_session(
        self,
        session_id: str,
        end_time: datetime,
        acceptance_rate: float,
        status: str = "completed",
    ) -> None:
        """Finalize a session with end time, acceptance rate, and status."""
        with self._session_factory() as db:
            session = db.get(SessionModel, session_id)
            if session is None:
                return
            session.end_time = end_time
            # Strip timezone info for consistent subtraction (SQLite stores naive)
            end_naive = end_time.replace(tzinfo=None) if end_time.tzinfo else end_time
            start_naive = session.start_time.replace(tzinfo=None) if session.start_time.tzinfo else session.start_time
            session.duration_seconds = int(
                (end_naive - start_naive).total_seconds()
            )
            session.acceptance_rate = acceptance_rate
            session.status = status

            # Sum tokens across interactions
            total_tokens = (
                db.query(func.sum(InteractionModel.tokens_used))
                .filter(InteractionModel.session_id == session_id)
                .scalar()
            )
            session.total_tokens_used = total_tokens
            db.commit()

    # ── Interaction CRUD ────────────────────────────────────────────────

    def add_interaction(
        self,
        session_id: str,
        sequence_number: int,
        timestamp: datetime,
        human_prompt: str,
        claude_response: str,
        was_accepted: bool,
        was_modified: bool,
        interaction_type: str,
        modification_count: Optional[int] = None,
        tokens_used: Optional[int] = None,
    ) -> str:
        """Add an interaction to a session. Returns the interaction ID."""
        interaction = InteractionModel(
            session_id=session_id,
            sequence_number=sequence_number,
            timestamp=timestamp,
            human_prompt=human_prompt,
            claude_response=claude_response,
            response_length=len(claude_response),
            was_accepted=was_accepted,
            was_modified=was_modified,
            modification_count=modification_count,
            tokens_used=tokens_used,
            interaction_type=interaction_type,
        )
        with self._session_factory() as db:
            db.add(interaction)
            db.commit()
            return interaction.id

    def get_session_interactions(self, session_id: str) -> List[InteractionModel]:
        """Return all interactions for a session, ordered by sequence number."""
        with self._session_factory() as db:
            return (
                db.query(InteractionModel)
                .filter(InteractionModel.session_id == session_id)
                .order_by(InteractionModel.sequence_number)
                .all()
            )

    def get_next_sequence_number(self, session_id: str) -> int:
        """Return the next sequence number for a session."""
        with self._session_factory() as db:
            max_seq = (
                db.query(func.max(InteractionModel.sequence_number))
                .filter(InteractionModel.session_id == session_id)
                .scalar()
            )
            return (max_seq or 0) + 1

    # ── Error CRUD ──────────────────────────────────────────────────────

    def add_error(
        self,
        interaction_id: str,
        session_id: str,
        error_type: str,
        error_message: str,
        language: str,
        severity: str,
        timestamp: datetime,
        was_resolved_in_next_interaction: Optional[bool] = None,
        recovery_interactions_count: Optional[int] = None,
    ) -> str:
        """Add an error record. Returns the error ID."""
        error = ErrorModel(
            interaction_id=interaction_id,
            session_id=session_id,
            error_type=error_type,
            error_message=error_message,
            language=language,
            severity=severity,
            timestamp=timestamp,
            was_resolved_in_next_interaction=was_resolved_in_next_interaction,
            recovery_interactions_count=recovery_interactions_count,
        )
        with self._session_factory() as db:
            db.add(error)
            db.commit()
            return error.id

    # ── Code Metrics CRUD ───────────────────────────────────────────────

    def add_code_metrics(
        self,
        interaction_id: str,
        language: str,
        cyclomatic_complexity: Optional[float] = None,
        lines_of_code: Optional[int] = None,
        function_count: Optional[int] = None,
        class_count: Optional[int] = None,
        max_nesting_depth: Optional[int] = None,
        has_type_hints: Optional[bool] = None,
        code_quality_score: Optional[float] = None,
    ) -> str:
        """Add code metrics for an interaction. Returns the metrics ID."""
        metrics = CodeMetricsModel(
            interaction_id=interaction_id,
            language=language,
            cyclomatic_complexity=cyclomatic_complexity,
            lines_of_code=lines_of_code,
            function_count=function_count,
            class_count=class_count,
            max_nesting_depth=max_nesting_depth,
            has_type_hints=has_type_hints,
            code_quality_score=code_quality_score,
        )
        with self._session_factory() as db:
            db.add(metrics)
            db.commit()
            return metrics.id
