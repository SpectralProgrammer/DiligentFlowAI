from app.models.task import ParsedTask, TaskExecutionResult
from app.models.token import ScopedToken


def execute_email_task(
    input_text: str,
    parsed_task: ParsedTask,
    token: ScopedToken,
) -> TaskExecutionResult:
    verb = "drafted" if parsed_task.action == "draft" else "prepared to send"
    return TaskExecutionResult(
        summary=f"Email task {verb} with demo Gmail access.",
        details={
            "channel": "email",
            "provider": "Gmail",
            "mode": "mock",
            "input": input_text,
            "granted_scopes": token.scopes,
            "next_step": "Connect Gmail or Auth0-issued downstream credentials to send real email.",
        },
    )
