from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
import os

from .api import router
from .config import settings
from .errors import (
    AppError,
    app_error_handler,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)

# 创建 FastAPI 应用，配置 OpenAPI 文档
app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    docs_url="/api/docs",      # Swagger UI 文档地址
    redoc_url="/api/redoc",    # ReDoc 文档地址
    openapi_url="/api/openapi.json",  # OpenAPI JSON schema
    openapi_tags=[
        {
            "name": "geocoding",
            "description": "地址与经纬度转换接口",
        },
        {
            "name": "batch",
            "description": "批量处理接口 - 支持 Excel/CSV 文件上传",
        },
        {
            "name": "health",
            "description": "健康检查接口",
        },
    ]
)

# ========== 注册异常处理器 ==========
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# ========== CORS 配置 ==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== 注册路由 ==========
app.include_router(router, prefix="/api")

# ========== 静态文件服务 (生产模式) ==========
# In development, we use Vite dev server.
# In production, we mount the built frontend to /app/static
static_dir = os.path.join(os.path.dirname(__file__), "../static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


@app.get("/health", tags=["health"], summary="健康检查")
def health_check():
    """
    健康检查接口
    
    返回服务运行状态，用于容器健康检查和负载均衡器探测。
    """
    return {"status": "ok", "version": settings.APP_VERSION}
