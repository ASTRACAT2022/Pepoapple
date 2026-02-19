from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Pepoapple Core"
    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8080
    database_url: str = "postgresql+psycopg://pepoapple:pepoapple@localhost:5432/pepoapple"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    rate_limit_per_minute: int = 120
    backup_dir: str = "./backups"
    webhook_timeout_seconds: int = 5

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
