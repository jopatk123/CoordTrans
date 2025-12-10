#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

run_backend_tests() {
  echo "Running backend tests..."
  pushd "$ROOT_DIR/backend" >/dev/null
  pytest
  popd >/dev/null
}

run_frontend_tests() {
  echo "Installing frontend dependencies (if needed) and running tests..."
  pushd "$ROOT_DIR/frontend" >/dev/null
  if [ ! -d node_modules ]; then
    npm install
  fi
  npm run test
  popd >/dev/null
}

run_backend_tests
run_frontend_tests

echo "All tests finished successfully."
