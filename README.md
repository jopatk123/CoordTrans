# CoordTrans - 高德地图经纬度转换工具

## 项目简介

这是一个基于 Web 的经纬度与地址相互转换工具，核心功能依赖于高德地图 API。项目采用前后端分离架构，支持单一部署（Docker）。

## 功能特性

1. **地址转经纬度 (Geocoding)**: 输入详细地址，获取经纬度坐标。
2. **经纬度转地址 (Reverse Geocoding)**: 输入经纬度，获取详细地址及周边信息。
3. **批量处理**: 支持 Excel/CSV 文件上传或批量文本输入，进行大批量数据的转换。
4. **行政区划查询**: 支持查询乡镇、街道等详细行政信息。
5. **结果导出**: 支持将批量查询结果导出为 Excel/CSV。

## 技术栈

- **前端**: React + Vite + Ant Design + Tailwind CSS
- **后端**: Python + FastAPI + Pandas (用于数据处理)
- **部署**: Docker (多阶段构建，后端托管前端静态资源)

## 目录结构

```text
CoordTrans/
    ├── backend/              # Python FastAPI 后端
│   ├── app/
│   │   ├── main.py       # 入口文件
│   │   ├── api.py        # 接口定义
│   │   ├── services.py   # 高德 API 封装
│   │   ├── config.py     # 配置管理
│   │   ├── errors.py     # 统一错误处理
│   │   └── utils.py      # 通用工具函数
│   ├── tests/            # 后端测试
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/             # React 前端
│   ├── src/
│   │   └── __tests__/    # 前端测试
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml    # 生产部署配置
├── Makefile              # 常用命令快捷方式
├── dev-backend.sh        # 后端开发脚本
├── dev-frontend.sh       # 前端开发脚本
├── scripts/run_tests.sh  # 一键测试脚本
└── README.md
```

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd CoordTrans

# 复制环境变量模版并配置
cp .env.example .env
```

编辑 `.env` 文件，填写你的高德地图 API Key：

```dotenv
AMAP_KEY=your_amap_api_key_here
```

> 💡 API Key 可从 [高德开放平台](https://lbs.amap.com/) 申请

### 2. 安装依赖

```bash
make install
```

或手动安装：

```bash
# 后端
cd backend && pip install -r requirements.txt

# 前端
cd frontend && npm install
```

### 3. 启动开发环境

- 启动后端：`./dev-backend.sh`（默认监听 `http://localhost:8000`）
- 启动前端：`./dev-frontend.sh`（默认监听 `http://localhost:5173`）

## API 文档

项目内置 OpenAPI 文档，启动后端服务后访问：

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

### 主要接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/geo` | POST | 地址转经纬度 |
| `/api/regeo` | POST | 经纬度转地址 |
| `/api/batch/file/geo` | POST | 批量地址转经纬度（文件上传） |
| `/api/batch/file/regeo` | POST | 批量经纬度转地址（文件上传） |
| `/health` | GET | 健康检查 |

## 运行测试

```bash
# 运行所有测试
make test

# 或使用一键脚本
./scripts/run_tests.sh

# 单独运行后端/前端测试
make test-backend
make test-frontend
```

## Docker 部署

### 构建镜像

```bash
make build
# 或
docker build -t coordtrans:latest -f backend/Dockerfile .
```

### 运行容器

```bash
docker-compose up -d
```

服务将在 `http://localhost:60000` 启动。

## 配置说明

所有配置项均可通过环境变量覆盖：

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `AMAP_KEY` | - | 高德地图 API Key（必填） |
| `BACKEND_PORT` | 8000 | 后端服务端口 |
| `BACKEND_HOST` | 0.0.0.0 | 后端服务地址 |
| `MAX_BATCH_SIZE` | 1000 | 批量处理最大行数 |
| `MAX_FILE_SIZE` | 10485760 | 上传文件最大大小（字节） |
| `REQUEST_TIMEOUT` | 10.0 | API 请求超时时间（秒） |
| `BATCH_CONCURRENCY` | 10 | 批量请求并发数 |

## 开发指南

### 项目结构说明

- `backend/app/config.py` - 配置管理，所有可配置项集中管理
- `backend/app/errors.py` - 统一错误处理和响应格式
- `backend/app/utils.py` - 通用工具函数，避免代码重复
- `backend/app/services.py` - 高德 API 封装，支持重试和并发控制

### 代码规范

- 后端使用 `flake8` 进行代码检查
- 前端使用 ESLint 进行代码检查
- 所有测试需在 CI 中通过后方可合并

## License

MIT License
