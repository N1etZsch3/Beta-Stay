from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    # App
    APP_NAME: str = "BetaStay"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    DATABASE_URL_SYNC: str = os.getenv("DATABASE_URL_SYNC")

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL")

    # Dashscope
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY")
    DASHSCOPE_MODEL: str = "qwen3-max-2026-01-23"
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = "HS256"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
