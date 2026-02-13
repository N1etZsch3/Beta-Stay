from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "BetaStay"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/betastay"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/betastay"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Dashscope
    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_MODEL: str = "qwen-max"

    # JWT
    SECRET_KEY: str = "betastay-secret-key-change-in-production"
    ALGORITHM: str = "HS256"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
