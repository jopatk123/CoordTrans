from pydantic_settings import BaseSettings
from pydantic import ConfigDict, Field


class Settings(BaseSettings):
    """应用配置类 - 所有配置项可通过环境变量覆盖"""
    
    model_config = ConfigDict(
        env_file=".env",
        extra="ignore"  # 忽略额外的配置项
    )
    
    # ========== 高德地图 API 配置 ==========
    AMAP_KEY: str = Field(default="", description="高德地图 API Key")
    AMAP_BASE_URL: str = Field(
        default="https://restapi.amap.com/v3",
        description="高德地图 API 基础 URL"
    )
    
    # ========== 请求配置 ==========
    REQUEST_TIMEOUT: float = Field(
        default=10.0, 
        ge=1.0, 
        le=60.0,
        description="单个请求超时时间（秒）"
    )
    BATCH_CONCURRENCY: int = Field(
        default=10, 
        ge=1, 
        le=50,
        description="批量请求并发数"
    )
    RETRY_TIMES: int = Field(
        default=2, 
        ge=0, 
        le=5,
        description="请求失败重试次数"
    )
    
    # ========== 批量处理限制 ==========
    MAX_BATCH_SIZE: int = Field(
        default=1000, 
        ge=1, 
        le=10000,
        description="单次批量处理最大行数"
    )
    MAX_FILE_SIZE: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        ge=1024,
        description="上传文件最大大小（字节）"
    )
    MAX_ADDRESS_LENGTH: int = Field(
        default=200, 
        ge=10, 
        le=500,
        description="地址最大字符长度"
    )
    MAX_CITY_LENGTH: int = Field(
        default=50, 
        ge=5, 
        le=100,
        description="城市名最大字符长度"
    )
    
    # ========== 服务配置 ==========
    BACKEND_PORT: int = Field(default=8000, description="后端服务端口")
    BACKEND_HOST: str = Field(default="0.0.0.0", description="后端服务地址")
    FRONTEND_PORT: int = Field(default=5173, description="前端服务端口")
    
    # ========== 应用信息 ==========
    APP_NAME: str = Field(default="CoordTrans API", description="应用名称")
    APP_VERSION: str = Field(default="1.0.0", description="应用版本")
    APP_DESCRIPTION: str = Field(
        default="高德地图经纬度转换工具 API - 支持地址与经纬度的相互转换",
        description="应用描述"
    )


settings = Settings()
