#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$ROOT_DIR/.env"

if [ -f "$ENV_FILE" ]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

cd "$ROOT_DIR/backend"

HOST_VALUE="${BACKEND_HOST:-0.0.0.0}"
PORT_VALUE="${BACKEND_PORT:-8000}"

exec uvicorn app.main:app --host "$HOST_VALUE" --port "$PORT_VALUE" --reload
