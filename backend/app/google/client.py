from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from html import unescape
from json import dumps, loads
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.config import get_settings
from app.google.storage import (
    GoogleConnectionRecord,
    create_signed_state,
    upsert_google_connection,
    verify_signed_state,
)
from app.models.task import TaskAttachment

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GMAIL_LIST_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
GMAIL_MESSAGE_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}"
GMAIL_ATTACHMENT_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}/attachments/{attachment_id}"
GMAIL_DRAFTS_URL = "https://gmail.googleapis.com/gmail/v1/users/me/drafts"
CALENDAR_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
CALENDAR_FREEBUSY_URL = "https://www.googleapis.com/calendar/v3/freeBusy"
GOOGLE_WORKSPACE_SCOPES = (
    "openid",
    "email",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
)


class GoogleIntegrationError(RuntimeError):
    """Raised when Google OAuth or API requests fail."""


@dataclass
class GmailAttachment:
    filename: str
    mime_type: str
    size: int
    text_preview: str | None = None


@dataclass
class GmailMessage:
    id: str
    sender: str
    subject: str
    snippet: str
    attachments: list[GmailAttachment]


@dataclass
class CalendarEvent:
    id: str
    title: str
    start: str
    end: str
    location: str | None
    html_link: str | None = None


@dataclass
class BusyWindow:
    start: str
    end: str


def _require_google_settings() -> tuple[str, str, str]:
    settings = get_settings()
    if not settings.google_client_id or not settings.google_client_secret or not settings.google_redirect_uri:
        raise GoogleIntegrationError(
            "GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REDIRECT_URI must be configured."
        )
    return settings.google_client_id, settings.google_client_secret, settings.google_redirect_uri


def _read_json_response(request: Request) -> dict[str, object]:
    try:
        with urlopen(request, timeout=20) as response:
            payload = response.read().decode("utf-8")
            return loads(payload)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise GoogleIntegrationError(
            f"Google request failed with {exc.code}: {detail}"
        ) from exc
    except URLError as exc:
        raise GoogleIntegrationError(
            "The backend could not reach Google. Check internet access and the Google API configuration."
        ) from exc


