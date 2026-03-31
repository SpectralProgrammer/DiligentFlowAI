from fastapi import APIRouter

from app.models.task import TaskRecord
from app.orchestrator.orchestrator import list_task_history

router = APIRouter(prefix="/history", tags=["history"])


@router.get("")
def get_history() -> list[TaskRecord]:
    return list_task_history()
