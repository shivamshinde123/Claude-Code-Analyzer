"""Seed the SQLite database with realistic test data for the dashboard.

Usage:
  cd monitor
  uv run python -m src.seed --sessions 20

Options:
  --db-path <path>        Override database location
  --sessions <int>        Number of sessions to create (default: 12)
  --min-interactions <n>  Minimum interactions per session (default: 1)
  --max-interactions <n>  Maximum interactions per session (default: 6)
  --reset                 Remove existing DB before seeding
"""

from __future__ import annotations

import argparse
import os
import random
import string
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from .db import DatabaseManager
from .utils import compute_code_metrics

# Default DB alongside project data/ like other services use
DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "sessions.db"

LANG_EXT = {
    "python": "py",
    "javascript": "js",
    "typescript": "ts",
}

PROMPTS = [
    "Write a function that validates emails",
    "Implement a debounce utility",
    "Refactor to add type hints",
    "Fix off-by-one error in range",
    "Document the public API",
    "Add input validation and error handling",
]

def _rand_name(prefix: str) -> str:
    return f"{prefix}_{''.join(random.choices(string.ascii_lowercase, k=6))}"


def _code_snippet(language: str, idx: int) -> str:
    if language == "python":
        variants = [
            "def add(a: int, b: int) -> int:\n    return a + b\n",
            "def debounce(fn, wait=300):\n    import time\n    last=[0]\n    def wrapped(*args, **kwargs):\n        now=time.time()*1000\n        if now-last[0]>wait:\n            last[0]=now\n            return fn(*args, **kwargs)\n    return wrapped\n",
            "class Service:\n    def __init__(self, repo):\n        self.repo = repo\n    def find(self, q: str) -> list[str]:\n        return [x for x in self.repo if q in x]\n",
        ]
    elif language == "javascript":
        variants = [
            "export function sum(a, b) { return a + b }\n",
            "export function debounce(fn, wait = 300) {\n  let t;\n  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), wait) }\n}\n",
            "export class Service {\n  constructor(items) { this.items = items }\n  find(q) { return this.items.filter(x => x.includes(q)) }\n}\n",
        ]
    else:  # typescript
        variants = [
            "export function sum(a: number, b: number): number { return a + b }\n",
            "export function debounce<T extends (...a: any[]) => any>(fn: T, wait = 300) {\n  let t: any;\n  return (...args: Parameters<T>) => { clearTimeout(t); t = setTimeout(() => fn(...args), wait) }\n}\n",
            "export class Service {\n  constructor(private items: string[]) {}\n  find(q: string): string[] { return this.items.filter(x => x.includes(q)) }\n}\n",
        ]
    return variants[idx % len(variants)]


def _maybe_error() -> Tuple[str, str] | None:
    # ~30% chance of an error on an interaction
    if random.random() > 0.3:
        return None
    etype = random.choices(["syntax", "runtime", "type", "logic"], weights=[3, 3, 2, 2])[0]
    messages = {
        "syntax": "SyntaxError: invalid syntax at line 1",
        "runtime": "TypeError: undefined is not a function",
        "type": "TS2322: Type 'number' is not assignable to type 'string'",
        "logic": "AssertionError: expected 5, got 4",
    }
    return etype, messages[etype]


def seed(db_path: Path, n_sessions: int, min_i: int, max_i: int) -> None:
    db = DatabaseManager(str(db_path))

    now = datetime.now(timezone.utc)

    languages = [
        ("python", 0.55),
        ("javascript", 0.3),
        ("typescript", 0.15),
    ]

    for s in range(n_sessions):
        lang = random.choices([l for l, _ in languages], weights=[w for _, w in languages])[0]
        ext = LANG_EXT[lang]
        project = random.choice(["analytics", "frontend", "etl", "dashboard"])  # project label

        # Session timing: spread over the last 21 days
        start = now - timedelta(days=random.randint(0, 21), hours=random.randint(0, 23))

        session_id = db.create_session(
            language=lang,
            start_time=start,
            project_name=project,
            file_path=f"seed/{project}/module.{ext}",
        )

        n_interactions = random.randint(min_i, max_i)
        accepted = 0
        for i in range(1, n_interactions + 1):
            timestamp = start + timedelta(minutes=5 * i)
            prompt = random.choice(PROMPTS)
            code = _code_snippet(lang, i)

            # Acceptance likelihood by language & position
            base = {"python": 0.75, "javascript": 0.7, "typescript": 0.8}[lang]
            was_accepted = random.random() < (base - 0.1 + 0.02 * i)
            if was_accepted:
                accepted += 1

            was_modified = (i > 1) and (random.random() < 0.35)
            itype = random.choice(["new_code", "refactor", "bugfix", "explanation"]) if i > 1 else "new_code"

            seq = db.get_next_sequence_number(session_id)
            interaction_id = db.add_interaction(
                session_id=session_id,
                sequence_number=seq,
                timestamp=timestamp,
                human_prompt=prompt,
                claude_response=code,
                was_accepted=was_accepted,
                was_modified=was_modified,
                interaction_type=itype,
                tokens_used=max(20, len(prompt + code) // 4),
            )

            # Add metrics for py/js/ts
            metrics = compute_code_metrics(code, lang)
            db.add_code_metrics(
                interaction_id=interaction_id,
                language=lang,
                **metrics,
            )

            # Occasionally add an error
            err = _maybe_error()
            if err:
                etype, message = err
                db.add_error(
                    interaction_id=interaction_id,
                    session_id=session_id,
                    error_type=etype,
                    error_message=message,
                    language=lang,
                    severity=random.choice(["low", "medium", "high"]),
                    timestamp=timestamp + timedelta(seconds=5),
                    was_resolved_in_next_interaction=random.random() < 0.6,
                    recovery_interactions_count=random.randint(0, 3),
                )

        end = start + timedelta(minutes=5 * (n_interactions + 1))
        acceptance_rate = accepted / max(1, n_interactions)
        status = random.choices(["completed", "abandoned"], weights=[8, 2])[0]
        db.end_session(
            session_id=session_id,
            end_time=end,
            acceptance_rate=acceptance_rate,
            status=status,
        )

    print(f"Seeded {n_sessions} sessions into {db_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Claude Code Analyzer DB with demo data")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--sessions", type=int, default=12)
    parser.add_argument("--min-interactions", type=int, default=1)
    parser.add_argument("--max-interactions", type=int, default=6)
    parser.add_argument("--reset", action="store_true", help="Remove existing DB before seeding")
    args = parser.parse_args()

    db_path = Path(args.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if args.reset and db_path.exists():
        db_path.unlink()

    random.seed(42)  # reproducible runs
    seed(db_path, args.sessions, args.min_interactions, args.max_interactions)


if __name__ == "__main__":
    main()