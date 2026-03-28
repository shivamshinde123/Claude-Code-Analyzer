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

## Demo Data (Seeding)

Want to see charts right away? Seed the SQLite DB with realistic demo data.

1) Stop running services first
   - If you started with `run.ps1`/`run.sh`, press Ctrl+C and wait for �All services stopped.�
   - This releases `data/sessions.db` so the seeder can write (avoids WinError 32 on Windows).

2) Seed demo data

- Windows (PowerShell):
```powershell
cd monitor
uv sync
uv run python -m src.seed --reset --sessions 20
```

- macOS/Linux:
```bash
cd monitor
uv sync
uv run python -m src.seed --reset --sessions 20
```

Options:
- Omit `--reset` to append more data instead of recreating the DB.
- Control volume with `--sessions N --min-interactions 1 --max-interactions 6`.

3) Start the app
- Windows: `./run.ps1`
- macOS/Linux: `./run.sh`
- Frontend: http://localhost:5173  �  Backend: http://localhost:8000

Docker users (optional):
```bash
docker compose run --rm monitor uv run python -m src.seed --reset --sessions 20
# then
docker compose up --build
```

Troubleshooting:
- �PermissionError: file in use�: ensure backend/monitor are stopped and no DB browser has `data/sessions.db` open.
- Use a custom DB path: `uv run python -m src.seed --db-path ..\data\sessions_demo.db` and set `DATABASE_PATH` for the backend accordingly.