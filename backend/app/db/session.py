from pathlib import Path
import sqlite3

from app.core.config import get_settings

GOOGLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS google_connections (
    user_sub TEXT PRIMARY KEY,
    email TEXT,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    scopes_json TEXT NOT NULL,
    expires_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _resolve_sqlite_path(database_url: str) -> Path:
    if not database_url.startswith("sqlite:///"):
        raise RuntimeError("DATABASE_URL must use sqlite:/// for the built-in Google token store.")

    raw_path = database_url.removeprefix("sqlite:///")
    if raw_path == ":memory:":
        return Path(":memory:")

    if raw_path.startswith("/") and len(raw_path) > 2 and raw_path[2] == ":":
        raw_path = raw_path.lstrip("/")

    path = Path(raw_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def get_db_connection() -> sqlite3.Connection:
    database_path = _resolve_sqlite_path(get_settings().database_url)

    if str(database_path) != ":memory:":
        database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(database_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.executescript(GOOGLE_SCHEMA)
    return connection
