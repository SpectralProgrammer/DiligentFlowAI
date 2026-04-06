from app.models.task import ParsedTask, TaskExecutionResult
from app.models.token import ScopedToken


def execute_finance_task(
    input_text: str,
    parsed_task: ParsedTask,
    token: ScopedToken,
) -> TaskExecutionResult:
    return TaskExecutionResult(
        summary="Finance analysis completed with simulated market data access.",
        details={
            "channel": "finance",
            "provider": "Market data",
            "mode": "mock",
            "input": input_text,
            "action": parsed_task.action,
            "granted_scopes": token.scopes,
            "insight": "This is where a brokerage, pricing, or portfolio API response would be normalized.",
        },
    )
