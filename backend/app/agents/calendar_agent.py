from app.models.task import ParsedTask, TaskExecutionResult
from app.models.token import ScopedToken


def execute_calendar_task(
    input_text: str,
    parsed_task: ParsedTask,
    token: ScopedToken,
) -> TaskExecutionResult:
    return TaskExecutionResult(
        summary="Calendar task prepared with demo Google Calendar access.",
        details={
            "channel": "calendar",
            "provider": "Google Calendar",
            "mode": "mock",
            "input": input_text,
            "action": parsed_task.action,
            "granted_scopes": token.scopes,
            "next_step": "Add Google Calendar OAuth credentials to create or read live events.",
        },
    )
