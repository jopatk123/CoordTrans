#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$ROOT_DIR/.env"

if [ -f "$ENV_FILE" ]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

cd "$ROOT_DIR/frontend"

if [ ! -d node_modules ]; then
  npm install
fi

PORT_VALUE="${FRONTEND_PORT:-5173}"

exec npm run dev -- --host 0.0.0.0 --port "$PORT_VALUE"
