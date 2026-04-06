from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json

from cryptography.fernet import Fernet

from app.core.config import get_settings
from app.db.session import get_db_connection


@dataclass
class GoogleConnectionRecord:
    user_sub: str
    email: str | None
    access_token: str
    refresh_token: str
    scopes: list[str]
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime


def _b64encode(value: bytes) -> str:
    return urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return urlsafe_b64decode(f"{value}{padding}")


def _get_fernet() -> Fernet:
    token_encryption_key = get_settings().token_encryption_key
    if not token_encryption_key:
        raise RuntimeError(
            "TOKEN_ENCRYPTION_KEY must be configured before Google connections can be stored."
        )

    try:
        return Fernet(token_encryption_key.encode("utf-8"))
    except Exception as exc:  # pragma: no cover - depends on local env secrets
        raise RuntimeError(
            "TOKEN_ENCRYPTION_KEY must be a valid Fernet key. Generate one with "
            "`python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"`."
        ) from exc


def _encrypt(value: str) -> str:
    return _get_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def _decrypt(value: str) -> str:
    return _get_fernet().decrypt(value.encode("utf-8")).decode("utf-8")


def _state_secret() -> bytes:
    token_encryption_key = get_settings().token_encryption_key
    if not token_encryption_key:
        raise RuntimeError(
            "TOKEN_ENCRYPTION_KEY must be configured before Google OAuth can be used."
        )
    return token_encryption_key.encode("utf-8")


def _serialize_datetime(value: datetime | None) -> str | None:
    return value.astimezone(timezone.utc).isoformat() if value else None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def create_signed_state(user_sub: str, expires_in_minutes: int = 10) -> str:
    payload = {
        "sub": user_sub,
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)).timestamp()),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = hmac.new(_state_secret(), payload_bytes, hashlib.sha256).digest()
    return f"{_b64encode(payload_bytes)}.{_b64encode(signature)}"


def verify_signed_state(state: str) -> str:
    try:
        encoded_payload, encoded_signature = state.split(".", 1)
    except ValueError as exc:
        raise RuntimeError("Google OAuth state is malformed.") from exc

    payload_bytes = _b64decode(encoded_payload)
    expected_signature = hmac.new(_state_secret(), payload_bytes, hashlib.sha256).digest()
    actual_signature = _b64decode(encoded_signature)

    if not hmac.compare_digest(expected_signature, actual_signature):
        raise RuntimeError("Google OAuth state validation failed.")

    payload = json.loads(payload_bytes.decode("utf-8"))
    expires_at = payload.get("exp")
    user_sub = payload.get("sub")
    if not isinstance(expires_at, int) or not isinstance(user_sub, str):
        raise RuntimeError("Google OAuth state payload is invalid.")
    if datetime.now(timezone.utc).timestamp() > expires_at:
        raise RuntimeError("Google OAuth state has expired. Start the connection flow again.")
    return user_sub


def _row_to_record(row) -> GoogleConnectionRecord:
    return GoogleConnectionRecord(
        user_sub=row["user_sub"],
        email=row["email"],
        access_token=_decrypt(row["access_token"]),
        refresh_token=_decrypt(row["refresh_token"]),
        scopes=json.loads(row["scopes_json"]),
        expires_at=_parse_datetime(row["expires_at"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def get_google_connection(user_sub: str) -> GoogleConnectionRecord | None:
    with get_db_connection() as connection:
        row = connection.execute(
            """
            SELECT user_sub, email, access_token, refresh_token, scopes_json, expires_at, created_at, updated_at
            FROM google_connections
            WHERE user_sub = ?
            """,
            (user_sub,),
        ).fetchone()

    if row is None:
        return None
    return _row_to_record(row)


def upsert_google_connection(
    user_sub: str,
    token_payload: dict[str, object],
    *,
    email: str | None = None,
) -> GoogleConnectionRecord:
    existing_connection = get_google_connection(user_sub)
    now = datetime.now(timezone.utc)

    access_token = token_payload.get("access_token")
    if not isinstance(access_token, str):
        raise RuntimeError("Google did not return an access token.")

    refresh_token = token_payload.get("refresh_token")
    if not isinstance(refresh_token, str):
        refresh_token = existing_connection.refresh_token if existing_connection else None
    if not refresh_token:
        raise RuntimeError(
            "Google did not return a refresh token. Remove the app from your Google account and reconnect."
        )

    scope_value = token_payload.get("scope")
    if isinstance(scope_value, str):
        scopes = sorted(scope_value.split())
    elif existing_connection:
        scopes = existing_connection.scopes
    else:
        scopes = []

    expires_in = token_payload.get("expires_in")
    expires_at = existing_connection.expires_at if existing_connection else None
    if isinstance(expires_in, int):
        expires_at = now + timedelta(seconds=expires_in)

    connection_email = email or (existing_connection.email if existing_connection else None)
    created_at = existing_connection.created_at if existing_connection else now

    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO google_connections (
                user_sub,
                email,
                access_token,
                refresh_token,
                scopes_json,
                expires_at,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_sub) DO UPDATE SET
                email = excluded.email,
                access_token = excluded.access_token,
                refresh_token = excluded.refresh_token,
                scopes_json = excluded.scopes_json,
                expires_at = excluded.expires_at,
                updated_at = excluded.updated_at
            """,
            (
                user_sub,
                connection_email,
                _encrypt(access_token),
                _encrypt(refresh_token),
                json.dumps(scopes),
                _serialize_datetime(expires_at),
                created_at.isoformat(),
                now.isoformat(),
            ),
        )
        connection.commit()

    stored_connection = get_google_connection(user_sub)
    if stored_connection is None:
        raise RuntimeError("The Google connection could not be stored.")
    return stored_connection


def delete_google_connection(user_sub: str) -> bool:
    with get_db_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM google_connections WHERE user_sub = ?",
            (user_sub,),
        )
        connection.commit()
    return cursor.rowcount > 0
