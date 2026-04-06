from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
import json
import re
from typing import Any

from app.google.client import (
    CalendarEvent,
    GmailMessage,
    GoogleIntegrationError,
    create_calendar_event,
    create_gmail_draft,
    ensure_fresh_google_connection,
    fetch_calendar_events,
    fetch_todays_calendar_events,
    fetch_unread_gmail_messages,
    query_calendar_freebusy,
)
from app.google.storage import GoogleConnectionRecord, get_google_connection
from app.models.task import TaskAttachment
from app.services.llm import generate_response

GMAIL_COMPOSE_SCOPE = "https://www.googleapis.com/auth/gmail.compose"
CALENDAR_EVENTS_SCOPE = "https://www.googleapis.com/auth/calendar.events"


class GoogleConnectionMissingError(RuntimeError):
    """Raised when the signed-in user has not connected Google yet."""


@dataclass
class AvailabilityPreferences:
    time_min: datetime
    time_max: datetime
    day_start_hour: int
    day_end_hour: int
    slot_minutes: int
    desired_slots: int
    label: str


@dataclass
class AvailabilitySlot:
    start: str
    end: str
    label: str


def _coerce_string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _short_scope_name(scope: str) -> str:
    return scope.rsplit("/", 1)[-1]


def _extract_json_payload(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        payload = json.loads(cleaned)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise RuntimeError("The assistant did not return valid JSON.")

    payload = json.loads(match.group(0))
    if not isinstance(payload, dict):
        raise RuntimeError("The assistant returned JSON, but not the expected object payload.")
    return payload


def _generate_structured_json(prompt: str) -> dict[str, Any]:
    response = generate_response(prompt=prompt)
    return _extract_json_payload(response)


def _require_google_connection(
    user_sub: str,
    *,
    required_scopes: tuple[str, ...] = (),
) -> GoogleConnectionRecord:
    connection = get_google_connection(user_sub)
    if connection is None:
        raise GoogleConnectionMissingError("Connect Google first to use Gmail and Calendar features.")

    connection = ensure_fresh_google_connection(connection)
    missing_scopes = sorted(set(required_scopes) - set(connection.scopes))
    if missing_scopes:
        missing_label = ", ".join(_short_scope_name(scope) for scope in missing_scopes)
        raise RuntimeError(
            f"Reconnect Google to grant the required scopes for this action: {missing_label}."
        )
    return connection


def _wants_email_summary(prompt: str) -> bool:
    normalized = prompt.lower()
    return any(term in normalized for term in ["email", "gmail", "inbox", "mail", "attachment"])


def _wants_calendar_summary(prompt: str) -> bool:
    normalized = prompt.lower()
    return any(term in normalized for term in ["calendar", "meeting", "schedule", "agenda", "event"])


def _wants_availability_help(prompt: str) -> bool:
    normalized = prompt.lower()
    return any(
        term in normalized
        for term in [
            "availability",
            "available",
            "free time",
            "free slot",
            "open slot",
            "open time",
            "when can",
            "deep work",
            "focus block",
            "focus time",
        ]
    )


def _wants_daily_digest(prompt: str) -> bool:
    normalized = prompt.lower()
    return any(term in normalized for term in ["daily digest", "morning digest", "daily brief", "brief me"])


def _extract_duration_minutes(prompt: str) -> int:
    match = re.search(r"(\d+)\s*(minute|min|hour|hr|hours|hrs)", prompt)
    if match:
        quantity = int(match.group(1))
        unit = match.group(2)
        return quantity * 60 if unit.startswith("h") else quantity
    if "deep work" in prompt or "focus" in prompt:
        return 90
    return 60


def _extract_count(prompt: str, default: int) -> int:
    numeric_match = re.search(r"(\d+)\s+(?:slots?|blocks?|times?)", prompt)
    if numeric_match:
        return max(1, min(int(numeric_match.group(1)), 5))

    word_map = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
    }
    for word, value in word_map.items():
        if word in prompt:
            return value

    return default


