"""Session logger: subscribes to detector events and persists to database."""

import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from .db import DatabaseManager
from .utils import (
    classify_interaction,
    compute_code_metrics,
    estimate_tokens,
    extract_language,
)

logger = logging.getLogger(__name__)

# ── Error detection patterns ─────────────────────────────────────────────────
# Each entry: (regex_pattern, error_type, severity)
_ERROR_PATTERNS: List[Tuple[str, str, str]] = [
    # Python – syntax / import always "error"; runtime = "warning"
    (r"Traceback \(most recent call last\)", "Traceback", "warning"),
    (r"\bSyntaxError\b", "SyntaxError", "error"),
    (r"\bIndentationError\b", "IndentationError", "error"),
    (r"\bImportError\b", "ImportError", "error"),
    (r"\bModuleNotFoundError\b", "ModuleNotFoundError", "error"),
    (r"\bNameError\b", "NameError", "warning"),
    (r"\bTypeError\b", "TypeError", "warning"),
    (r"\bAttributeError\b", "AttributeError", "warning"),
    (r"\bValueError\b", "ValueError", "warning"),
    (r"\bKeyError\b", "KeyError", "warning"),
    (r"\bIndexError\b", "IndexError", "warning"),
    # JavaScript / TypeScript
    (r"\bReferenceError\b", "ReferenceError", "warning"),
    (r"Cannot read propert(?:y|ies) of", "TypeError", "warning"),  # JS: Cannot read property/properties of null/undefined
    (r"is not a function", "TypeError", "warning"),
    (r"is not defined", "ReferenceError", "warning"),
    # General
    (r"\bException\b", "Exception", "warning"),
    (r"\bFAILED\b", "TestFailure", "error"),
    (r"\bat <anonymous>", "StackFrame", "warning"),
]

_COMPILED_PATTERNS = [
    (re.compile(pattern, re.IGNORECASE), error_type, severity)
    for pattern, error_type, severity in _ERROR_PATTERNS
]


class SessionLogger:
    """Listens to detector events, computes metrics, and stores everything in the database."""

    def __init__(self, db: DatabaseManager):
        self._db = db
        self._current_session_id: Optional[str] = None
        self._current_language: str = "unknown"
        self._previous_response: Optional[str] = None

    # ── Event Handler ───────────────────────────────────────────────────

    def on_event(self, event_type: str, data: Dict) -> None:
        """Dispatch detector events to the appropriate handler."""
        if event_type == "session_started":
            self._handle_session_started(data)
        elif event_type == "interaction_detected":
            self._handle_interaction_detected(data)
        elif event_type == "session_ended":
            self._handle_session_ended(data)

    # ── Session lifecycle ───────────────────────────────────────────────

    def _handle_session_started(self, data: Dict) -> None:
        file_path = data.get("file_path", "")
        language = data.get("language") or extract_language(file_path)
        project_name = data.get("project_name")
        timestamp = self._to_datetime(data.get("timestamp"))

        session_id = self._db.create_session(
            language=language,
            start_time=timestamp,
            project_name=project_name,
            file_path=file_path,
        )
        self._current_session_id = session_id
        self._current_language = language
        self._previous_response = None
        logger.info("Session started: %s (%s)", session_id[:8], language)

    def _handle_interaction_detected(self, data: Dict) -> None:
        if self._current_session_id is None:
            logger.warning("Interaction detected but no active session.")
            return

        human_prompt = data.get("human_prompt", "")
        claude_response = data.get("claude_response", "")
        timestamp = self._to_datetime(data.get("timestamp"))
        tokens = data.get("tokens") or estimate_tokens(human_prompt + claude_response)

        # Allow the detector to supply a per-interaction language; fall back to
        # the session-level language set at session_started time.
        interaction_language = data.get("language") or self._current_language

        # Classify and detect modification
        interaction_type = classify_interaction(claude_response)
        was_modified = self._detect_modification(claude_response)

        seq = self._db.get_next_sequence_number(self._current_session_id)

        interaction_id = self._db.add_interaction(
            session_id=self._current_session_id,
            sequence_number=seq,
            timestamp=timestamp,
            human_prompt=human_prompt,
            claude_response=claude_response,
            was_accepted=True,
            was_modified=was_modified,
            interaction_type=interaction_type,
            tokens_used=tokens,
        )

        # Compute code metrics for supported languages
        if interaction_language in ("python", "javascript", "typescript"):
            metrics = compute_code_metrics(claude_response, interaction_language)
            self._db.add_code_metrics(
                interaction_id=interaction_id,
                language=interaction_language,
                **metrics,
            )

        self._previous_response = claude_response
        logger.info(
            "Interaction logged: seq=%d, type=%s", seq, interaction_type
        )

        # Detect and persist errors found in the conversation text
        errors = self._detect_errors(human_prompt, claude_response, interaction_language)
        for error_type, error_message, severity in errors:
            self._db.add_error(
                interaction_id=interaction_id,
                session_id=self._current_session_id,
                error_type=error_type,
                error_message=error_message,
                language=interaction_language,
                severity=severity,
                timestamp=timestamp,
            )
        if errors:
            logger.debug("Logged %d error(s) for interaction seq=%d", len(errors), seq)

    def _handle_session_ended(self, data: Dict) -> None:
        if self._current_session_id is None:
            return

        timestamp = self._to_datetime(data.get("timestamp"))
        acceptance_rate = self._calculate_acceptance_rate()
        reason = data.get("reason", "completed")
        status = "abandoned" if reason == "timeout" else "completed"

        self._db.end_session(
            session_id=self._current_session_id,
            end_time=timestamp,
            acceptance_rate=acceptance_rate,
            status=status,
        )

        logger.info(
            "Session ended: %s (%.0f%% acceptance, %s)",
            self._current_session_id[:8],
            acceptance_rate * 100,
            status,
        )
        self._current_session_id = None
        self._previous_response = None

    # ── Helpers ─────────────────────────────────────────────────────────

    def _detect_modification(self, claude_response: str) -> bool:
        if self._previous_response is None:
            return False
        return claude_response != self._previous_response

    def _calculate_acceptance_rate(self) -> float:
        if self._current_session_id is None:
            return 0.0
        interactions = self._db.get_session_interactions(self._current_session_id)
        if not interactions:
            return 0.0
        accepted = sum(1 for i in interactions if i.was_accepted)
        return accepted / len(interactions)

    @staticmethod
    def _detect_errors(
        human_prompt: str, claude_response: str, language: str
    ) -> List[Tuple[str, str, str]]:
        """Scan conversation text for error patterns.

        Returns a deduplicated list of (error_type, error_message, severity) tuples.
        """
        combined = f"{human_prompt}\n{claude_response}"
        seen_types: set = set()
        results: List[Tuple[str, str, str]] = []
        for regex, error_type, severity in _COMPILED_PATTERNS:
            if error_type in seen_types:
                continue
            match = regex.search(combined)
            if match:
                # Use the matched line as the error message (trim to 255 chars)
                line_start = combined.rfind("\n", 0, match.start()) + 1
                line_end = combined.find("\n", match.end())
                if line_end == -1:
                    line_end = len(combined)
                error_message = combined[line_start:line_end].strip()[:255]
                results.append((error_type, error_message, severity))
                seen_types.add(error_type)
        return results

    @staticmethod
    def _to_datetime(value) -> datetime:
        """Convert a timestamp (float epoch or datetime) to a datetime."""
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        return datetime.now(timezone.utc)
