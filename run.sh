#!/usr/bin/env bash
# Start all three Claude Code Analyzer services.
# Usage: ./run.sh

set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

cleanup() {
    echo ""
    echo "Shutting down services..."
    kill $MONITOR_PID $BACKEND_PID $FRONTEND_PID 2>/dev/null
    wait $MONITOR_PID $BACKEND_PID $FRONTEND_PID 2>/dev/null
    echo "All services stopped."
}
trap cleanup EXIT INT TERM

echo "=== Claude Code Analyzer ==="
echo ""

# 1. Monitor
echo "[1/3] Starting monitor service..."
cd "$ROOT_DIR/monitor"
uv run python src/main.py &
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
