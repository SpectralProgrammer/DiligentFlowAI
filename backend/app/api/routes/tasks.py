from fastapi import APIRouter
from app.orchestrator.orchestrator import run_task
from app.models.task import TaskRequest, TaskResponse

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("")
def create_task(payload: TaskRequest) -> TaskResponse:
    return run_task(payload.input_text)
