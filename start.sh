#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

BACKEND_PORT="${BACKEND_PORT:-8000}"
BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

log() {
  printf '%s\n' "$*"
}

die() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

kill_port_processes() {
  local port="$1"
  local label="$2"
  local pids=""

  if command -v lsof >/dev/null 2>&1; then
    pids="$(lsof -ti tcp:"$port" 2>/dev/null || true)"
  fi

  if [ -z "$pids" ]; then
    return 0
  fi

  log "Stopping ${label} processes on port ${port}..."

  while IFS= read -r pid; do
    [ -n "$pid" ] || continue
    kill "$pid" 2>/dev/null || true
  done <<EOF
$pids
EOF

  pids=""
  if command -v lsof >/dev/null 2>&1; then
    pids="$(lsof -ti tcp:"$port" 2>/dev/null || true)"
  fi

  while IFS= read -r pid; do
    [ -n "$pid" ] || continue
    kill -9 "$pid" 2>/dev/null || true
  done <<EOF
$pids
EOF
}

start_backend() {
  if [ ! -x "$BACKEND_DIR/.venv/bin/python" ]; then
    die "backend/.venv not found. Run 'make install' first."
  fi

  log "Starting backend on http://localhost:${BACKEND_PORT}..."
  (
    cd "$BACKEND_DIR"
    exec .venv/bin/python -m uvicorn app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" --reload
  ) &
  BACKEND_PID=$!
}

start_frontend() {
  if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    die "frontend/node_modules not found. Run 'cd frontend && npm ci' first."
  fi

  log "Starting frontend on http://localhost:${FRONTEND_PORT}..."
  (
    cd "$FRONTEND_DIR"
    exec npm run dev -- --host 0.0.0.0 --port "$FRONTEND_PORT"
  ) &
  FRONTEND_PID=$!
}

cleanup() {
  local status="$?"

  if [ -n "${BACKEND_PID:-}" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi

  if [ -n "${FRONTEND_PID:-}" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi

  wait "${BACKEND_PID:-}" 2>/dev/null || true
  wait "${FRONTEND_PID:-}" 2>/dev/null || true

  exit "$status"
}

monitor_children() {
  while true; do
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
      die "backend process exited unexpectedly."
    fi

    if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
      die "frontend process exited unexpectedly."
    fi

    sleep 1
  done
}

trap cleanup INT TERM EXIT

kill_port_processes "$BACKEND_PORT" "backend"
kill_port_processes "$FRONTEND_PORT" "frontend"

start_backend
start_frontend

log "Backend ready: http://localhost:${BACKEND_PORT}"
log "Frontend ready: http://localhost:${FRONTEND_PORT}"

monitor_children