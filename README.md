# Claude Code Analyzer

A full-stack analytics system that monitors Claude Code sessions locally, computes metrics, and displays interactive dashboards.

## Architecture

Three independent services communicating through a shared SQLite database:

```
monitor/    →  SQLite DB  →  backend/  →  frontend/
(collect)      (shared)      (API)        (dashboard)
```

- **Monitor** — Python service that watches `.claude` files and logs session data
- **Backend** — FastAPI server exposing analytics REST APIs
- **Frontend** — React dashboard with interactive charts and filters

## Tech Stack

| Service | Stack |
|---------|-------|
| Monitor | Python 3.9+, SQLAlchemy, Watchdog, Pydantic, uv |
| Backend | Python 3.9+, FastAPI, Uvicorn, SQLAlchemy, uv |
| Frontend | React 18, Vite, Plotly.js, Axios, React Router |

## Quick Start

### Option 1: Start all services at once

**Linux/macOS:**
```bash
./run.sh
```

**Windows (PowerShell):**
```powershell
.\run.ps1
```

### Option 2: Start services individually

**Monitor** (data collection):
```bash
cd monitor && uv sync && uv run python src/main.py
```

**Backend** (API server — http://localhost:8000):
```bash
cd backend && uv sync && uv run uvicorn src.main:app --host 127.0.0.1 --port 8000
```

**Frontend** (dashboard — http://localhost:5173):
```bash
cd frontend && npm install && npm run dev
```

### Option 3: Docker

```bash
docker compose up --build
```

## Features

- **Dashboard** — KPI cards, acceptance rate timeline, error distribution chart, scatter plot
- **Session list** — Sortable table of all coding sessions with language, duration, acceptance rate
- **Session detail** — Full interaction history with prompts, responses, and errors
- **Filtering** — Filter by programming language, date range
- **Insights** — Auto-generated recommendations from session metrics
- **Code metrics** — Cyclomatic complexity, nesting depth, type hint detection, quality scores

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /api/sessions` | List sessions (filterable) |
| `GET /api/sessions/stats/summary` | Aggregate statistics |
| `GET /api/sessions/{id}` | Session detail with interactions |
| `GET /api/metrics/quality` | Code quality metrics over time |
| `GET /api/metrics/errors` | Error distribution and patterns |
| `GET /api/metrics/acceptance` | Acceptance rates by language/type |
| `GET /api/timeline/session/{id}` | Per-interaction timeline |
| `GET /api/timeline/historical` | Daily/weekly/monthly trends |

API docs (Swagger UI): http://localhost:8000/docs

## Running Tests

```bash
# Backend tests (52 tests)
cd backend && uv sync --dev && uv run pytest tests/ -v

# Monitor tests (40 tests)
cd monitor && uv sync --dev && uv run pytest tests/ -v
```

## Project Structure

```
claude-code-analyzer/
├── monitor/          # Python: watches .claude files, logs sessions
│   ├── src/          #   detector, logger, db, utils
│   └── tests/        #   40 unit tests
├── backend/          # Python FastAPI: exposes analytics APIs
│   ├── src/          #   api/, db/, utils/
│   └── tests/        #   52 unit + integration tests
├── frontend/         # React: interactive dashboards and charts
│   └── src/          #   pages/, components/, hooks/, api/
├── shared/           # Database schema and constants
├── data/             # SQLite database (auto-created)
├── run.sh            # Start all services (Linux/macOS)
├── run.ps1           # Start all services (Windows)
└── docker-compose.yml
```

## License

MIT
