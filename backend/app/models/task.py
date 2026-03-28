from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.token import ScopedToken


class TaskRequest(BaseModel):
    input_text: str = Field(min_length=3, max_length=1000)


class ParsedTask(BaseModel):
    agent_id: str
    action: str
    resource: str
    confidence: Literal["high", "medium", "low"]
    reasoning: str


class TaskExecutionResult(BaseModel):
    summary: str
    details: dict[str, Any]


class TaskResponse(BaseModel):
    status: Literal["completed", "denied"]
    parsed_task: ParsedTask
    permission_granted: bool
    token: ScopedToken | None = None
    result: TaskExecutionResult | None = None
    audit_trail: list[str]


class TaskRecord(BaseModel):
    id: str
    created_at: datetime
    input_text: str
    status: Literal["completed", "denied"]
    parsed_task: ParsedTask
    permission_granted: bool
    result_summary: str
