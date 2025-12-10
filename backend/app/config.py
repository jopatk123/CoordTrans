from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        extra="ignore"  # 忽略额外的配置项
    )
    
    AMAP_KEY: str = ""
    BACKEND_PORT: int = 8000
    BACKEND_HOST: str = "0.0.0.0"
    FRONTEND_PORT: int = 5173

settings = Settings()
