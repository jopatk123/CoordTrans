from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    AMAP_KEY: str = ""
    
    class Config:
        env_file = ".env"

settings = Settings()
