"""Monitor entry point: orchestrates detector and logger."""

import argparse
import logging
import os
import signal
import sys
import time

from .db import DatabaseManager
from .detector import SessionDetector
from .logger import SessionLogger

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sessions.db")


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Claude Code Analyzer - Monitor Service")
    parser.add_argument(
        "--db-path",
        default=os.environ.get("DATABASE_PATH", DEFAULT_DB_PATH),
        help="Path to SQLite database (default: ../data/sessions.db)",
    )
    parser.add_argument(
        "--watch-dir",
        default=os.environ.get("WATCH_DIRECTORY"),
        help="Additional directory to watch (optional)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=int(os.environ.get("SESSION_TIMEOUT_SECONDS", "300")),
        help="Session inactivity timeout in seconds (default: 300)",
    )
    parser.add_argument(
        "--log-level",
        default=os.environ.get("LOG_LEVEL", "INFO"),
        help="Logging level (default: INFO)",
    )

    # CLI fallback for testing
    parser.add_argument(
        "--log-interaction",
        nargs=2,
        metavar=("PROMPT", "RESPONSE"),
        help="Manually log a single interaction (for testing)",
    )
    parser.add_argument(
        "--language",
        default="python",
        help="Language for --log-interaction (default: python)",
    )
    parser.add_argument(
        "--test-session",
        action="store_true",
        help="Log a complete test session with sample data",
    )

    return parser.parse_args()


def log_single_interaction(db: DatabaseManager, prompt: str, response: str, language: str) -> None:
    """Log a single interaction via CLI fallback."""
    logger = SessionLogger(db)
    now = time.time()

    logger.on_event("session_started", {
        "timestamp": now,
        "language": language,
        "file_path": f"cli_test.{language[:2]}",
        "project_name": "cli-test",
    })

    logger.on_event("interaction_detected", {
        "timestamp": now + 1,
        "human_prompt": prompt,
        "claude_response": response,
    })

    logger.on_event("session_ended", {
        "timestamp": now + 2,
        "reason": "completed",
    })

    print(f"Logged interaction: {prompt[:50]}...")


def log_test_session(db: DatabaseManager) -> None:
    """Log a complete test session with sample data."""
    test_interactions = [
        (
            "Write a function that validates email addresses",
            'def validate_email(email: str) -> bool:\n    """Validate an email address format."""\n    import re\n    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$"\n    return bool(re.match(pattern, email))',
        ),
        (
            "Add error handling to the email validator",
            'def validate_email(email: str) -> bool:\n    """Validate an email address format."""\n    if not email or not isinstance(email, str):\n        return False\n    import re\n    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$"\n    return bool(re.match(pattern, email))',
        ),
        (
            "Write a test for the email validator",
            'def test_validate_email():\n    assert validate_email("user@example.com") is True\n    assert validate_email("invalid") is False\n    assert validate_email("") is False\n    assert validate_email(None) is False\n    assert validate_email("a@b.c") is True',
        ),
    ]

    session_logger = SessionLogger(db)
    now = time.time()

    session_logger.on_event("session_started", {
        "timestamp": now,
        "language": "python",
        "file_path": "test_project/validators.py",
        "project_name": "test-project",
    })

    for i, (prompt, response) in enumerate(test_interactions):
        session_logger.on_event("interaction_detected", {
            "timestamp": now + (i + 1) * 30,
            "human_prompt": prompt,
            "claude_response": response,
        })

    session_logger.on_event("session_ended", {
        "timestamp": now + len(test_interactions) * 30 + 60,
        "reason": "completed",
    })

    print(f"Test session logged with {len(test_interactions)} interactions.")


def run_watcher(db: DatabaseManager, args: argparse.Namespace) -> None:
    """Run the file system watcher continuously."""
    watch_paths = None
    if args.watch_dir:
        watch_paths = [args.watch_dir]

    detector = SessionDetector(
        watch_paths=watch_paths,
        timeout_seconds=args.timeout,
    )
    session_logger = SessionLogger(db)
    detector.subscribe(session_logger)

    # Graceful shutdown
    def shutdown(signum, frame):
        print("\nShutting down...")
        detector.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    detector.start()
    print("Monitor started. Watching for Claude Code sessions...")
    print("Press Ctrl+C to stop.\n")

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        detector.stop()


def main() -> None:
    args = parse_args()
    setup_logging(args.log_level)
    db_path = os.path.abspath(args.db_path)
    db = DatabaseManager(db_path)

    print(f"Database: {db_path}")

    if args.log_interaction:
        prompt, response = args.log_interaction
        log_single_interaction(db, prompt, response, args.language)
    elif args.test_session:
        log_test_session(db)
    else:
        run_watcher(db, args)


if __name__ == "__main__":
    main()
