from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.agents import router as agents_router
from app.api.routes.chat import router as chat_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.google import router as google_router
from app.api.routes.history import router as history_router
from app.api.routes.permissions import router as permissions_router
from app.api.routes.tasks import router as tasks_router
from app.api.routes.tokens import router as tokens_router
from app.core.auth import require_auth
from app.core.config import get_settings

def create_app() -> FastAPI:
    app = FastAPI(title="Authorized-to-Act Backend")
    settings = get_settings()
    protected_dependencies = [Depends(require_auth)]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat_router, dependencies=protected_dependencies)
    app.include_router(dashboard_router, dependencies=protected_dependencies)
    app.include_router(tasks_router, dependencies=protected_dependencies)
    app.include_router(history_router, dependencies=protected_dependencies)
    app.include_router(agents_router, dependencies=protected_dependencies)
    app.include_router(permissions_router, dependencies=protected_dependencies)
    app.include_router(tokens_router, dependencies=protected_dependencies)
    app.include_router(google_router)

    @app.get("/healthz")
    def healthcheck():
        return {
            "status": "ok",
            "auth0_enabled": settings.auth0_enabled,
            "google_enabled": settings.google_enabled,
        }

    @app.get("/")
    def root():
        return {
            "message": "Authorized-to-Act backend is running",
            "frontend_hint": "Open the Next.js app to preview routes, submit tasks, and inspect decisions.",
            "auth": {
                "provider": "Auth0",
                "api_protected": True,
                "audience": settings.auth0_audience,
            },
            "available_routes": [
                "/healthz",
                "/chat",
                "/dashboard/bootstrap",
                "/tasks",
                "/tasks/preview",
                "/history",
                "/agents",
                "/permissions",
                "/tokens/about",
                "/google/status",
                "/google/connect",
                "/google/callback",
                "/google/summary",
            ],
        }

    return app


app = create_app()