def _next_weekday(start: date, weekday: int) -> date:
    days_ahead = (weekday - start.weekday()) % 7
    return start + timedelta(days=days_ahead)


def _build_availability_preferences(prompt: str) -> AvailabilityPreferences:
    now = datetime.now().astimezone()
    normalized = prompt.lower()

    if "next week" in normalized:
        start_day = _next_weekday(now.date() + timedelta(days=7), 0)
        end_day = start_day + timedelta(days=7)
    elif "this week" in normalized:
        start_day = now.date()
        end_day = _next_weekday(now.date(), 6) + timedelta(days=1)
    elif "tomorrow" in normalized:
        start_day = now.date() + timedelta(days=1)
        end_day = start_day + timedelta(days=1)
    elif "today" in normalized:
        start_day = now.date()
        end_day = start_day + timedelta(days=1)
    else:
        start_day = now.date()
        end_day = start_day + timedelta(days=5)

    if "afternoon" in normalized:
        day_start_hour, day_end_hour = 12, 18
    elif "morning" in normalized:
        day_start_hour, day_end_hour = 8, 12
    elif "evening" in normalized:
        day_start_hour, day_end_hour = 17, 21
    else:
        day_start_hour, day_end_hour = 9, 17

    slot_minutes = _extract_duration_minutes(normalized)
    desired_slots = _extract_count(
        normalized,
        default=2 if ("deep work" in normalized or "focus" in normalized) else 3,
    )

    time_min = datetime.combine(start_day, time.min, tzinfo=now.tzinfo)
    time_max = datetime.combine(end_day, time.min, tzinfo=now.tzinfo)
    if start_day == now.date():
        time_min = max(time_min, now)

    label = "focus block" if ("deep work" in normalized or "focus" in normalized) else "meeting slot"
    return AvailabilityPreferences(
        time_min=time_min,
        time_max=time_max,
        day_start_hour=day_start_hour,
        day_end_hour=day_end_hour,
        slot_minutes=slot_minutes,
        desired_slots=desired_slots,
        label=label,
    )


def _parse_iso_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone()


