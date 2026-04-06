from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/tokens", tags=["tokens"])


@router.get("/about")
def about_tokens() -> dict[str, str | int]:
    settings = get_settings()
    return {
        "kind": "auth0-protected-session + internal-scoped-token",
        "ttl_minutes": 30,
        "issuer": settings.auth0_domain or "auth0-not-configured",
        "note": "Auth0 protects the operator session and backend API. The orchestrator still mints 30-minute internal scoped tokens for individual agent actions.",
    }
