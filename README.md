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
├── backend/            # Python FastAPI 后端
│   ├── app/
│   │   ├── main.py     # 入口文件
│   │   ├── api.py      # 接口定义
│   │   └── services.py # 高德 API 封装
│   ├── tests/          # 后端测试
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/           # React 前端
│   ├── src/
│   │   └── __tests__/  # 前端测试
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml  # 生产部署配置
├── Makefile           # 常用命令快捷方式
├── dev.sh / dev-*.sh  # 本地开发快捷脚本
├── scripts/run_tests.sh # 一键测试脚本
└── README.md
```

## 快速开始

1. 复制环境变量模版：`cp .env.example .env`，并填写 `AMAP_KEY` 等配置。
2. 安装依赖：`make install`（分别安装后端和前端依赖）。
3. 启动本地开发环境：
	- 完整前后端：`./dev.sh`（按下 `Ctrl+C` 可同时停止两个进程）。
	- 仅后端：`./dev-backend.sh`（默认监听 `BACKEND_HOST` 与 `BACKEND_PORT`）。
	- 仅前端：`./dev-frontend.sh`（默认监听 `FRONTEND_PORT`）。

## 运行测试

- 推荐使用一键脚本：`./scripts/run_tests.sh`（先运行后端 pytest，再运行前端 Vitest）。
- 也可以通过 `make test`、`make test-backend`、`make test-frontend` 分别执行。

所有测试均会在 CI 中执行，请在提交前确保它们通过。
