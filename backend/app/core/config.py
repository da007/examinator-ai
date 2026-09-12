from typing import Optional
from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import ValidationInfo
import sys as _sys
if "pytest" in _sys.modules:
    import os as _os
    if _os.getenv("ENV", "").lower() != "testing":
        raise RuntimeError(
            "\n\n[SAFETY] Попытка запустить pytest без ENV=TESTING!\n"
            "Установи переменную: ENV=TESTING pytest ...\n"
            "Или добавь в pytest.ini: env = ENV=TESTING\n"
        )

# -------------------- PROJECT --------------------

class ProjectSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PROJECT_",
        extra="ignore"
    )

    NAME: str
    API_V1_STR: str
    
    
# -------------------- APP --------------------

class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="APP_",
        extra="ignore"
    )

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8


# -------------------- POSTGRES --------------------

class PostgresSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="POSTGRES_",
        extra="ignore"
    )

    USER: str
    PASSWORD: str
    SERVER: str
    DB: str
    PORT: int = 5432

    DATABASE_URL: Optional[PostgresDsn] = None

    @field_validator("PORT", mode="before")
    @classmethod
    def parse_port(cls, v: Optional[str], info: ValidationInfo):
        if isinstance(v, str):
            return int(v)
        return v
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info: ValidationInfo):
        if isinstance(v, str) and v:
            return v

        required = ["USER", "PASSWORD", "SERVER", "PORT", "DB"]

        missing = [k for k in required if not info.data.get(k)]
        if missing:
            raise ValueError(f"Missing DB config: {missing}")

        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=info.data["USER"],
            password=info.data["PASSWORD"],
            host=info.data["SERVER"],
            port=info.data["PORT"],
            path=info.data["DB"],
        )

# -------------------- REDIS --------------------

class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        extra="ignore"
    )

    HOST: str = "redis"
    PORT: int = 6379


# -------------------- S3 --------------------

class S3Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="S3_",
        extra="ignore"
    )

    ENDPOINT: str
    ACCESS_KEY: str
    SECRET_KEY: str
    BUCKET_NAME: str = "lectures"
    USE_SSL: bool = False


# -------------------- INIT --------------------

class InitSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="INIT_",
        extra="ignore"
    )

    SUPERUSER_ORG_ID: str
    SUPERUSER_EMAIL: str
    SUPERUSER_PASSWORD: str

# -------------------- LM_STUDIO --------------------

class LMStudioSettings(BaseSettings):
    """
    Настройки LM Studio (OpenAI-совместимый локальный API).
    Переменные окружения: LM_STUDIO_BASE_URL, LM_STUDIO_MODEL, LM_STUDIO_API_KEY.
    """
    model_config = SettingsConfigDict(
        env_prefix="LM_STUDIO_",
        extra="ignore"
    )

    MODEL: str
    BASE_URL: str = "http://localhost:1234"


# -------------------- ROOT --------------------

class Settings:
    project = ProjectSettings()
    app = AppSettings()
    postgres = PostgresSettings()
    redis = RedisSettings()
    s3 = S3Settings()
    init = InitSettings()
    lmStudio = LMStudioSettings()


settings = Settings()