#!/usr/bin/env bash
# CAP CDSS — Local dev server (backend + frontend in one command)
# Usage: ./dev.sh
# Press Ctrl+C to stop both.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

# ── Ensure Python venv + backend deps ──
if [ ! -d "$ROOT/.venv" ]; then
    echo "Creating Python venv..."
    python3 -m venv "$ROOT/.venv"
fi
if ! "$ROOT/.venv/bin/python" -c "import uvicorn; import nest_asyncio" 2>/dev/null; then
    echo "Installing backend dependencies..."
    "$ROOT/.venv/bin/pip" install -q -e "$ROOT[dev,server]"
fi

# ── Ensure frontend node_modules ──
if [ ! -d "$ROOT/frontend/node_modules" ]; then
    echo "Installing frontend dependencies..."
    (cd "$ROOT/frontend" && npm ci --no-audit --no-fund)
fi

# ── Start servers ──
cleanup() {
    kill $BACK_PID $FRONT_PID 2>/dev/null
    wait $BACK_PID $FRONT_PID 2>/dev/null
    echo "Stopped."
}
trap cleanup EXIT

(cd "$ROOT" && .venv/bin/uvicorn server.main:app --port 8000 --reload) &
BACK_PID=$!

(cd "$ROOT/frontend" && npx vite --port 5173) &
FRONT_PID=$!

echo ""
echo "  Open: http://localhost:5173"
echo "  Ctrl+C to stop"
echo ""

wait
