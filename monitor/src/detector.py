"""File system monitoring to detect Claude Code sessions."""

import logging
import os
import platform
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

from .reader import ConversationFileReader
from .utils import detect_language_from_code, detect_project_language

logger = logging.getLogger(__name__)

# Default session timeout: 5 minutes of inactivity
DEFAULT_TIMEOUT_SECONDS = 300


def _default_watch_paths() -> List[str]:
    """Return platform-appropriate paths where Claude Code stores JSONL files."""
    home = os.path.expanduser("~")
    system = platform.system()

    candidates = [
        # Primary: the projects sub-directory that contains one JSONL per session
        os.path.join(home, ".claude", "projects"),
        # Fallback: watch the whole .claude directory in case the layout differs
        os.path.join(home, ".claude"),
    ]

    if system == "Darwin":
        candidates.append(os.path.join(home, "Library", "Application Support", "Claude"))
    elif system == "Windows":
        appdata = os.environ.get("LOCALAPPDATA", os.path.join(home, "AppData", "Local"))
        candidates.append(os.path.join(appdata, "Claude"))
    else:  # Linux
        candidates.append(os.path.join(home, ".config", "claude"))

    return [p for p in candidates if os.path.isdir(p)]


class _ClaudeFileHandler(FileSystemEventHandler):
    """Watchdog handler that forwards relevant file events to the detector."""

    def __init__(self, detector: "SessionDetector"):
        self._detector = detector

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._detector._on_file_event("created", event.src_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._detector._on_file_event("modified", event.src_path)


class SessionDetector:
    """Watches the file system for Claude Code activity and emits events.

    Reads Claude Code's JSONL conversation files (stored under
    ``~/.claude/projects/``) to extract real prompt/response pairs.

    Subscribers receive events via ``on_event(event_type, data)`` where
    *event_type* is one of: ``session_started``, ``interaction_detected``,
    ``session_ended``.

    ``interaction_detected`` data now includes:

    * ``human_prompt``  – the exact text the user typed
    * ``claude_response`` – the full text (or tool-call summary) Claude returned
    * ``tokens`` – total token count from the ``usage`` field
    * ``language`` – detected programming language
    """

    def __init__(
        self,
        watch_paths: Optional[List[str]] = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ):
        defaults = _default_watch_paths()
        if watch_paths:
            all_paths = defaults + [p for p in watch_paths if p not in defaults]
            self._watch_paths = [p for p in all_paths if os.path.isdir(p)]
        else:
            self._watch_paths = defaults
        self._timeout = timeout_seconds
        self._subscribers: List[Any] = []
        self._observer: Optional[Observer] = None
        self._last_activity: Optional[float] = None
        self._timeout_timer: Optional[threading.Timer] = None
        self._active_session: bool = False

        # JSONL reader with per-file line cursors
        self._reader: ConversationFileReader = ConversationFileReader()
        # Claude Code session IDs we have already emitted session_started for
        self._known_sessions: Set[str] = set()

    # ── Public API ──────────────────────────────────────────────────────

    def subscribe(self, handler: Any) -> None:
        """Register a subscriber. Must implement on_event(event_type, data)."""
        self._subscribers.append(handler)

    def emit(self, event_type: str, data: Dict) -> None:
        """Broadcast an event to all subscribers."""
        logger.debug("Event: %s", event_type)
        for handler in self._subscribers:
            try:
                handler.on_event(event_type, data)
            except Exception:
                logger.exception("Subscriber error on %s", event_type)

    def start(self) -> None:
        """Start watching file system for Claude Code activity."""
        if not self._watch_paths:
            logger.warning("No watch paths found. Use CLI fallback to log interactions.")
            return

        # Advance cursors past existing JSONL files so we only process
        # new conversations that start after this monitor session begins.
        self._initialize_cursors()

        self._observer = Observer()
        handler = _ClaudeFileHandler(self)

        for path in self._watch_paths:
            logger.info("Watching: %s", path)
            self._observer.schedule(handler, path, recursive=True)

        self._observer.start()
        logger.info("Detector started.")

    def stop(self) -> None:
        """Stop watching and cancel any pending timeout."""
        if self._timeout_timer:
            self._timeout_timer.cancel()

        if self._active_session:
            self.emit("session_ended", {
                "timestamp": time.time(),
                "reason": "detector_stopped",
            })
            self._active_session = False

        if self._observer:
            self._observer.stop()
            self._observer.join()
            logger.info("Detector stopped.")

    # ── Internal ────────────────────────────────────────────────────────

    def _initialize_cursors(self) -> None:
        """Fast-forward read cursors past all files that already exist.

        This ensures the watcher only captures conversations that start
        *after* the monitor is launched, avoiding re-processing old history.
        Use ``--import-history`` (main.py) to explicitly import past sessions.
        """
        for watch_path in self._watch_paths:
            for root, _dirs, files in os.walk(watch_path):
                for fname in files:
                    if fname.endswith(".jsonl"):
                        self._reader.advance_cursor(os.path.join(root, fname))

    def _on_file_event(self, action: str, file_path: str) -> None:
        """Handle a file system event from Watchdog."""
        # Only process Claude Code JSONL conversation files
        if not file_path.endswith(".jsonl"):
            return

        turns = self._reader.read_new_turns(file_path)
        if not turns:
            return

        now = time.time()
        self._last_activity = now

        for turn in turns:
            # Use the Claude session ID (or file path as fallback) to decide
            # whether this is the start of a new session.
            session_key = turn.session_id or file_path

            if session_key not in self._known_sessions:
                self._known_sessions.add(session_key)
                self._active_session = True

                language = detect_project_language(turn.cwd)
                if language == "unknown":
                    language = detect_language_from_code(turn.claude_response)

                self.emit("session_started", {
                    "timestamp": turn.timestamp.timestamp(),
                    "file_path": turn.cwd,
                    "project_name": turn.project_name,
                    "language": language,
                })

            # Determine language for this individual interaction
            language = detect_project_language(turn.cwd)
            if language == "unknown":
                language = detect_language_from_code(turn.claude_response)

            self.emit("interaction_detected", {
                "timestamp": turn.timestamp.timestamp(),
                "file_path": turn.cwd,
                "human_prompt": turn.human_prompt,
                "claude_response": turn.claude_response,
                "tokens": turn.tokens_used,
                "language": language,
            })

        self._reset_timeout()

    def _reset_timeout(self) -> None:
        """Reset the inactivity timer."""
        if self._timeout_timer:
            self._timeout_timer.cancel()

        self._timeout_timer = threading.Timer(
            self._timeout, self._on_timeout
        )
        self._timeout_timer.daemon = True
        self._timeout_timer.start()

    def _on_timeout(self) -> None:
        """Called when session times out due to inactivity."""
        if self._active_session:
            logger.info("Session timed out after %ds of inactivity.", self._timeout)
            self._active_session = False
            self.emit("session_ended", {
                "timestamp": time.time(),
                "reason": "timeout",
            })
