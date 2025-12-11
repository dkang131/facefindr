import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:123456@localhost:5432/facefindr"
    )
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:7219")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "facefinder_secret_key")
    MASTER_ADMIN_TOKEN: str = os.getenv("MASTER_ADMIN_TOKEN", "facefindr_master_token")
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")

    # class Config:
    #     env_file = ".env"

settings = Settings()