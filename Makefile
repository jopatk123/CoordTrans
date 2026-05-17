.PHONY: help dev dev-backend dev-frontend build test test-backend test-frontend clean install lint-frontend

help: ## 显示帮助信息
	@echo "可用命令:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## 安装所有依赖
	@echo "📦 安装后端依赖..."
	cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
	@echo "📦 安装前端依赖..."
	cd frontend && npm ci
	@echo "✅ 依赖安装完成"

dev: ## 使用 Docker Compose 启动完整开发环境
	docker-compose up --build

dev-backend: ## 启动后端开发服务器（本地）
	@chmod +x dev-backend.sh
	@./dev-backend.sh

dev-frontend: ## 启动前端开发服务器（本地）
	@chmod +x dev-frontend.sh
	@./dev-frontend.sh

build: ## 构建 Docker 镜像
	@echo "🏗️  构建 Docker 镜像..."
	docker build -t coordtrans:latest -f backend/Dockerfile .
	@echo "✅ 镜像构建完成"

test: test-backend test-frontend ## 运行所有测试

test-backend: ## 运行后端测试
	@echo "🧪 运行后端测试..."
	cd backend && .venv/bin/pytest tests/ -v --cov=app --cov-report=html --cov-report=term
	@echo "✅ 后端测试完成，查看 backend/htmlcov/index.html 获取覆盖率报告"

test-frontend: ## 运行前端测试
	@echo "🧪 运行前端测试..."
	cd frontend && npm run test
	@echo "✅ 前端测试完成"

test-coverage: ## 运行测试并生成覆盖率报告
	@echo "📊 生成测试覆盖率报告..."
	cd backend && .venv/bin/pytest tests/ --cov=app --cov-report=html --cov-report=term
	cd frontend && npm run test:coverage
	@echo "✅ 覆盖率报告已生成"

clean: ## 清理临时文件和缓存
	@echo "🧹 清理临时文件..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ 清理完成"

lint-backend: ## 检查后端代码格式
	@echo "🔍 检查后端代码..."
	cd backend && python -m pylint app/

lint-frontend: ## 检查前端代码
	@echo "🔍 检查前端代码..."
	cd frontend && npm run lint

format-backend: ## 格式化后端代码
	@echo "🎨 格式化后端代码..."
	cd backend && black app/
	@echo "✅ 后端代码格式化完成"

docker-up: ## 启动 Docker Compose 服务
	docker-compose up -d

docker-down: ## 停止 Docker Compose 服务
	docker-compose down

docker-logs: ## 查看 Docker Compose 日志
	docker-compose logs -f

.DEFAULT_GOAL := help