def _post_form(url: str, payload: dict[str, str]) -> dict[str, object]:
    encoded_payload = urlencode(payload).encode("utf-8")
    request = Request(
        url,
        data=encoded_payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    return _read_json_response(request)


def _get_json(url: str, access_token: str) -> dict[str, object]:
    request = Request(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )
    return _read_json_response(request)


def _post_json(url: str, access_token: str, payload: dict[str, object]) -> dict[str, object]:
    request = Request(
        url,
        data=dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    return _read_json_response(request)


def _decode_base64url(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")


def _decode_text_payload(value: str) -> str:
    return _decode_base64url(value).decode("utf-8", errors="replace")


def _strip_html(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    normalized_whitespace = re.sub(r"\s+", " ", unescape(without_tags))
    return normalized_whitespace.strip()


def build_google_authorization_url(user_sub: str) -> str:
    client_id, _, redirect_uri = _require_google_settings()
    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(GOOGLE_WORKSPACE_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": create_signed_state(user_sub),
        }
    )
    return f"{GOOGLE_AUTH_URL}?{query}"


def _fetch_google_user_email(access_token: str) -> str | None:
    profile = _get_json(GOOGLE_USERINFO_URL, access_token)
    email = profile.get("email")
    return email if isinstance(email, str) else None


def exchange_google_code(code: str, state: str) -> GoogleConnectionRecord:
    user_sub = verify_signed_state(state)
    client_id, client_secret, redirect_uri = _require_google_settings()
    token_payload = _post_form(
        GOOGLE_TOKEN_URL,
        {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
    )
    access_token = token_payload.get("access_token")
    if not isinstance(access_token, str):
        raise GoogleIntegrationError("Google did not return an access token during the OAuth exchange.")
    connection_email = _fetch_google_user_email(access_token)
    return upsert_google_connection(user_sub, token_payload, email=connection_email)


def refresh_google_connection(connection: GoogleConnectionRecord) -> GoogleConnectionRecord:
    client_id, client_secret, _ = _require_google_settings()
    token_payload = _post_form(
        GOOGLE_TOKEN_URL,
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": connection.refresh_token,
            "grant_type": "refresh_token",
        },
    )
    return upsert_google_connection(connection.user_sub, token_payload, email=connection.email)


def ensure_fresh_google_connection(connection: GoogleConnectionRecord) -> GoogleConnectionRecord:
    expires_at = connection.expires_at
    if not expires_at:
        return connection

    if expires_at <= datetime.now(timezone.utc) + timedelta(minutes=2):
        return refresh_google_connection(connection)
    return connection


def _fetch_attachment_preview(
    access_token: str,
    message_id: str,
    attachment_id: str,
    mime_type: str,
    size: int,
) -> str | None:
    if size > 150_000:
        return None
    if not (
        mime_type.startswith("text/")
        or mime_type in {"application/json", "application/xml"}
    ):
        return None

    payload = _get_json(
        GMAIL_ATTACHMENT_URL.format(message_id=message_id, attachment_id=attachment_id),
        access_token,
    )
    data = payload.get("data")
    if not isinstance(data, str):
        return None

    preview_text = _decode_text_payload(data)
    preview_text = re.sub(r"\s+", " ", preview_text).strip()
    return preview_text[:800] if preview_text else None


def _walk_message_payload(
    access_token: str,
    message_id: str,
    payload: dict[str, object],
    *,
    attachments: list[GmailAttachment],
    text_segments: list[str],
) -> None:
    parts = payload.get("parts")
    if isinstance(parts, list):
        for part in parts:
            if isinstance(part, dict):
                _walk_message_payload(
                    access_token,
                    message_id,
                    part,
                    attachments=attachments,
                    text_segments=text_segments,
                )

    filename = payload.get("filename")
    mime_type = payload.get("mimeType")
    body = payload.get("body", {})
    if not isinstance(body, dict):
        body = {}

    attachment_id = body.get("attachmentId")
    size = body.get("size")
    data = body.get("data")
    normalized_mime_type = mime_type if isinstance(mime_type, str) else "application/octet-stream"
    normalized_size = size if isinstance(size, int) else 0

    if isinstance(filename, str) and filename:
        text_preview: str | None = None
        if isinstance(attachment_id, str):
            text_preview = _fetch_attachment_preview(
                access_token,
                message_id,
                attachment_id,
                normalized_mime_type,
                normalized_size,
            )
        elif isinstance(data, str) and normalized_mime_type.startswith("text/"):
            text_preview = _decode_text_payload(data)[:800]

        attachments.append(
            GmailAttachment(
                filename=filename,
                mime_type=normalized_mime_type,
                size=normalized_size,
                text_preview=text_preview.strip() if text_preview else None,
            )
        )
        return

    if isinstance(data, str):
        if normalized_mime_type == "text/plain":
            text_segments.append(_decode_text_payload(data))
        elif normalized_mime_type == "text/html" and not text_segments:
            text_segments.append(_strip_html(_decode_text_payload(data)))


def fetch_unread_gmail_messages(access_token: str, limit: int = 5) -> list[GmailMessage]:
    list_query = urlencode({"maxResults": str(limit), "q": "in:inbox is:unread"})
    payload = _get_json(f"{GMAIL_LIST_URL}?{list_query}", access_token)
    raw_messages = payload.get("messages", [])
    if not isinstance(raw_messages, list):
        return []

    messages: list[GmailMessage] = []
    for raw_message in raw_messages:
        if not isinstance(raw_message, dict):
            continue
        message_id = raw_message.get("id")
        if not isinstance(message_id, str):
            continue

        detail = _get_json(
            f"{GMAIL_MESSAGE_URL.format(message_id=message_id)}?{urlencode({'format': 'full'})}",
            access_token,
        )
        payload_data = detail.get("payload", {})
        headers = payload_data.get("headers", []) if isinstance(payload_data, dict) else []
        sender = "Unknown sender"
        subject = "No subject"
        for header in headers:
            if not isinstance(header, dict):
                continue
            name = header.get("name")
            value = header.get("value")
            if not isinstance(name, str) or not isinstance(value, str):
                continue
            if name.lower() == "from":
                sender = value
            if name.lower() == "subject":
                subject = value

        attachments: list[GmailAttachment] = []
        text_segments: list[str] = []
        if isinstance(payload_data, dict):
            _walk_message_payload(
                access_token,
                message_id,
                payload_data,
                attachments=attachments,
                text_segments=text_segments,
            )

        snippet = detail.get("snippet")
        summary_snippet = re.sub(r"\s+", " ", " ".join(text_segments)).strip()
        if not summary_snippet and isinstance(snippet, str):
            summary_snippet = snippet.strip()
        messages.append(
            GmailMessage(
                id=message_id,
                sender=sender,
                subject=subject,
                snippet=summary_snippet[:400] if summary_snippet else "",
                attachments=attachments,
            )
        )

    return messages


def fetch_calendar_events(
    access_token: str,
    *,
    time_min: datetime,
    time_max: datetime,
    limit: int = 5,
) -> list[CalendarEvent]:
    query = urlencode(
        {
            "singleEvents": "true",
            "orderBy": "startTime",
            "timeMin": time_min.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "timeMax": time_max.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "maxResults": str(limit),
        }
    )
    payload = _get_json(f"{CALENDAR_EVENTS_URL}?{query}", access_token)
    raw_events = payload.get("items", [])
    if not isinstance(raw_events, list):
        return []

    events: list[CalendarEvent] = []
    for raw_event in raw_events:
        if not isinstance(raw_event, dict):
            continue
        event_id = raw_event.get("id")
        summary = raw_event.get("summary")
        start = raw_event.get("start", {})
        end = raw_event.get("end", {})
        if not isinstance(event_id, str) or not isinstance(summary, str):
            continue

        start_value = start.get("dateTime") or start.get("date")
        end_value = end.get("dateTime") or end.get("date")
        location = raw_event.get("location")
        html_link = raw_event.get("htmlLink")
        events.append(
            CalendarEvent(
                id=event_id,
                title=summary,
                start=start_value if isinstance(start_value, str) else "Unknown start",
                end=end_value if isinstance(end_value, str) else "Unknown end",
                location=location if isinstance(location, str) else None,
                html_link=html_link if isinstance(html_link, str) else None,
            )
        )

    return events


def fetch_todays_calendar_events(access_token: str, limit: int = 5) -> list[CalendarEvent]:
    now = datetime.now().astimezone()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    return fetch_calendar_events(access_token, time_min=day_start, time_max=day_end, limit=limit)


def query_calendar_freebusy(
    access_token: str,
    *,
    time_min: datetime,
    time_max: datetime,
    calendar_ids: list[str] | None = None,
) -> list[BusyWindow]:
    payload = _post_json(
        CALENDAR_FREEBUSY_URL,
        access_token,
        {
            "timeMin": time_min.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "timeMax": time_max.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "items": [{"id": calendar_id} for calendar_id in (calendar_ids or ["primary"])],
        },
    )
    calendars = payload.get("calendars", {})
    if not isinstance(calendars, dict):
        return []

    busy_windows: list[BusyWindow] = []
    for calendar_payload in calendars.values():
        if not isinstance(calendar_payload, dict):
            continue
        busy_entries = calendar_payload.get("busy", [])
        if not isinstance(busy_entries, list):
            continue
        for busy_entry in busy_entries:
            if not isinstance(busy_entry, dict):
                continue
            start = busy_entry.get("start")
            end = busy_entry.get("end")
            if isinstance(start, str) and isinstance(end, str):
                busy_windows.append(BusyWindow(start=start, end=end))

    return busy_windows


def create_calendar_event(
    access_token: str,
    *,
    title: str,
    start: str,
    end: str,
    description: str | None = None,
    location: str | None = None,
    attendees: list[str] | None = None,
) -> CalendarEvent:
    payload: dict[str, object] = {
        "summary": title,
        "start": {"dateTime": start},
        "end": {"dateTime": end},
    }
    if description:
        payload["description"] = description
    if location:
        payload["location"] = location
    if attendees:
        payload["attendees"] = [{"email": attendee} for attendee in attendees]

    event_payload = _post_json(CALENDAR_EVENTS_URL, access_token, payload)
    start_payload = event_payload.get("start", {})
    end_payload = event_payload.get("end", {})
    return CalendarEvent(
        id=str(event_payload.get("id", "")),
        title=str(event_payload.get("summary", title)),
        start=str(start_payload.get("dateTime") or start_payload.get("date") or start),
        end=str(end_payload.get("dateTime") or end_payload.get("date") or end),
        location=event_payload.get("location") if isinstance(event_payload.get("location"), str) else location,
        html_link=event_payload.get("htmlLink") if isinstance(event_payload.get("htmlLink"), str) else None,
    )


def create_gmail_draft(
    access_token: str,
    *,
    subject: str,
    body: str,
    to_addresses: list[str],
    cc_addresses: list[str] | None = None,
    bcc_addresses: list[str] | None = None,
    attachments: list[TaskAttachment] | None = None,
) -> dict[str, object]:
    message = EmailMessage()
    message["Subject"] = subject
    if to_addresses:
        message["To"] = ", ".join(to_addresses)
    if cc_addresses:
        message["Cc"] = ", ".join(cc_addresses)
    if bcc_addresses:
        message["Bcc"] = ", ".join(bcc_addresses)
    message.set_content(body)

    for attachment in attachments or []:
        try:
            attachment_bytes = base64.b64decode(attachment.data_base64)
        except Exception as exc:
            raise GoogleIntegrationError(
                f"Attachment `{attachment.name}` could not be decoded."
            ) from exc

        maintype, _, subtype = attachment.mime_type.partition("/")
        normalized_maintype = maintype or "application"
        normalized_subtype = subtype or "octet-stream"
        message.add_attachment(
            attachment_bytes,
            maintype=normalized_maintype,
            subtype=normalized_subtype,
            filename=attachment.name,
        )

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    return _post_json(
        GMAIL_DRAFTS_URL,
        access_token,
        {"message": {"raw": raw_message}},
    )
