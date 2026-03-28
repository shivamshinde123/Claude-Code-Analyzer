"""Monitor entry point: orchestrates detector and logger."""

import argparse
import logging
import os
import signal
import sys
import time

from .db import DatabaseManager
from .detector import SessionDetector, _default_watch_paths
from .logger import SessionLogger
from .reader import ConversationFileReader
from .utils import (
    classify_interaction,
    compute_code_metrics,
    detect_language_from_code,
    detect_project_language,
    estimate_tokens,
)

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sessions.db")

# Phrases that suggest the user is rejecting / correcting the previous response.
_REJECTION_PHRASES = [
    "that's wrong", "thats wrong", "that is wrong",
    "try again", "no, instead", "no instead",
    "revert", "not right", "incorrect",
    "that doesn't work", "that doesnt work", "doesn't work", "doesnt work",
    "not what i wanted", "wrong approach", "undo that",
    "not correct", "you're wrong", "youre wrong",
]


def _is_rejection(prompt: str) -> bool:
    """Return True if *prompt* looks like a correction or rejection of the previous response.

    Both outright rejections ("that's wrong", "revert") and requests to retry
    ("try again", "not what I wanted") are treated equivalently here — in both
    cases the immediately preceding interaction is considered not accepted.
    """
    text = prompt.lower()
    return any(phrase in text for phrase in _REJECTION_PHRASES)


LANGUAGE_TO_EXT = {
    "python": "py", "javascript": "js", "typescript": "ts",
    "java": "java", "go": "go", "rust": "rs", "csharp": "cs",
    "cpp": "cpp", "ruby": "rb", "php": "php", "swift": "swift", "kotlin": "kt",
}


def _language_extension(language: str) -> str:
    return LANGUAGE_TO_EXT.get(language, language[:2])


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
        "--import-history",
        action="store_true",
        help=(
            "Read all existing Claude Code JSONL files and import them as completed "
            "sessions into the database.  Safe to run multiple times on the same DB "
            "(duplicate sessions may appear if the file has not changed between runs)."
        ),
    )
    parser.add_argument(
        "--no-import-history",
        action="store_true",
        default=False,
        help=(
            "Skip the automatic history import that normally runs before starting "
            "the live watcher. Useful if you want a faster startup or have already "
            "imported history manually."
        ),
    )

    return parser.parse_args()


def log_single_interaction(db: DatabaseManager, prompt: str, response: str, language: str) -> None:
    """Log a single interaction via CLI fallback."""
    logger = SessionLogger(db)
    now = time.time()

    logger.on_event("session_started", {
        "timestamp": now,
        "language": language,
        "file_path": f"cli_test.{_language_extension(language)}",
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



def import_history(db: DatabaseManager) -> None:
    """Import all existing Claude Code JSONL conversations into the database.

    Scans the default Claude Code watch paths for ``*.jsonl`` files, parses
    each one from the beginning, and writes completed sessions + interactions
    into the database.  Useful for populating the dashboard with past activity
    without running the live watcher.
    """
    watch_paths = _default_watch_paths()
    if not watch_paths:
        print("No Claude Code directories found. Is Claude Code installed?")
        return

    reader = ConversationFileReader()
    sessions_imported = 0
    interactions_imported = 0

    for watch_path in watch_paths:
        for root, _dirs, files in os.walk(watch_path):
            for fname in sorted(files):
                if not fname.endswith(".jsonl"):
                    continue

                file_path = os.path.join(root, fname)
                turns = reader.read_all_turns(file_path)
                if not turns:
                    continue

                first_turn = turns[0]
                last_turn = turns[-1]
                cwd = first_turn.cwd

                # Determine language: project config first, then code-fence scan
                language = detect_project_language(cwd)
                if language == "unknown":
                    for t in turns:
                        lang = detect_language_from_code(t.claude_response)
                        if lang != "unknown":
                            language = lang
                            break

                session_id = db.create_session(
                    language=language,
                    start_time=first_turn.timestamp,
                    status="completed",
                    project_name=first_turn.project_name,
                    file_path=cwd,
                )
                sessions_imported += 1

                accepted_count = 0

                for i, turn in enumerate(turns):
                    # Heuristic: if the very next prompt looks like a rejection,
                    # mark this interaction as not accepted.
                    if i + 1 < len(turns):
                        was_accepted = not _is_rejection(turns[i + 1].human_prompt)
                    else:
                        # No follow-up prompt exists: this is the final interaction in the
                        # session, so we optimistically assume it was accepted (the user
                        # stopped asking, which is the most common success signal available
                        # without explicit user feedback).
                        was_accepted = True

                    if was_accepted:
                        accepted_count += 1

                    tokens = turn.tokens_used or estimate_tokens(
                        turn.human_prompt + turn.claude_response
                    )
                    interaction_id = db.add_interaction(
                        session_id=session_id,
                        sequence_number=i + 1,
                        timestamp=turn.timestamp,
                        human_prompt=turn.human_prompt,
                        claude_response=turn.claude_response,
                        was_accepted=was_accepted,
                        was_modified=(i > 0),
                        interaction_type=classify_interaction(turn.claude_response),
                        tokens_used=tokens,
                    )

                    if language in ("python", "javascript", "typescript"):
                        metrics = compute_code_metrics(turn.claude_response, language)
                        db.add_code_metrics(
                            interaction_id=interaction_id,
                            language=language,
                            **metrics,
                        )

                    # Detect and persist errors found in the conversation text.
                    errors = SessionLogger._detect_errors(
                        turn.human_prompt, turn.claude_response, language
                    )
                    for error_type, error_message, severity in errors:
                        db.add_error(
                            interaction_id=interaction_id,
                            session_id=session_id,
                            error_type=error_type,
                            error_message=error_message,
                            language=language,
                            severity=severity,
                            timestamp=turn.timestamp,
                        )

                    interactions_imported += 1

                acceptance_rate = accepted_count / len(turns) if turns else 0.0

                db.end_session(
                    session_id=session_id,
                    end_time=last_turn.timestamp,
                    acceptance_rate=acceptance_rate,
                    status="completed",
                )

    print(
        f"History import complete: {sessions_imported} session(s), "
        f"{interactions_imported} interaction(s)."
    )


def run_watcher(db: DatabaseManager, args: argparse.Namespace) -> None:
    """Run the file system watcher continuously."""
    # Append --watch-dir to defaults rather than replacing them
    extra_paths = [args.watch_dir] if args.watch_dir else None

    detector = SessionDetector(
        watch_paths=extra_paths,
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
    elif args.import_history:
        import_history(db)
    else:
        if not args.no_import_history:
            print("Auto-importing history before starting watcher...")
            import_history(db)
        run_watcher(db, args)


if __name__ == "__main__":
    main()
