#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# AI Smart Irrigation Dashboard Startup Script
# Usage: bash start_dashboard.sh
# ─────────────────────────────────────────────────────────────────────────────

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "=== AI Smart Irrigation Dashboard Launcher ==="

# ── Step 1: Force-release port 8000 (handles TIME_WAIT and zombie uvicorn) ──
echo "[1/3] Releasing port 8000 if occupied..."
# fuser -k sends SIGKILL to any process holding the port
sudo fuser -k -KILL 8000/tcp 2>/dev/null && echo "  Killed process on port 8000." || echo "  Port 8000 was already free."

# Wait for OS to release the socket from TIME_WAIT
sleep 2

# ── Step 2: Activate virtualenv ──
echo "[2/3] Activating virtual environment..."
source venv/bin/activate

# ── Step 3: Start uvicorn ──
echo "[3/3] Starting Dashboard API on http://0.0.0.0:8000 ..."
exec env \
  PYTHONPATH="$PROJECT_DIR:$PROJECT_DIR/raspberry_pi" \
  DASHBOARD_START_RECEIVER=1 \
  uvicorn raspberry_pi.dashboard.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --timeout-graceful-shutdown 5
