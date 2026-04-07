from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path

from dotenv import dotenv_values

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent


def _load_environment() -> None:
    # Merge repo env files explicitly so more specific local files can override
    # empty placeholders in broader defaults, while real shell env vars still win.
    merged_env: dict[str, str] = {}

    for env_path in (
        REPO_ROOT / ".env",
        BACKEND_DIR / ".env",
        REPO_ROOT / "frontend" / ".env.local",
    ):
        if not env_path.exists():
            continue

        merged_env.update(
            {
                key: value
                for key, value in dotenv_values(env_path).items()
                if value is not None
            }
        )

    for key, value in merged_env.items():
        existing_value = os.environ.get(key)
        if existing_value is None or existing_value == "":
            os.environ[key] = value


_load_environment()


def _normalize_domain(domain: str | None) -> str | None:
    if not domain:
        return None
    return domain.removeprefix("https://").rstrip("/")


def _normalize_url(url: str | None, default: str) -> str:
    if not url:
        return default
    return url.rstrip("/")


def _parse_origins(origins: str | None) -> tuple[str, ...]:
    if not origins:
        return ("http://localhost:3000", "http://127.0.0.1:3000")
    return tuple(origin.strip() for origin in origins.split(",") if origin.strip())


def _default_database_url() -> str:
    database_path = REPO_ROOT / "backend" / "data" / "authorized_to_act.db"
    return f"sqlite:///{database_path.as_posix()}"


@dataclass(frozen=True)
class Settings:
    auth0_domain: str | None
    auth0_audience: str | None
    cors_origins: tuple[str, ...]
    app_base_url: str
    database_url: str
    google_client_id: str | None
    google_client_secret: str | None
    google_redirect_uri: str | None
    token_encryption_key: str | None

    @property
    def auth0_enabled(self) -> bool:
        return bool(self.auth0_domain and self.auth0_audience)

    @property
    def auth0_issuer(self) -> str | None:
        if not self.auth0_domain:
            return None
        return f"https://{self.auth0_domain}/"

    @property
    def auth0_jwks_url(self) -> str | None:
        if not self.auth0_issuer:
            return None
        return f"{self.auth0_issuer}.well-known/jwks.json"

    @property
    def google_enabled(self) -> bool:
        return bool(
            self.google_client_id
            and self.google_client_secret
            and self.google_redirect_uri
            and self.token_encryption_key
        )


@lru_cache
def get_settings() -> Settings:
    return Settings(
        auth0_domain=_normalize_domain(os.getenv("AUTH0_DOMAIN")),
        auth0_audience=os.getenv("AUTH0_AUDIENCE"),
        cors_origins=_parse_origins(os.getenv("CORS_ORIGINS")),
        app_base_url=_normalize_url(os.getenv("APP_BASE_URL"), "http://localhost:3000"),
        database_url=os.getenv("DATABASE_URL", _default_database_url()),
        google_client_id=os.getenv("GOOGLE_CLIENT_ID"),
        google_client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        google_redirect_uri=os.getenv("GOOGLE_REDIRECT_URI"),
        token_encryption_key=os.getenv("TOKEN_ENCRYPTION_KEY"),
    )
