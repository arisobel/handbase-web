from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "HandBase Web"
    app_env: str = "development"
    app_secret_key: str = "change-me"
    database_url: str = "postgresql+psycopg://handbase:handbase@db:5432/handbase"
    default_locale: str = "en"
    cors_origins: str = "http://localhost:5173,http://localhost:8000"
    app_build_revision: str = "unknown"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()
