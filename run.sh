#!/usr/bin/env bash
# Start all three Claude Code Analyzer services.
# Usage: ./run.sh

set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

cleanup() {
    set +e
    echo ""
    echo "Shutting down services..."
    [ -n "$MONITOR_PID" ]  && kill "$MONITOR_PID"  2>/dev/null
    [ -n "$BACKEND_PID" ]  && kill "$BACKEND_PID"  2>/dev/null
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null
    [ -n "$MONITOR_PID" ]  && wait "$MONITOR_PID"  2>/dev/null
    [ -n "$BACKEND_PID" ]  && wait "$BACKEND_PID"  2>/dev/null
    [ -n "$FRONTEND_PID" ] && wait "$FRONTEND_PID" 2>/dev/null
    echo "All services stopped."
}
trap cleanup EXIT INT TERM

echo "=== Claude Code Analyzer ==="
echo ""

# 1. Monitor
echo "[1/3] Starting monitor service..."
cd "$ROOT_DIR/monitor"
uv run python -m src.main &
MONITOR_PID=$!

# 2. Backend
echo "[2/3] Starting backend service (http://localhost:8000)..."
cd "$ROOT_DIR/backend"
uv run uvicorn src.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# 3. Frontend
echo "[3/3] Starting frontend service (http://localhost:5173)..."
cd "$ROOT_DIR/frontend"
if [ ! -d "node_modules" ]; then
    echo "  Installing frontend dependencies..."
    npm install --silent
fi
npm run dev &
FRONTEND_PID=$!

echo ""
echo "All services running:"
echo "  Monitor:  PID $MONITOR_PID"
echo "  Backend:  http://localhost:8000  (PID $BACKEND_PID)"
echo "  Frontend: http://localhost:5173  (PID $FRONTEND_PID)"
echo ""
echo "Press Ctrl+C to stop all services."

wait

