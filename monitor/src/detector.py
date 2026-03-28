"""File system monitoring to detect Claude Code sessions."""

import logging
import os
import platform
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

logger = logging.getLogger(__name__)

# Default session timeout: 5 minutes of inactivity
DEFAULT_TIMEOUT_SECONDS = 300


def _default_watch_paths() -> List[str]:
    """Return platform-appropriate paths where Claude Code stores metadata."""
    home = os.path.expanduser("~")
    system = platform.system()

    paths = [
        os.path.join(home, ".claude"),
    ]

    if system == "Darwin":
        paths.append(os.path.join(home, "Library", "Application Support", "Claude"))
    elif system == "Windows":
        appdata = os.environ.get("LOCALAPPDATA", os.path.join(home, "AppData", "Local"))
        paths.append(os.path.join(appdata, "Claude"))
    else:  # Linux
        paths.append(os.path.join(home, ".config", "claude"))

    return [p for p in paths if os.path.isdir(p)]


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

    Subscribers receive events via `on_event(event_type, data)` where
    event_type is one of: session_started, interaction_detected, session_ended.
    """

    def __init__(
        self,
        watch_paths: Optional[List[str]] = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ):
        self._watch_paths = watch_paths or _default_watch_paths()
        self._timeout = timeout_seconds
        self._subscribers: List[Any] = []
        self._observer: Optional[Observer] = None
        self._last_activity: Optional[float] = None
        self._timeout_timer: Optional[threading.Timer] = None
        self._active_session: bool = False

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

    def _on_file_event(self, action: str, file_path: str) -> None:
        """Handle a file system event from Watchdog."""
        now = time.time()
        self._last_activity = now

        if not self._active_session:
            self._active_session = True
            self.emit("session_started", {
                "timestamp": now,
                "file_path": file_path,
            })
        else:
            self.emit("interaction_detected", {
                "timestamp": now,
                "file_path": file_path,
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
