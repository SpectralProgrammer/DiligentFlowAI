from fastapi import APIRouter
from app.models.task import ParsedTask, TaskRequest, TaskResponse
from app.orchestrator.orchestrator import run_task
from app.orchestrator.parser import parse_task

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/preview")
def preview_task(payload: TaskRequest) -> ParsedTask:
    return parse_task(payload.input_text)


@router.post("")
def create_task(payload: TaskRequest) -> TaskResponse:
    return run_task(payload.input_text)
