"""统一错误处理模块"""
import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from typing import Optional, Any

logger = logging.getLogger(__name__)


class ApiResponse(BaseModel):
    """统一 API 响应格式"""
    status: str  # "success" or "error"
    code: int = 200
    msg: str = ""
    data: Optional[Any] = None

    @classmethod
    def success(cls, data: Any = None, msg: str = "操作成功") -> dict:
        """成功响应"""
        return cls(status="success", code=200, msg=msg, data=data).model_dump()

    @classmethod
    def error(cls, msg: str, code: int = 400, data: Any = None) -> dict:
        """错误响应"""
        return cls(status="error", code=code, msg=msg, data=data).model_dump()

    @classmethod
    def not_found(cls, msg: str = "未找到结果") -> dict:
        """未找到响应"""
        return cls(status="failed", code=404, msg=msg, data=None).model_dump()


class AppError(Exception):
    """应用自定义错误基类"""
    
    def __init__(
        self, 
        msg: str, 
        code: int = 400, 
        detail: Optional[str] = None
    ):
        self.msg = msg
        self.code = code
        self.detail = detail or msg
        super().__init__(self.msg)


class ValidationError(AppError):
    """输入验证错误"""
    
    def __init__(self, msg: str, detail: Optional[str] = None):
        super().__init__(msg=msg, code=422, detail=detail)


class ServiceUnavailableError(AppError):
    """外部服务不可用错误"""
    
    def __init__(self, msg: str = "服务暂时不可用，请稍后重试"):
        super().__init__(msg=msg, code=502)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """处理应用自定义错误"""
    logger.warning(f"AppError: {exc.msg} (code={exc.code})")
    return JSONResponse(
        status_code=exc.code,
        content=ApiResponse.error(msg=exc.msg, code=exc.code)
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """处理 HTTP 异常"""
    logger.warning(f"HTTPException: {exc.detail} (status={exc.status_code})")
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse.error(
            msg=str(exc.detail), 
            code=exc.status_code
        )
    )


async def validation_exception_handler(
    request: Request, 
    exc: RequestValidationError
) -> JSONResponse:
    """处理请求验证错误"""
    errors = exc.errors()
    # 提取第一个错误的友好信息
    if errors:
        first_error = errors[0]
        field = ".".join(str(loc) for loc in first_error.get("loc", []))
        msg = first_error.get("msg", "验证失败")
        detail = f"{field}: {msg}" if field else msg
    else:
        detail = "请求参数验证失败"
    
    logger.warning(f"ValidationError: {detail}")
    return JSONResponse(
        status_code=422,
        content=ApiResponse.error(msg=detail, code=422)
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理未知异常"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ApiResponse.error(
            msg="服务器内部错误，请稍后重试", 
            code=500
        )
    )
