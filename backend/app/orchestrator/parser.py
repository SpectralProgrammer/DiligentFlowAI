from app.models.task import ParsedTask


def parse_task(input_text: str) -> ParsedTask:
    normalized = input_text.lower()

    if any(word in normalized for word in ["email", "mail", "send", "draft", "reply"]):
        action = "draft" if "draft" in normalized else "send"
        return ParsedTask(
            agent_id="email-agent",
            action=action,
            resource="gmail-api",
            confidence="high",
            reasoning="The request includes common email verbs, so it maps to the email agent.",
        )

    if any(word in normalized for word in ["calendar", "meeting", "schedule", "invite"]):
        action = "read" if any(word in normalized for word in ["show", "check", "read"]) else "schedule"
        return ParsedTask(
            agent_id="calendar-agent",
            action=action,
            resource="google-calendar",
            confidence="high",
            reasoning="The request includes scheduling language, so it maps to the calendar agent.",
        )

    return ParsedTask(
        agent_id="finance-agent",
        action="analyze",
        resource="market-data",
        confidence="medium",
        reasoning="The request did not match communication or scheduling keywords, so it falls back to finance analysis.",
    )
