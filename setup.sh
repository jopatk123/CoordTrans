#!/bin/bash

# 项目设置脚本 - 首次运行时使用

set -e

echo "🚀 CoordTrans 项目初始化..."

# 1. 检查依赖
echo ""
echo "📋 检查系统依赖..."

if ! command -v docker &> /dev/null; then
    echo "❌ 未找到 Docker，请先安装 Docker"
    exit 1
fi
echo "✅ Docker 已安装"

if ! command -v docker-compose &> /dev/null; then
    echo "❌ 未找到 Docker Compose，请先安装"
    exit 1
fi
echo "✅ Docker Compose 已安装"

# 2. 创建 .env 文件
echo ""
echo "📝 设置环境变量..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ 已创建 .env 文件"
    echo "⚠️  请编辑 .env 文件并填写你的高德地图 API Key"
else
    echo "ℹ️  .env 文件已存在"
fi

# 3. 设置脚本权限
echo ""
echo "🔧 设置脚本权限..."
chmod +x dev.sh dev-backend.sh dev-frontend.sh
echo "✅ 脚本权限已设置"

# 4. 提示后续步骤
echo ""
echo "✨ 初始化完成！"
echo ""
echo "📌 后续步骤："
echo "   1. 编辑 .env 文件，填写 AMAP_KEY"
echo "   2. 运行 'make dev' 或 './dev.sh' 启动开发环境"
echo "   3. 访问 http://localhost:5173 查看前端"
echo "   4. 访问 http://localhost:8000/docs 查看 API 文档"
echo ""
echo "📚 更多信息请查看 README.md 和 CONTRIBUTING.md"
