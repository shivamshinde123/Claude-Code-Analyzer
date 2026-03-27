# Backend Service

FastAPI server exposing analytics APIs for Claude Code session data.

## Setup

```bash
cd backend
uv sync
```

## Run

```bash
uv run python src/main.py
```

Or with auto-reload:

```bash
uv run uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

## API Docs

Swagger UI: http://localhost:8000/docs

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/sessions` | List sessions (filterable) |
| GET | `/api/sessions/{id}` | Session detail |
| GET | `/api/sessions/stats/summary` | Aggregate stats |
| GET | `/api/metrics/quality` | Code quality metrics |
| GET | `/api/metrics/errors` | Error analysis |
| GET | `/api/metrics/acceptance` | Acceptance rate metrics |
| GET | `/api/timeline/session/{id}` | Session timeline |
| GET | `/api/timeline/historical` | Historical trends |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_PATH` | `../data/sessions.db` | Path to SQLite database |
| `API_PORT` | `8000` | Server port |
| `API_HOST` | `127.0.0.1` | Server host |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | CORS origin |
