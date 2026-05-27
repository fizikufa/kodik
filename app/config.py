"""Конфигурация приложения через переменные окружения."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    usd_to_rub: float = 90.0
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_secret: str = "dev-secret"
    database_url: str = "sqlite+aiosqlite:///./data/app.db"

    jwt_secret: str = "dev-jwt"
    jwt_alg: str = "HS256"
    jwt_expire_hours: int = 168

    admin_username: str = "admin"
    admin_password: str = "admin123"

    kodik_api_key: str = ""
    kodik_base_url: str = "https://api.kodikrouter.ru/v1"


settings = Settings()
