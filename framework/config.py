"""Typed, validated runtime configuration.

Values come from environment variables (prefix ``RC_``) or a local ``.env`` file,
so nothing environment-specific or secret is ever hardcoded in the suite.
"""

from functools import lru_cache

from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RC_", env_file=".env", extra="ignore")

    base_url: HttpUrl = Field(default=HttpUrl("http://localhost:3000"))
    admin_username: str = "e2e.admin"
    admin_password: SecretStr = SecretStr("E2e-Admin-Pass-1")
    api_timeout_s: float = 30.0
    # Default timeout for Playwright actions/assertions (ms). Auto-waiting replaces sleeps.
    ui_timeout_ms: int = 15_000

    @property
    def url(self) -> str:
        return str(self.base_url).rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()
