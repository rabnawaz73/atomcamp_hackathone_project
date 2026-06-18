from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openrouter_api_key: str = ""
    openrouter_model: str = "deepseek/deepseek-chat"

    openweathermap_api_key: str = ""
    waqi_api_key: str = ""

    telegram_bot_token: str = ""

    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""

    database_url: str = "sqlite:///healthguardian.db"
    secret_key: str = "dev-secret-change-in-production"
    default_city: str = "London"


@lru_cache
def get_settings() -> Settings:
    return Settings()
