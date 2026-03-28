# Monitor Service

Watches for Claude Code sessions and logs interactions to SQLite.

## Setup

```bash
cd monitor
uv sync
```

## Run

```bash
uv run python src/main.py
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_PATH` | `../data/sessions.db` | Path to SQLite database |
| `WATCH_DIRECTORY` | Current directory | Root directory to monitor |
| `SESSION_TIMEOUT_SECONDS` | `300` | Inactivity timeout |
| `LOG_LEVEL` | `INFO` | Python logging level |

## Tests

```bash
uv sync --dev
uv run pytest tests/ -v
```

40 tests covering utility functions and database operations.

## CLI Fallback

For testing without actual Claude Code:

```bash
uv run python src/main.py --log-interaction "Write a hello function" "def hello(): print('hello')"
```
