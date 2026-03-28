# Claude Code Analyzer - Developer Context

This file serves as the central hub for Claude Code sessions. Reference the `rules/` folder for specific implementation details and guidelines.

## Quick Project Overview

**What**: Full-stack analytics system that monitors Claude Code sessions locally, computes metrics, and displays interactive dashboards.

**Why**: Portfolio project showcasing full-stack capabilities (Python monitoring + FastAPI backend + React frontend), clean architecture, and data engineering skills.

**Architecture**: Three independent services (monitor → backend → frontend) with shared SQLite database.

```
claude-code-analyzer/
├── monitor/          # Python: watches .claude files, logs sessions
├── backend/          # Python FastAPI: exposes analytics APIs
├── frontend/         # React: interactive dashboards and charts
├── shared/           # Database schema and constants
└── rules/            # Implementation guidelines (this folder)
```

## Key Files & When to Reference

| File | Use When |
|------|----------|
| `rules/00-architecture.md` | Understanding overall system design and folder structure |
| `rules/01-database-schema.md` | Building database models, writing queries, or understanding data relationships |
| `rules/02-monitor-service.md` | Implementing the monitoring system (detector, logger, db interactions) |
| `rules/03-backend-service.md` | Building FastAPI endpoints, API design, aggregation functions |
| `rules/04-frontend-service.md` | React components, hooks, styling, chart integration |
| `rules/05-implementation-phases.md` | Step-by-step build order, what to do in each phase |
| `rules/06-testing-strategy.md` | Testing approach, how to validate each service |
| `rules/07-subagent-workflow.md` | When and how to create specialized Claude Code agents |
| `rules/08-styling-standards.md` | Code style, naming conventions, best practices |

## Current Status

- [x] Architecture designed
- [x] Database schema finalized
- [x] Phase 1: Setup (folder structure, configs)
- [x] Phase 2: Monitor service
- [x] Phase 3: Backend service
- [x] Phase 4: Frontend service
- [ ] Phase 5: Integration & Polish

## Key Technologies

**Monitor**
- Python 3.9+
- SQLAlchemy (ORM)
- Watchdog (file monitoring)
- Pydantic (validation)
- uv (package manager)

**Backend**
- FastAPI
- Uvicorn
- SQLAlchemy
- Pydantic
- Python 3.9+

**Frontend**
- React 18
- Vite
- Plotly.js (charting)
- Axios (HTTP client)
- Tailwind CSS (styling, optional)

## Database

**Path**: `../data/sessions.db` (shared across all services)

**Tables**: 
- `sessions` - Session metadata
- `interactions` - Individual code suggestions
- `errors` - Error tracking
- `code_metrics` - Code quality metrics

See `rules/01-database-schema.md` for detailed schemas.

## Running Services

**Monitor** (data collection)
```bash
cd monitor && uv sync && uv run python src/main.py
```

**Backend** (API server)
```bash
cd backend && uv sync && uv run python src/main.py
```

**Frontend** (dashboard)
```bash
cd frontend && npm install && npm run dev
```

Dashboard will be available at `http://localhost:5173`

## MVP Success Criteria

✓ Monitor collects Claude Code session data to SQLite
✓ Backend serves data via REST APIs with filtering
✓ Frontend displays interactive charts and filters
✓ All three services run with simple commands
✓ Dashboard updates as new sessions are logged
✓ Code is clean, documented, and cloneable

## Git Workflow

- **Never commit directly to the `master` branch.** Always create a separate feature branch for each step/phase/task.
- Create a pull request (PR) to merge the feature branch into `master`.
- Branch naming: use descriptive names like `phase-1/setup`, `feature/monitor-service`, `fix/db-schema`, etc.
- **Before starting any new task, always fetch the GitHub issue status** (`gh issue list`) to check what's open, in progress, or completed. Update issues as you progress (add comments, check off tasks, close when done).

## Important Notes

- **Use `uv` not `pip`** for all Python dependencies
- **Each service is independent** - can be tested separately
- **Database is shared** - monitor writes, backend reads, frontend displays
- **Use subagents** when a component becomes complex (see `rules/07-subagent-workflow.md`)
- **Commit frequently** with clear messages
- **This is a portfolio project** - production-quality code, good documentation

## Next Steps

1. Start with Phase 1: Setup (see `rules/05-implementation-phases.md`)
2. Create folder structure and config files
3. Set up each service's pyproject.toml
4. Move to Phase 2: Monitor service implementation

## Questions? Issues?

- Check the rules folder for specific guidance
- Review the relevant rule file before starting a new component
- Create a subagent for complex tasks (see `rules/07-subagent-workflow.md`)
