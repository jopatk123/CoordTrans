#!/usr/bin/env bash
# 一键运行前后端全量测试脚本
# 用法: ./scripts/run_tests.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "======================================"
echo "  CoordTrans 全量测试"
echo "======================================"

# ── 后端测试 ──────────────────────────────
echo ""
echo "🧪 [1/3] 后端单元测试 (pytest)"
cd "$REPO_ROOT/backend"
if [ ! -x ".venv/bin/pytest" ]; then
  echo "❌ 未找到 .venv，请先执行: make install"
  exit 1
fi
.venv/bin/pytest tests/ -v --cov=app --cov-report=term-missing
echo "✅ 后端测试通过"

# ── 后端 lint ─────────────────────────────
echo ""
echo "🔍 [2/3] 后端代码质量检查 (flake8)"
.venv/bin/flake8 app/
echo "✅ 后端 lint 通过"

# ── 前端测试 ──────────────────────────────
echo ""
echo "🧪 [3/3] 前端测试 (vitest)"
cd "$REPO_ROOT/frontend"
if [ ! -d "node_modules" ]; then
  echo "❌ 未找到 node_modules，请先执行: make install"
  exit 1
fi
npm test -- --run
echo "✅ 前端测试通过"

echo ""
echo "======================================"
echo "  ✅ 所有测试通过"
echo "======================================"
