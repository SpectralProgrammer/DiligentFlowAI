from fastapi import APIRouter
from app.core.config import get_settings
from app.orchestrator.orchestrator import list_agents, list_task_history
from app.permissions.openfga_client import list_permissions

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/bootstrap")
def get_dashboard_bootstrap() -> dict[str, object]:
    settings = get_settings()
    return {
        "agents": list_agents(),
        "history": list_task_history(),
        "permissions": list_permissions(),
        "token_info": {
            "kind": "auth0-protected-session + internal-scoped-token",
            "ttl_minutes": 30,
            "issuer": settings.auth0_domain or "auth0-not-configured",
            "note": (
                "Auth0 protects the operator session and backend API. "
                "The orchestrator still mints 30-minute internal scoped tokens "
                "for individual agent actions."
            ),
        },
    }
