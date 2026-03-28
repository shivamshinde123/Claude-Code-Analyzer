"""Parse Claude Code JSONL conversation files to extract interactions.

Claude Code stores each session as a JSONL file under::

    ~/.claude/projects/<encoded-project-path>/<session-uuid>.jsonl

Every line is a JSON object.  The two relevant ``type`` values are:

* ``"user"``      – human message (the prompt)
* ``"assistant"`` – Claude's reply (text and/or tool calls)

Example user entry::

    {
      "type": "user",
      "message": {"role": "user", "content": [{"type": "text", "text": "..."}]},
      "uuid": "...",
      "timestamp": "2024-01-01T12:00:00.000Z",
      "sessionId": "...",
      "cwd": "/home/user/myproject",
      "version": "1"
    }

Example assistant entry (adds ``usage`` and optional ``costUSD``)::

    {
      "type": "assistant",
      "message": {
        "role": "assistant",
        "content": [
          {"type": "text", "text": "Here is the code …"},
          {"type": "tool_use", "id": "…", "name": "write_file", "input": {…}}
        ]
      },
      "uuid": "...",
      "timestamp": "2024-01-01T12:00:05.000Z",
      "sessionId": "...",
      "cwd": "/home/user/myproject",
      "costUSD": 0.003,
      "durationMs": 4200,
      "usage": {"input_tokens": 500, "output_tokens": 300,
                "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0},
      "version": "1"
    }
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterator, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    """One human→assistant interaction extracted from a JSONL file."""

    human_prompt: str
    claude_response: str
    timestamp: datetime
    session_id: str
    project_name: str
    cwd: str
    tokens_used: int


# ── Helpers ──────────────────────────────────────────────────────────────────


def _extract_text(content) -> str:
    """Return the concatenated text from a message *content* value.

    *content* may be a plain string or a list of typed content blocks.
    Only ``{"type": "text", ...}`` blocks are extracted; tool-result and
    tool-use blocks are ignored here (see :func:`_extract_tool_summary`).
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [
            block["text"]
            for block in content
            if isinstance(block, dict) and block.get("type") == "text" and block.get("text")
        ]
        return "\n".join(parts)
    return ""


def _extract_tool_summary(content) -> str:
    """Return a short human-readable summary of any tool calls present.

    Used as a fallback when an assistant message has no plain-text body
    (e.g. Claude went straight to calling tools without explaining itself).
    """
    if not isinstance(content, list):
        return ""
    names = [
        block["name"]
        for block in content
        if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name")
    ]
    return "[Tool use: {}]".format(", ".join(names)) if names else ""


def _extract_tokens(entry: dict) -> int:
    """Return the total token count from the ``usage`` field of an entry."""
    usage = entry.get("usage") or {}
    return usage.get("input_tokens", 0) + usage.get("output_tokens", 0)


def _parse_timestamp(ts: str) -> datetime:
    """Convert an ISO 8601 string (possibly ending in ``Z``) to a datetime."""
    if not ts:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)


def _project_name(cwd: str) -> str:
    """Derive a display name from a working-directory path."""
    if not cwd:
        return "unknown"
    return os.path.basename(cwd.rstrip("/\\")) or "unknown"


# ── Main class ───────────────────────────────────────────────────────────────


class ConversationFileReader:
    """Reads a Claude Code JSONL file and returns new conversation turns.

    A *turn* is one user message immediately followed by the assistant reply.
    An internal per-file line cursor ensures that successive calls to
    :meth:`read_new_turns` never return the same turn twice, making it safe
    to call on every watchdog ``on_modified`` event.

    Usage::

        reader = ConversationFileReader()

        # On the first watchdog event for a file:
        turns = reader.read_new_turns("/path/to/session.jsonl")

        # On the next event for the same file (only new lines are read):
        turns = reader.read_new_turns("/path/to/session.jsonl")
    """

    def __init__(self) -> None:
        # Maps absolute file path → number of lines already consumed
        self._cursors: Dict[str, int] = {}

    # ── Public API ───────────────────────────────────────────────────────────

    def read_new_turns(self, file_path: str) -> List[ConversationTurn]:
        """Return :class:`ConversationTurn` objects for lines added since the
        last call for *file_path*.  Returns an empty list if nothing is new or
        the file cannot be read.
        """
        new_entries = self._read_new_entries(file_path)
        if not new_entries:
            return []
        return list(self._pair_entries(new_entries))

    def read_all_turns(self, file_path: str) -> List[ConversationTurn]:
        """Read *file_path* from the beginning, ignoring any stored cursor.

        The cursor is then advanced to the end so future calls to
        :meth:`read_new_turns` will only see subsequent content.
        Use this when importing historical sessions.
        """
        self._cursors.pop(file_path, None)
        return self.read_new_turns(file_path)

    def advance_cursor(self, file_path: str) -> None:
        """Fast-forward the cursor to the current end of *file_path*.

        Call this for files that already existed when the monitor started so
        that :meth:`read_new_turns` only ever returns *future* activity.
        """
        try:
            with open(file_path, encoding="utf-8") as fh:
                count = sum(1 for _ in fh)
            self._cursors[file_path] = count
        except OSError:
            pass

    # ── Internal ─────────────────────────────────────────────────────────────

    def _read_new_entries(self, file_path: str) -> List[dict]:
        """Return parsed JSON objects for lines appended after the cursor."""
        try:
            with open(file_path, encoding="utf-8") as fh:
                all_lines = fh.readlines()
        except OSError:
            logger.debug("Cannot open %s", file_path)
            return []

        cursor = self._cursors.get(file_path, 0)
        new_lines = all_lines[cursor:]
        self._cursors[file_path] = len(all_lines)

        entries: List[dict] = []
        for raw in new_lines:
            raw = raw.strip()
            if not raw:
                continue
            try:
                entries.append(json.loads(raw))
            except json.JSONDecodeError:
                logger.debug("Skipping malformed JSON line in %s", file_path)
        return entries

    @staticmethod
    def _pair_entries(entries: List[dict]) -> Iterator[ConversationTurn]:
        """Yield one :class:`ConversationTurn` per consecutive user→assistant pair."""
        pending_human: Optional[dict] = None

        for entry in entries:
            kind = entry.get("type")

            if kind == "user":
                msg = entry.get("message", {})
                text = _extract_text(msg.get("content", ""))
                if text.strip():
                    # Only treat messages that have real text as prompts;
                    # pure tool-result messages are skipped.
                    pending_human = entry

            elif kind == "assistant" and pending_human is not None:
                msg = entry.get("message", {})
                content = msg.get("content", "")
                response = _extract_text(content)

                # If Claude only made tool calls without explanatory text, note
                # the tool names so the response field is never empty.
                if not response.strip():
                    response = _extract_tool_summary(content)

                if not response.strip():
                    # Completely empty assistant entry – skip and keep pending_human
                    # so the next assistant entry can still pair with it.
                    continue

                human_text = _extract_text(
                    pending_human.get("message", {}).get("content", "")
                )
                cwd = entry.get("cwd") or pending_human.get("cwd", "")
                sid = entry.get("sessionId") or pending_human.get("sessionId", "")
                ts = entry.get("timestamp") or pending_human.get("timestamp", "")

                yield ConversationTurn(
                    human_prompt=human_text,
                    claude_response=response,
                    timestamp=_parse_timestamp(ts),
                    session_id=sid,
                    project_name=_project_name(cwd),
                    cwd=cwd,
                    tokens_used=_extract_tokens(entry),
                )
                pending_human = None
