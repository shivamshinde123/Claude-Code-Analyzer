# Start all three Claude Code Analyzer services.
# Usage: .\run.ps1

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "=== Claude Code Analyzer ===" -ForegroundColor Cyan
Write-Host ""

# 1. Monitor
Write-Host "[1/3] Starting monitor service..." -ForegroundColor Green
$monitor = Start-Process -NoNewWindow -PassThru -FilePath "cmd.exe" `
    -ArgumentList "/c uv run python -m src.main" `
    -WorkingDirectory "$RootDir\monitor"

# 2. Backend
Write-Host "[2/3] Starting backend service (http://localhost:8000)..." -ForegroundColor Green
$backend = Start-Process -NoNewWindow -PassThru -FilePath "cmd.exe" `
    -ArgumentList "/c uv run uvicorn src.main:app --host 127.0.0.1 --port 8000" `
    -WorkingDirectory "$RootDir\backend"

# 3. Frontend
Write-Host "[3/3] Starting frontend service (http://localhost:5173)..." -ForegroundColor Green
if (-not (Test-Path "$RootDir\frontend\node_modules")) {
    Write-Host "  Installing frontend dependencies..." -ForegroundColor Gray
    Start-Process -NoNewWindow -Wait -FilePath "cmd.exe" `
        -ArgumentList "/c npm install --silent" `
        -WorkingDirectory "$RootDir\frontend"
}
$frontend = Start-Process -NoNewWindow -PassThru -FilePath "cmd.exe" `
    -ArgumentList "/c npm run dev" `
    -WorkingDirectory "$RootDir\frontend"

Write-Host ""
Write-Host "All services running:" -ForegroundColor Cyan
Write-Host "  Monitor:  PID $($monitor.Id)"
Write-Host "  Backend:  http://localhost:8000  (PID $($backend.Id))"
Write-Host "  Frontend: http://localhost:5173  (PID $($frontend.Id))"
Write-Host ""
Write-Host "Press Ctrl+C to stop all services."

try {
    Wait-Process -Id $monitor.Id, $backend.Id, $frontend.Id
} finally {
    Write-Host "`nShutting down services..." -ForegroundColor Yellow
    $monitor, $backend, $frontend | ForEach-Object {
        if (-not $_.HasExited) { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
    }
    Write-Host "All services stopped."
}

