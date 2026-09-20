from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_SECRET_KEYS = {"change-me", "change-me-in-production", ""}


class Settings(BaseSettings):
    app_name: str = "HandBase Web"
    app_env: str = "development"
    app_secret_key: str = "change-me"
    database_url: str = "postgresql+psycopg://handbase:handbase@db:5432/handbase"
    default_locale: str = "en"
    cors_origins: str = "http://localhost:5173,http://localhost:8000"
    app_build_revision: str = "unknown"

    # --- authentication -------------------------------------------------- #
    #: Access tokens are short-lived because they are not revocable; the
    #: refresh token in the database is the revocation point.
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 1_209_600  # 14 days
    invitation_ttl_hours: int = 168  # 7 days
    auth_cookie_name: str = "handbase_refresh"
    #: `None` means "secure in production, plain over http elsewhere" so local
    #: development works without TLS while production never sends the cookie
    #: over an unencrypted connection.
    auth_cookie_secure: bool | None = None
    auth_cookie_samesite: str = "lax"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}

    @property
    def cookie_secure(self) -> bool:
        if self.auth_cookie_secure is not None:
            return self.auth_cookie_secure
        return self.is_production

    def secret_key_is_insecure(self) -> bool:
        return self.app_secret_key.strip().lower() in INSECURE_SECRET_KEYS


@lru_cache
def get_settings() -> Settings:
    return Settings()
