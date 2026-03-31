"""FastAPI backend for Claude Code Analyzer analytics."""

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import sessions, metrics, timeline
from .db.models import Base, get_engine, get_session_factory
from .db.queries import QueryManager

load_dotenv()

app = FastAPI(
    title="Claude Code Analyzer API",
    version="0.1.0",
    description="Analytics API for Claude Code sessions",
)

# CORS — allow the frontend dev server
frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup — ensure the data directory and tables exist
db_path = os.getenv("DATABASE_PATH", os.path.join("..", "data", "sessions.db"))
os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

engine = get_engine(db_path)
Base.metadata.create_all(engine)

# Reuse the same engine for the session factory to avoid a second connection pool
session_factory = get_session_factory(db_path, engine=engine)
qm = QueryManager(session_factory)

# Wire the query manager into each router module
sessions.init_query_manager(qm)
metrics.init_query_manager(qm)
timeline.init_query_manager(qm)

# Health check
@app.get("/health")
async def health():
    """Return a simple liveness probe response.

    Used by load balancers and container orchestrators to confirm the service
    is up and accepting requests.
    """
    return {"status": "ok"}


# Register routers
app.include_router(sessions.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")
app.include_router(timeline.router, prefix="/api")