def _merge_busy_windows(windows: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    if not windows:
        return []

    ordered = sorted(windows, key=lambda item: item[0])
    merged: list[tuple[datetime, datetime]] = [ordered[0]]
    for start, end in ordered[1:]:
        previous_start, previous_end = merged[-1]
        if start <= previous_end:
            merged[-1] = (previous_start, max(previous_end, end))
        else:
            merged.append((start, end))
    return merged


def _append_slots_from_gap(
    *,
    gap_start: datetime,
    gap_end: datetime,
    slot_minutes: int,
    label: str,
    slots: list[AvailabilitySlot],
    desired_slots: int,
) -> None:
    cursor = gap_start
    slot_delta = timedelta(minutes=slot_minutes)
    while cursor + slot_delta <= gap_end and len(slots) < desired_slots:
        slot_end = cursor + slot_delta
        slots.append(
            AvailabilitySlot(
                start=cursor.isoformat(),
                end=slot_end.isoformat(),
                label=f"{label.title()}: {cursor.strftime('%a %b %d %I:%M %p')} - {slot_end.strftime('%I:%M %p')}",
            )
        )
        cursor = slot_end


def suggest_calendar_slots(access_token: str, prompt: str) -> list[AvailabilitySlot]:
    preferences = _build_availability_preferences(prompt)
    busy_windows = query_calendar_freebusy(
        access_token,
        time_min=preferences.time_min,
        time_max=preferences.time_max,
    )
    normalized_busy = _merge_busy_windows(
        [
            (_parse_iso_datetime(window.start), _parse_iso_datetime(window.end))
            for window in busy_windows
        ]
    )

    slots: list[AvailabilitySlot] = []
    current_day = preferences.time_min.date()
    final_day = preferences.time_max.date()

    while current_day < final_day and len(slots) < preferences.desired_slots:
        day_start = datetime.combine(
            current_day,
            time(hour=preferences.day_start_hour),
            tzinfo=preferences.time_min.tzinfo,
        )
        day_end = datetime.combine(
            current_day,
            time(hour=preferences.day_end_hour),
            tzinfo=preferences.time_min.tzinfo,
        )

        window_start = max(day_start, preferences.time_min)
        window_end = min(day_end, preferences.time_max)
        if window_start < window_end:
            relevant_busy = [
                (max(start, window_start), min(end, window_end))
                for start, end in normalized_busy
                if end > window_start and start < window_end
            ]
            cursor = window_start
            for busy_start, busy_end in relevant_busy:
                if cursor < busy_start:
                    _append_slots_from_gap(
                        gap_start=cursor,
                        gap_end=busy_start,
                        slot_minutes=preferences.slot_minutes,
                        label=preferences.label,
                        slots=slots,
                        desired_slots=preferences.desired_slots,
                    )
                cursor = max(cursor, busy_end)
                if len(slots) >= preferences.desired_slots:
                    break

            if len(slots) < preferences.desired_slots and cursor < window_end:
                _append_slots_from_gap(
                    gap_start=cursor,
                    gap_end=window_end,
                    slot_minutes=preferences.slot_minutes,
                    label=preferences.label,
                    slots=slots,
                    desired_slots=preferences.desired_slots,
                )

        current_day += timedelta(days=1)

    return slots


def _format_messages(messages: list[GmailMessage]) -> str:
    if not messages:
        return "No unread inbox emails were returned."

    lines: list[str] = []
    for message in messages:
        attachment_line = (
            "  Attachments: "
            + ", ".join(
                f"{attachment.filename} ({attachment.mime_type}, {attachment.size} bytes)"
                + (f" preview: {attachment.text_preview}" if attachment.text_preview else "")
                for attachment in message.attachments
            )
            if message.attachments
            else "  Attachments: none"
        )
        lines.append(
            f"- From: {message.sender}\n"
            f"  Subject: {message.subject}\n"
            f"  Snippet: {message.snippet or 'No preview'}\n"
            f"{attachment_line}"
        )
    return "\n".join(lines)


def _format_events(events: list[CalendarEvent]) -> str:
    if not events:
        return "No events were returned for the requested time window."

    lines = []
    for event in events:
        location = f" | Location: {event.location}" if event.location else ""
        lines.append(f"- {event.title}\n  Start: {event.start}\n  End: {event.end}{location}")
    return "\n".join(lines)


def _format_slots(slots: list[AvailabilitySlot]) -> str:
    if not slots:
        return "No free slots were found in the requested window."
    return "\n".join(f"- {slot.label}" for slot in slots)


def build_google_summary(user_sub: str, prompt: str) -> dict[str, Any]:
    connection = _require_google_connection(user_sub)

    try:
        include_email = _wants_email_summary(prompt)
        include_calendar = _wants_calendar_summary(prompt)
        if not include_email and not include_calendar:
            include_email = True
            include_calendar = True

        messages = fetch_unread_gmail_messages(connection.access_token) if include_email else []
        events = fetch_todays_calendar_events(connection.access_token) if include_calendar else []
    except GoogleIntegrationError as exc:
        raise RuntimeError(str(exc)) from exc

    summary_prompt = (
        "You are preparing a concise Google Workspace briefing.\n"
        f"Connected account: {connection.email or 'unknown'}\n"
        f"User request: {prompt}\n\n"
        "Unread Gmail context:\n"
        f"{_format_messages(messages)}\n\n"
        "Google Calendar context:\n"
        f"{_format_events(events)}\n\n"
        "Respond with short labeled sections. Highlight priority emails, important meetings, "
        "and suggested next steps."
    )
    response = generate_response(prompt=summary_prompt)

    return {
        "response": response,
        "email_count": len(messages),
        "event_count": len(events),
        "connected_email": connection.email,
        "emails": [asdict(message) for message in messages],
        "events": [asdict(event) for event in events],
    }


def _select_requested_attachments(
    attachments: list[TaskAttachment],
    requested_names: list[str],
) -> list[TaskAttachment]:
    if not requested_names:
        return attachments

    requested_lookup = {name.lower() for name in requested_names}
    matched = [attachment for attachment in attachments if attachment.name.lower() in requested_lookup]
    return matched or attachments


def create_google_draft_from_prompt(
    user_sub: str,
    prompt: str,
    attachments: list[TaskAttachment] | None = None,
) -> dict[str, Any]:
    connection = _require_google_connection(user_sub, required_scopes=(GMAIL_COMPOSE_SCOPE,))
    uploaded_attachments = attachments or []
    attachment_names = ", ".join(attachment.name for attachment in uploaded_attachments) or "None"
    draft_payload = _generate_structured_json(
        "Return only valid JSON.\n"
        "Create a Gmail draft plan for the user's request.\n"
        "Schema:\n"
        "{\n"
        '  "to": ["person@example.com"],\n'
        '  "cc": [],\n'
        '  "bcc": [],\n'
        '  "subject": "Short subject",\n'
        '  "body": "Plain-text email body",\n'
        '  "attachments": ["filename.ext"],\n'
        '  "notes": ["Any unresolved recipient or follow-up note"]\n'
        "}\n"
        f"Uploaded attachments available: {attachment_names}\n"
        "If the request does not provide an email address, leave the recipient arrays empty.\n"
        "User request:\n"
        f"{prompt}"
    )

    selected_attachments = _select_requested_attachments(
        uploaded_attachments,
        _coerce_string_list(draft_payload.get("attachments")),
    )
    subject = str(draft_payload.get("subject") or "Draft from Authorized Assistant").strip()
    body = str(draft_payload.get("body") or prompt.strip()).strip()
    if not body:
        body = "Draft created from Authorized Assistant."

    try:
        draft_result = create_gmail_draft(
            connection.access_token,
            subject=subject,
            body=body,
            to_addresses=_coerce_string_list(draft_payload.get("to")),
            cc_addresses=_coerce_string_list(draft_payload.get("cc")),
            bcc_addresses=_coerce_string_list(draft_payload.get("bcc")),
            attachments=selected_attachments,
        )
    except GoogleIntegrationError as exc:
        raise RuntimeError(str(exc)) from exc

    return {
        "summary": "Created a live Gmail draft.",
        "details": {
            "channel": "email",
            "provider": "Gmail",
            "mode": "live",
            "subject": subject,
            "to": _coerce_string_list(draft_payload.get("to")),
            "cc": _coerce_string_list(draft_payload.get("cc")),
            "bcc": _coerce_string_list(draft_payload.get("bcc")),
            "notes": _coerce_string_list(draft_payload.get("notes")),
            "attachments": [attachment.name for attachment in selected_attachments],
            "draft_id": draft_result.get("id"),
            "message_id": (
                draft_result.get("message", {}).get("id")
                if isinstance(draft_result.get("message"), dict)
                else None
            ),
        },
    }


def _looks_like_flexible_block_request(prompt: str) -> bool:
    normalized = prompt.lower()
    return any(
        term in normalized
        for term in ["deep work", "focus block", "focus time", "block off", "plan around", "protect time"]
    )


def _extract_calendar_events(prompt: str) -> list[dict[str, Any]]:
    payload = _generate_structured_json(
        "Return only valid JSON.\n"
        "Convert the user's scheduling request into calendar event objects.\n"
        "Schema:\n"
        "{\n"
        '  "events": [\n'
        "    {\n"
        '      "title": "Event title",\n'
        '      "start": "2026-04-06T14:00:00-04:00",\n'
        '      "end": "2026-04-06T15:00:00-04:00",\n'
        '      "description": "Optional description",\n'
        '      "location": "Optional location",\n'
        '      "attendees": ["person@example.com"]\n'
        "    }\n"
        "  ]\n"
        "}\n"
        f"Current local date and time: {datetime.now().astimezone().isoformat()}\n"
        "Use RFC3339 timestamps with timezone offsets.\n"
        "Reasonable defaults are allowed when the request is vague: morning 9 AM, afternoon 2 PM, evening 6 PM, and 60-minute duration.\n"
        "User request:\n"
        f"{prompt}"
    )
    raw_events = payload.get("events", [])
    if not isinstance(raw_events, list):
        raise RuntimeError("The calendar planner did not return an events list.")
    return [event for event in raw_events if isinstance(event, dict)]


def create_google_calendar_events_from_prompt(user_sub: str, prompt: str) -> dict[str, Any]:
    connection = _require_google_connection(user_sub, required_scopes=(CALENDAR_EVENTS_SCOPE,))

    created_events: list[CalendarEvent] = []
    try:
        if _looks_like_flexible_block_request(prompt):
            slots = suggest_calendar_slots(connection.access_token, prompt)
            if not slots:
                return {
                    "summary": "No free calendar slots were found for that planning request.",
                    "details": {
                        "channel": "calendar",
                        "provider": "Google Calendar",
                        "mode": "live",
                        "created_events": [],
                        "suggested_slots": [],
                    },
                }

            requested_count = _extract_count(prompt.lower(), default=2)
            title = "Deep Work Block" if "deep work" in prompt.lower() else "Focus Block"
            for slot in slots[:requested_count]:
                created_events.append(
                    create_calendar_event(
                        connection.access_token,
                        title=title,
                        start=slot.start,
                        end=slot.end,
                        description=f"Created from request: {prompt}",
                    )
                )
        else:
            for planned_event in _extract_calendar_events(prompt)[:4]:
                start_value = planned_event.get("start")
                end_value = planned_event.get("end")
                if not isinstance(start_value, str) or not isinstance(end_value, str):
                    continue

                created_events.append(
                    create_calendar_event(
                        connection.access_token,
                        title=str(planned_event.get("title") or "New Event"),
                        start=start_value,
                        end=end_value,
                        description=str(planned_event.get("description") or "").strip() or None,
                        location=str(planned_event.get("location") or "").strip() or None,
                        attendees=_coerce_string_list(planned_event.get("attendees")),
                    )
                )
    except GoogleIntegrationError as exc:
        raise RuntimeError(str(exc)) from exc

    if not created_events:
        return {
            "summary": "I could not extract a concrete calendar event from that request yet.",
            "details": {
                "channel": "calendar",
                "provider": "Google Calendar",
                "mode": "live",
                "created_events": [],
                "note": "Try including a clearer date or time, or ask for open slots first.",
            },
        }

    return {
        "summary": (
            "Created a live Google Calendar event."
            if len(created_events) == 1
            else f"Created {len(created_events)} live Google Calendar events."
        ),
        "details": {
            "channel": "calendar",
            "provider": "Google Calendar",
            "mode": "live",
            "created_events": [asdict(event) for event in created_events],
        },
    }


def read_google_calendar_workspace(user_sub: str, prompt: str) -> dict[str, Any]:
    connection = _require_google_connection(user_sub)
    try:
        if _wants_availability_help(prompt):
            slots = suggest_calendar_slots(connection.access_token, prompt)
            return {
                "summary": (
                    "Suggested available calendar slots."
                    if slots
                    else "No open calendar slots matched the requested window."
                ),
                "details": {
                    "channel": "calendar",
                    "provider": "Google Calendar",
                    "mode": "live",
                    "slots": [asdict(slot) for slot in slots],
                },
            }

        now = datetime.now().astimezone()
        upcoming_events = fetch_calendar_events(
            connection.access_token,
            time_min=now,
            time_max=now + timedelta(days=2),
            limit=6,
        )
        return {
            "summary": "Fetched upcoming Google Calendar events.",
            "details": {
                "channel": "calendar",
                "provider": "Google Calendar",
                "mode": "live",
                "events": [asdict(event) for event in upcoming_events],
            },
        }
    except GoogleIntegrationError as exc:
        raise RuntimeError(str(exc)) from exc
