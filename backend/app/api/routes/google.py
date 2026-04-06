from datetime import datetime
from typing import Any
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from app.core.auth import require_auth
from app.core.config import get_settings
from app.google.client import GoogleIntegrationError, build_google_authorization_url, exchange_google_code
from app.google.storage import delete_google_connection, get_google_connection
from app.google.workspace import GoogleConnectionMissingError, build_google_summary

router = APIRouter(prefix="/google", tags=["google"])


class GoogleConnectResponse(BaseModel):
    auth_url: str


class GoogleConnectionStatusResponse(BaseModel):
    connected: bool
    email: str | None = None
    scopes: list[str] = Field(default_factory=list)
    updated_at: datetime | None = None


class GoogleDisconnectResponse(BaseModel):
    disconnected: bool


class GoogleSummaryRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=4000)


class GoogleSummaryResponse(BaseModel):
    response: str
    email_count: int
    event_count: int
    connected_email: str | None = None


def _get_user_sub(claims: dict[str, Any]) -> str:
    user_sub = claims.get("sub")
    if not isinstance(user_sub, str) or not user_sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The Auth0 token did not include a subject for this user.",
        )
    return user_sub


def _redirect_to_frontend(status_value: str, message: str) -> RedirectResponse:
    query = urlencode({"google": status_value, "message": message})
    target = f"{get_settings().app_base_url}/?{query}"
    return RedirectResponse(target, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/status", response_model=GoogleConnectionStatusResponse)
def google_status(claims: dict[str, Any] = Depends(require_auth)) -> GoogleConnectionStatusResponse:
    connection = get_google_connection(_get_user_sub(claims))
    if connection is None:
        return GoogleConnectionStatusResponse(connected=False)

    return GoogleConnectionStatusResponse(
        connected=True,
        email=connection.email,
        scopes=connection.scopes,
        updated_at=connection.updated_at,
    )


@router.post("/connect", response_model=GoogleConnectResponse)
def google_connect(claims: dict[str, Any] = Depends(require_auth)) -> GoogleConnectResponse:
    try:
        return GoogleConnectResponse(auth_url=build_google_authorization_url(_get_user_sub(claims)))
    except GoogleIntegrationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.get("/callback")
def google_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
) -> RedirectResponse:
    if error:
        message = error_description or f"Google returned an OAuth error: {error}"
        return _redirect_to_frontend("error", message)

    if not code or not state:
        return _redirect_to_frontend("error", "Google did not return the expected OAuth callback values.")

    try:
        connection = exchange_google_code(code, state)
    except (GoogleIntegrationError, RuntimeError) as exc:
        return _redirect_to_frontend("error", str(exc))

    account_label = connection.email or "your Google account"
    return _redirect_to_frontend(
        "connected",
        f"Connected {account_label} for Gmail and Calendar summaries.",
    )


@router.delete("/connection", response_model=GoogleDisconnectResponse)
def google_disconnect(claims: dict[str, Any] = Depends(require_auth)) -> GoogleDisconnectResponse:
    disconnected = delete_google_connection(_get_user_sub(claims))
    return GoogleDisconnectResponse(disconnected=disconnected)


@router.post("/summary", response_model=GoogleSummaryResponse)
def google_summary(
    payload: GoogleSummaryRequest,
    claims: dict[str, Any] = Depends(require_auth),
) -> GoogleSummaryResponse:
    user_sub = _get_user_sub(claims)

    try:
        result = build_google_summary(user_sub, payload.prompt)
        return GoogleSummaryResponse(
            response=str(result["response"]),
            email_count=int(result["email_count"]),
            event_count=int(result["event_count"]),
            connected_email=(
                str(result["connected_email"]) if result["connected_email"] is not None else None
            ),
        )
    except GoogleConnectionMissingError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
