from datetime import datetime, timezone
from uuid import uuid4

from app.agents.calendar_agent import execute_calendar_task
from app.agents.email_agent import execute_email_task
from app.agents.finance_agent import execute_finance_task
from app.audit.logger import log_event
from app.models.agent import AgentCapability, AgentDefinition
from app.models.task import TaskRecord, TaskResponse
from app.orchestrator.parser import parse_task
from app.permissions.openfga_client import check_permission
from app.vault.token_service import issue_token

AGENTS: list[AgentDefinition] = [
    AgentDefinition(
        id="email-agent",
        name="Email Agent",
        summary="Drafts or sends email with scoped Gmail access.",
        capabilities=[
            AgentCapability(
                action="send",
                resource="gmail-api",
                description="Send a message through Gmail.",
            ),
            AgentCapability(
                action="draft",
                resource="gmail-api",
                description="Create an email draft for review.",
            ),
        ],
    ),
    AgentDefinition(
        id="calendar-agent",
        name="Calendar Agent",
        summary="Schedules and inspects events with limited calendar permissions.",
        capabilities=[
            AgentCapability(
                action="schedule",
                resource="google-calendar",
                description="Create a calendar event.",
            ),
            AgentCapability(
                action="read",
                resource="google-calendar",
                description="Read availability or event details.",
            ),
        ],
    ),
    AgentDefinition(
        id="finance-agent",
        name="Finance Agent",
        summary="Analyzes finance requests with tightly scoped market-data access.",
        capabilities=[
            AgentCapability(
                action="analyze",
                resource="market-data",
                description="Analyze market or portfolio questions.",
            ),
            AgentCapability(
                action="summarize",
                resource="market-data",
                description="Summarize finance data for a user.",
            ),
        ],
    ),
]

TASK_HISTORY: list[TaskRecord] = []


def list_agents() -> list[AgentDefinition]:
    return AGENTS


def list_task_history() -> list[TaskRecord]:
    return list(reversed(TASK_HISTORY[-10:]))


def run_task(input_text: str) -> TaskResponse:
    audit_trail: list[str] = []
    parsed_task = parse_task(input_text)
    audit_trail.append(
        f"Parsed request for agent `{parsed_task.agent_id}` with scope `{parsed_task.action}:{parsed_task.resource}`."
    )
    log_event("orchestrator", f"Received task: {input_text}")

    allowed = check_permission(
        parsed_task.agent_id,
        parsed_task.action,
        parsed_task.resource,
    )
    audit_trail.append(
        "Permission granted by policy matrix."
        if allowed
        else "Permission denied by policy matrix."
    )

    if not allowed:
        response = TaskResponse(
            status="denied",
            parsed_task=parsed_task,
            permission_granted=False,
            audit_trail=audit_trail,
        )
        _record_task(input_text, response)
        log_event("permission", "Denied")
        return response

    token = issue_token(parsed_task.agent_id, [f"{parsed_task.action}:{parsed_task.resource}"])
    audit_trail.append("Issued a short-lived scoped token for the selected agent.")
    log_event("vault", "Token issued")

    if parsed_task.agent_id == "email-agent":
        result = execute_email_task(input_text, parsed_task, token)
    elif parsed_task.agent_id == "calendar-agent":
        result = execute_calendar_task(input_text, parsed_task, token)
    else:
        result = execute_finance_task(input_text, parsed_task, token)

    audit_trail.append("Executed agent handler and collected normalized result.")
    log_event("agent", result.summary)

    response = TaskResponse(
        status="completed",
        parsed_task=parsed_task,
        permission_granted=True,
        token=token,
        result=result,
        audit_trail=audit_trail,
    )
    _record_task(input_text, response)
    return response


def _record_task(input_text: str, response: TaskResponse) -> None:
    TASK_HISTORY.append(
        TaskRecord(
            id=str(uuid4()),
            created_at=datetime.now(timezone.utc),
            input_text=input_text,
            status=response.status,
            parsed_task=response.parsed_task,
            permission_granted=response.permission_granted,
            result_summary=response.result.summary if response.result else "Permission denied",
        )
    )
