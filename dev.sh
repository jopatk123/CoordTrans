#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BACKEND_SCRIPT="$ROOT_DIR/dev-backend.sh"
FRONTEND_SCRIPT="$ROOT_DIR/dev-frontend.sh"

if [ ! -x "$BACKEND_SCRIPT" ] || [ ! -x "$FRONTEND_SCRIPT" ]; then
  chmod +x "$BACKEND_SCRIPT" "$FRONTEND_SCRIPT"
fi

"$BACKEND_SCRIPT" &
BACKEND_PID=$!

"$FRONTEND_SCRIPT" &
FRONTEND_PID=$!

cleanup() {
  echo "Shutting down development processes..."
  kill "$BACKEND_PID" "$FRONTEND_PID" >/dev/null 2>&1 || true
}

trap cleanup EXIT

wait
