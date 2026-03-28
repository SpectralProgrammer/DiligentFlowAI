from fastapi import APIRouter

from app.models.agent import AgentDefinition
from app.orchestrator.orchestrator import list_agents

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("")
def get_agents() -> list[AgentDefinition]:
    return list_agents()
